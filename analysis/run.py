"""Rebuild every analytical artifact from the original UCI workbook."""
from pathlib import Path
import hashlib
import json
import urllib.request
import zipfile
import io
import sys
import numpy as np
import pandas as pd
import duckdb
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw/Online Retail.xlsx'
OUT = ROOT / 'reports'
URL = 'https://archive.ics.uci.edu/static/public/352/online+retail.zip'


def save_chart(fig, path):
    """Render in memory; do not reopen unchanged PNGs displayed in Windows."""
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png')
    payload = buffer.getvalue()
    if not path.exists() or path.read_bytes() != payload:
        path.write_bytes(payload)


def main():
    for folder in [RAW.parent, OUT / 'figures', ROOT / 'data/processed']:
        folder.mkdir(parents=True, exist_ok=True)
    if not RAW.exists():
        print('Downloading original UCI data...', flush=True)
        try:
            with urllib.request.urlopen(URL, timeout=120) as response:
                archive = zipfile.ZipFile(io.BytesIO(response.read()))
            member = next(n for n in archive.namelist() if n.endswith('.xlsx'))
            RAW.write_bytes(archive.read(member))
        except Exception as error:
            raise RuntimeError(f'Download failed. Download {URL}, extract Online Retail.xlsx into {RAW.parent}, then rerun.') from error
    print('Reading workbook...', flush=True)
    raw = pd.read_excel(RAW, engine='openpyxl', dtype={'InvoiceNo': str, 'StockCode': str})
    raw.columns = ['invoice_no', 'stock_code', 'description', 'quantity', 'invoice_date', 'unit_price', 'customer_id', 'country']
    duplicates = int(raw.duplicated().sum())
    df = raw.drop_duplicates().copy()
    df['invoice_date'] = pd.to_datetime(df.invoice_date, errors='raise')
    df['customer_id'] = df.customer_id.astype('Int64').astype('string')
    # Explicit rounding to nearest penny, half away from zero, at LINE level.
    values = df.quantity * df.unit_price * 100
    df['amount_pence'] = (np.sign(values) * np.floor(np.abs(values) + .500000001)).astype('int64')
    df['exclusion_reason'] = np.select([
        df.invoice_no.str.upper().str.startswith('C'), df.quantity.lt(0),
        df.quantity.eq(0), df.unit_price.le(0), df.customer_id.isna()],
        ['cancellation_credit', 'negative_quantity', 'zero_quantity', 'nonpositive_price', 'missing_customer'], default='included')
    audit = df.groupby('exclusion_reason', dropna=False).agg(rows=('invoice_no', 'size'), amount_pence=('amount_pence', 'sum')).reset_index()
    audit.to_csv(OUT / 'cleaning_audit.csv', index=False)
    sales = df[df.exclusion_reason.eq('included')].drop(columns='exclusion_reason').copy()
    credits = df[df.invoice_no.str.upper().str.startswith('C') | df.quantity.lt(0)].copy()
    # Last calendar day is incomplete: conservative observation window excludes it.
    end = df.invoice_date.max().normalize()
    sales = sales[sales.invoice_date.lt(end)]
    credits = credits[credits.invoice_date.lt(end)]
    positive_scope = df[df.quantity.gt(0) & df.unit_price.gt(0) & ~df.invoice_no.str.upper().str.startswith('C') & df.invoice_date.lt(end)].copy()
    positive_scope['customer_scope'] = np.where(positive_scope.customer_id.notna(), 'identified', 'unidentified')
    coverage = positive_scope.groupby('customer_scope').agg(rows=('invoice_no', 'size'), revenue_pence=('amount_pence', 'sum')).reset_index()
    coverage['revenue_gbp'] = coverage.revenue_pence / 100
    coverage.to_csv(OUT / 'customer_coverage.csv', index=False)
    sales.to_csv(ROOT / 'data/processed/sales.csv', index=False)
    con = duckdb.connect(str(ROOT / 'data/processed/retail.duckdb'))
    con.register('sales_frame', sales)
    con.execute('CREATE OR REPLACE TABLE sales AS SELECT * FROM sales_frame')
    con.register('credits_frame', credits)
    con.execute('CREATE OR REPLACE TABLE credits AS SELECT * FROM credits_frame')
    con.execute('CREATE OR REPLACE TABLE settings AS SELECT ?::TIMESTAMP AS observation_end', [end.to_pydatetime()])
    con.execute((ROOT / 'sql/01_orders.sql').read_text())
    tables = {}
    for name, file in [('kpis', '02_revenue'), ('cohorts', '03_cohorts'), ('rfm', '04_rfm'), ('products', '05_products'), ('product_followup', '06_product_followup'), ('basket_affinity', '07_basket_affinity')]:
        tables[name] = con.execute((ROOT / f'sql/{file}.sql').read_text()).df()
        tables[name].to_csv(OUT / f'{name}.csv', index=False)
    con.register('rfm_result', tables['rfm'])
    con.execute('CREATE OR REPLACE TABLE customer_rfm AS SELECT * FROM rfm_result')
    orders = con.execute('SELECT * FROM orders').df()
    checks = []
    def check(label, condition):
        if not bool(condition):
            raise AssertionError(label)
        checks.append(label)
    check('Invoice has exactly one customer', sales.groupby('invoice_no').customer_id.nunique().max() == 1)
    invoice_times = sales.groupby('invoice_no').invoice_date.agg(['min', 'max', 'nunique'])
    invoice_times[invoice_times['nunique'].gt(1)].to_csv(OUT / 'invoice_timestamp_audit.csv')
    check('Invoice line timestamps span at most one minute', (invoice_times['max'] - invoice_times['min']).max() <= pd.Timedelta(minutes=1))
    check('Unique order key', not orders.invoice_no.duplicated().any())
    check('Repeat orders exist', orders.order_number.max() >= 2)
    check('More than 180 days observed', (end - sales.invoice_date.min()).days >= 180)
    line_total = int(sales.amount_pence.sum())
    check('Lines reconcile exactly to orders in integer pence', line_total == int(orders.revenue_pence.sum()))
    joined = con.execute('SELECT count(*),sum(o.revenue_pence) FROM orders o JOIN customer_rfm r USING(customer_id)').fetchone()
    check('Customer join preserves order count and revenue', joined[0] == len(orders) and int(joined[1]) == line_total)
    check('RFM customer key unique', not tables['rfm'].customer_id.duplicated().any())
    check('Product output key unique', not tables['products'].stock_code.duplicated().any())
    expected_products = sales.groupby('stock_code').amount_pence.sum()
    check('Product join preserves per-product revenue', all(int(round(row.revenue_gbp*100)) == int(expected_products[row.stock_code]) for row in tables['products'].itertuples()))
    independent = orders.sort_values(['customer_id', 'order_date', 'invoice_no']).groupby('customer_id').cumcount().add(1)
    check('pandas independently verifies SQL order ranking', np.array_equal(independent.to_numpy(), orders.sort_values(['customer_id', 'order_date', 'invoice_no']).order_number.to_numpy()))
    k = tables['kpis'].iloc[0]
    customer_frequency = orders.groupby('customer_id').size()
    repeat_ids = customer_frequency[customer_frequency.ge(2)].index
    repeat_customer_pence = int(orders.loc[orders.customer_id.isin(repeat_ids), 'revenue_pence'].sum())
    check('Repeat customer revenue independently reconciles including first orders', repeat_customer_pence == int(round(k.repeat_customer_revenue_gbp*100)))
    check('Two revenue definitions ordered and bounded', 0 <= k.repeat_revenue_gbp <= k.repeat_customer_revenue_gbp <= k.revenue_gbp)
    expected_rfm = orders.groupby('customer_id').agg(last_date=('order_date','max'), frequency=('invoice_no','size'), pence=('revenue_pence','sum'))
    actual_rfm = tables['rfm'].set_index('customer_id').reindex(expected_rfm.index)
    recency = (end - expected_rfm.last_date.dt.normalize()).dt.days
    check('RFM recency independently reconciles', np.array_equal(recency, actual_rfm.recency_days))
    check('RFM frequency independently reconciles', np.array_equal(expected_rfm.frequency, actual_rfm.frequency))
    check('RFM monetary independently reconciles', np.array_equal(expected_rfm.pence, np.rint(actual_rfm.monetary_gbp*100).astype('int64')))
    expected_scores = [np.where(recency<=30,3,np.where(recency<=90,2,1)), np.where(expected_rfm.frequency>=5,3,np.where(expected_rfm.frequency>=2,2,1)), np.where(expected_rfm.pence>=100000,3,np.where(expected_rfm.pence>=30000,2,1))]
    check('All RFM scores independently reconcile', all(np.array_equal(actual_rfm[col], score) for col,score in zip(['r_score','f_score','m_score'],expected_scores)))
    expected_segment = np.select([recency.gt(90)&expected_rfm.frequency.ge(2), recency.gt(90),recency.le(30)&expected_rfm.frequency.ge(5)&expected_rfm.pence.ge(100000),expected_rfm.frequency.eq(1)],['At-risk repeat','Dormant one-time','Champions','Recent one-time'],default='Active repeat')
    check('Every RFM segment independently reconciles', np.array_equal(expected_segment, actual_rfm.segment))
    # Independent pandas product exposures and outcomes, including censored buyers.
    exposure = sales[['invoice_no','customer_id','stock_code']].merge(orders[['invoice_no','customer_id','order_date','order_number']],on=['invoice_no','customer_id'],validate='many_to_one')
    exposure = exposure[exposure.stock_code.str.fullmatch(r'[0-9]{5}[A-Za-z]*')].sort_values('order_number').drop_duplicates(['stock_code','customer_id'])
    exposure['mature'] = exposure.order_date.add(pd.Timedelta(days=90)).lt(end)
    next_dates = orders.sort_values('order_number').groupby('customer_id').order_date.shift(-1)
    next_map = pd.Series(next_dates.to_numpy(),index=orders.sort_values('order_number').invoice_no)
    exposure['returned'] = exposure.invoice_no.map(next_map).le(exposure.order_date+pd.Timedelta(days=90)) & exposure.mature
    independent_products = exposure.groupby('stock_code').agg(all_buyers=('customer_id','size'),eligible_buyers=('mature','sum'),returning_buyers=('returned','sum')).sort_index()
    product_actual = tables['product_followup'].set_index('stock_code').sort_index()
    check('All product buyer counts and 90-day outcomes independently reconcile', independent_products.equals(product_actual[independent_products.columns].astype(independent_products.dtypes)))
    eligible_products = tables['product_followup'].query('eligible_buyers >= 50').copy()
    revenue_threshold = eligible_products.revenue_gbp.quantile(.75)
    repeat_threshold = eligible_products.repeat_90_pct.median()
    priorities = eligible_products[(eligible_products.revenue_gbp.ge(revenue_threshold)) & eligible_products.repeat_90_pct.lt(repeat_threshold)].copy()
    priorities['high_revenue_threshold_gbp'] = revenue_threshold
    priorities['low_repeat_threshold_pct'] = repeat_threshold
    priorities.to_csv(OUT/'product_priorities.csv',index=False)
    tables['product_priorities'] = priorities
    tables['rfm'][tables['rfm'].segment.eq('At-risk repeat')].sort_values('monetary_gbp',ascending=False).to_csv(OUT/'at_risk_customers.csv',index=False)
    check('First plus repeat equals total', int(orders.loc[orders.order_number.eq(1), 'revenue_pence'].sum()) + int(round(k.repeat_revenue_gbp * 100)) == line_total)
    c = tables['cohorts']
    check('Retention bounded', c.retention_pct.between(0, 100).all())
    check('Cumulative retention never decreases within cohort', all(group.sort_values('days').returning_customers.diff().dropna().ge(0).all() for _, group in c.groupby('cohort')))
    check('Cohort censoring respected', all((pd.to_datetime(c.cohort) + pd.offsets.MonthEnd(0) + pd.to_timedelta(c.days, unit='D')) < end))
    # Independent customer-level cumulative outcomes, then compare every SQL cell.
    first = orders.groupby('customer_id').order_date.min()
    for row in c.itertuples():
        ids = first[first.dt.to_period('M').eq(pd.Timestamp(row.cohort).to_period('M'))].index
        candidates = orders[orders.customer_id.isin(ids) & orders.order_number.ge(2)].copy()
        expected = candidates[candidates.order_date.le(candidates.customer_id.map(first) + pd.Timedelta(days=row.days))].customer_id.nunique()
        check(f'Cohort {str(row.cohort)[:7]} / {row.days} independently reconciles', expected == row.returning_customers and len(ids) == row.customers)
    segments = tables['rfm'].groupby('segment').agg(customers=('customer_id', 'size'), revenue_gbp=('monetary_gbp', 'sum')).reset_index()
    segments.to_csv(OUT / 'segments.csv', index=False)
    identified_credits = int(credits.loc[credits.customer_id.notna(), 'amount_pence'].sum()) / 100
    audit_info = {
        'source_url': URL, 'source_sha256': hashlib.sha256(RAW.read_bytes()).hexdigest(),
        'python': sys.version, 'pandas': pd.__version__, 'duckdb': duckdb.__version__,
        'raw_rows': len(raw), 'exact_duplicate_rows_removed': duplicates,
        'invoices_with_multiple_timestamps': int(invoice_times['nunique'].gt(1).sum()),
        'identified_share_of_positive_sales_pct': float(100*line_total/positive_scope.amount_pence.sum()),
        'observation_start': str(sales.invoice_date.min()), 'observation_end_exclusive': str(end),
        'last_partial_day_sales_rows_excluded': int((df.exclusion_reason.eq('included') & df.invoice_date.ge(end)).sum()),
        'identified_credit_gbp': identified_credits,
        'sales_plus_identified_credits_gbp': float(k.revenue_gbp + identified_credits),
        'checks_passed': checks,
    }
    (OUT / 'validation.json').write_text(json.dumps(audit_info, indent=2), encoding='utf-8')
    draw(tables, segments)
    write_summary(tables, segments, audit_info)
    con.close()
    print(f'Complete: {len(checks)} checks passed. See reports/executive-summary.md', flush=True)


def draw(t, segments):
    plt.rcParams.update({'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False, 'figure.dpi': 150})
    k = t['kpis'].iloc[0]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    vals = [k.revenue_gbp-k.repeat_revenue_gbp, k.repeat_revenue_gbp]
    bars = ax.barh(['First observed order', 'Second order onward'], np.array(vals)/1e6, color=['#90a4ae', '#00796b'])
    for bar, v in zip(bars, vals):
        ax.text(bar.get_width()+.03, bar.get_y()+bar.get_height()/2, f'GBP {v/1e6:.2f}m | {v/k.revenue_gbp:.1%}', va='center')
    ax.set(xlabel='Positive sales revenue (GBP millions)', title='How much revenue comes after the first order?', xlim=(0, max(vals)/1e6*1.4))
    fig.text(.02, .01, 'Identified customers; credits excluded; first = first observed in this dataset.', fontsize=9)
    fig.tight_layout(rect=(0,.04,1,1))
    # Preserve the original requested chart, including while a Windows viewer has it open.
    if not (OUT/'figures/revenue.png').exists():
        save_chart(fig, OUT/'figures/revenue.png')
    plt.close(fig)
    fig, axes = plt.subplots(1,2,figsize=(14,5),sharex=True)
    comparisons = [(vals,['First observed order','Second order onward'],'Order-based: second order onward'),([k.revenue_gbp-k.repeat_customer_revenue_gbp,k.repeat_customer_revenue_gbp],['One-time customers','Repeat customers (all orders)'],'Customer-based: at least two orders')]
    for ax,(amounts,labels,title) in zip(axes,comparisons):
        ax.barh(labels,np.array(amounts)/1e6,color=['#90a4ae','#00796b'])
        for i,value in enumerate(amounts): ax.text(value/1e6+.07,i,f'{value/k.revenue_gbp:.1%}\nGBP {value/1e6:.2f}m',va='center',fontsize=10)
        ax.set(title=title,xlabel='Positive sales (GBP millions)',xlim=(0,k.revenue_gbp/1e6*1.18))
    fig.suptitle('Two definitions of repeat revenue — same sales denominator')
    fig.text(.02,.01,'Identified customers; before credits. Repeat-customer status uses the full observed window, including first orders.',fontsize=9)
    fig.tight_layout(rect=(0,.06,1,.94)); save_chart(fig, OUT/'figures/revenue_comparison.png'); plt.close(fig)
    pivot = t['cohorts'].pivot(index='cohort', columns='days', values='retention_pct')
    sizes = t['cohorts'].groupby('cohort').customers.first()
    fig, ax = plt.subplots(figsize=(8, 7))
    matrix = pivot.to_numpy()
    cmap = plt.get_cmap('YlGnBu').copy(); cmap.set_bad('#eeeeee')
    im = ax.imshow(matrix, cmap=cmap, vmin=0, vmax=70, aspect='auto')
    for i in range(len(pivot)):
        for j in range(len(pivot.columns)):
            v=matrix[i,j]
            ax.text(j,i,'Not mature' if pd.isna(v) else f'{v:.1f}%',ha='center',va='center',color='white' if v>45 else 'black')
    ax.set_xticks(range(len(pivot.columns)), [f'Within {d} days' for d in pivot.columns])
    ax.set_yticks(range(len(pivot)), [f'{str(d)[:7]} (n={sizes[d]:,})' for d in pivot.index])
    ax.set(title='Cumulative repeat purchase by first observed month', ylabel='Monthly cohort (eligible customers)')
    fig.colorbar(im, ax=ax, label='Customers with a second order (%)')
    fig.text(.02,.01,'Whole-cohort maturity; grey = insufficient follow-up. This is cumulative, not monthly active retention.',fontsize=8)
    fig.tight_layout(rect=(0,.04,1,1)); save_chart(fig, OUT/'figures/cohorts.png'); plt.close(fig)
    fig, ax = plt.subplots(figsize=(9, 5))
    s=segments.sort_values('revenue_gbp')
    ax.barh(s.segment, s.revenue_gbp/1000, color='#00796b')
    ax.set(xlabel='Historical positive sales (GBP thousands)',title='RFM segments: historical revenue to prioritize outreach')
    fig.tight_layout(); save_chart(fig, OUT/'figures/segments.png'); plt.close(fig)
    p=t['products'].head(12)
    fig, ax=plt.subplots(figsize=(9,6))
    ax.scatter(p.repeat_90_pct,p.revenue_gbp/1000,s=p.eligible_first_buyers*1.5,alpha=.65,color='#00796b')
    for r in p.itertuples(): ax.annotate(r.stock_code,(r.repeat_90_pct,r.revenue_gbp/1000),fontsize=8)
    ax.set(xlabel='First-basket buyers who placed another order within 90 days (%)',ylabel='All-period product revenue (GBP thousands)',title='Products: revenue versus subsequent customer repeat purchase')
    fig.text(.02,.01,'Top 12 by revenue with >=50 mature first buyers. Bubble area = buyers. Product associations, not causal lift.',fontsize=8)
    fig.tight_layout(rect=(0,.04,1,1)); save_chart(fig, OUT/'figures/products.png'); plt.close(fig)
    p=t['product_followup'].query('eligible_buyers >= 50').head(15)
    flagged=set(t['product_priorities'].stock_code)
    fig,ax=plt.subplots(figsize=(10,6))
    ax.scatter(p.repeat_90_pct,p.revenue_gbp/1000,s=p.eligible_buyers*.7,alpha=.7,color=['#d95f02' if sku in flagged else '#00796b' for sku in p.stock_code])
    for i,row in enumerate(p.itertuples()):
        ax.annotate(f'{row.stock_code} (n={row.eligible_buyers})',(row.repeat_90_pct,row.revenue_gbp/1000),xytext=(4,5 if i%2 else -12),textcoords='offset points',fontsize=8)
    priority=t['product_priorities'].iloc[0]
    ax.axvline(priority.low_repeat_threshold_pct,color='#777777',linestyle='--',label='Median eligible-product repeat rate')
    ax.axhline(priority.high_revenue_threshold_gbp/1000,color='#777777',linestyle=':',label='75th percentile eligible-product revenue')
    ax.set(xlabel='Any later purchase within 90 days of first SKU purchase (%)',ylabel='All-window sales (GBP thousands)',title='High sales, weak follow-up: all product buyers')
    ax.legend(fontsize=8)
    fig.text(.02,.01,'Top 15 eligible SKUs by sales; orange = flagged. n = buyers with full 90-day follow-up; area = n.',fontsize=9)
    fig.tight_layout(rect=(0,.04,1,1));save_chart(fig, OUT/'figures/product_followup.png');plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(20,14))
    for ax,name in zip(axes.flat,['revenue_comparison','cohorts','segments','product_followup']):
        ax.imshow(plt.imread(OUT/f'figures/{name}.png'));ax.axis('off')
    fig.suptitle('Revenue & Retention Analytics | Historical positive sales, identified customers',fontsize=20)
    fig.tight_layout(rect=(0,0,1,.96));save_chart(fig, OUT/'figures/dashboard.png');plt.close(fig)


def write_summary(t, segments, audit):
    k=t['kpis'].iloc[0]; c=t['cohorts']; r=t['rfm']; p=t['products']
    mature=c[c.days.eq(90)].sort_values('retention_pct',ascending=False)
    best=mature.iloc[0]; worst=mature.iloc[-1]
    risk=r[r.segment.eq('At-risk repeat')]
    product=t['product_priorities'].iloc[0]
    pooled=mature.returning_customers.sum()/mature.customers.sum()*100
    summary=f'''# Executive summary

Real UCI Online Retail transactions, not synthetic data. Observation ends before {audit['observation_end_exclusive'][:10]}; GBP positive sales among identified customers. These are historical observations, not forecasts.

## Five calculated findings

1. **{k.repeat_revenue_pct:.2f}%** of GBP **{k.revenue_gbp:,.2f}** positive sales comes from the second observed order onward (GBP **{k.repeat_revenue_gbp:,.2f}**). Evidence: `kpis.csv`, `sql/02_revenue.sql`.
2. Customers with at least two observed orders generate **{k.repeat_customer_revenue_pct:.2f}%** of sales (**GBP {k.repeat_customer_revenue_gbp:,.2f}**), INCLUDING their first orders. **{int(r.frequency.ge(2).sum()):,}/{int(k.customers):,} customers ({(r.frequency.ge(2)).mean()*100:.2f}%)** are repeat buyers. This differs from finding 1 by **{k.repeat_customer_revenue_pct-k.repeat_revenue_pct:.2f} percentage points**. Evidence: `rfm.csv`, `kpis.csv`.
3. Mature cohorts have a pooled 90-day repeat rate of **{pooled:.2f}%**. Highest: **{str(best.cohort)[:7]}**, **{best.retention_pct:.2f}%** ({int(best.returning_customers)}/{int(best.customers)}); lowest: **{str(worst.cohort)[:7]}**, **{worst.retention_pct:.2f}%** ({int(worst.returning_customers)}/{int(worst.customers)}). Evidence: `cohorts.csv`. Seasonality and left truncation prevent a causal ranking of acquisition quality.
4. **{len(risk):,} repeat customers** have not bought for more than 90 days. They generated GBP **{risk.monetary_gbp.sum():,.2f}**, **{risk.monetary_gbp.sum()/k.revenue_gbp*100:.2f}%** of historical sales. Evidence: `rfm.csv`, `segments.csv`. This is an inactivity proxy, not a churn probability.
5. The high-sales / low-repeat screen flags **{len(t['product_priorities'])} products**. The highest-revenue flagged SKU is **{product.stock_code} ({product.description})**: GBP **{product.revenue_gbp:,.2f}** sales, **{int(product.returning_buyers)}/{int(product.eligible_buyers)} mature buyers ({product.repeat_90_pct:.2f}%)** who placed another order within 90 days of their first purchase of that SKU; **{int(product.censored_buyers)}** buyers lack follow-up. High sales threshold: **GBP {product.high_revenue_threshold_gbp:,.2f}**; low repeat threshold: **{product.low_repeat_threshold_pct:.2f}%**. Evidence: `product_priorities.csv`, `product_followup.csv`. Buyers can appear under multiple SKUs; these counts are not additive.

### Additional product diagnosis: all buyers, not only first baskets

Anchor each customer/SKU at the first observed purchase of that SKU; follow for 90 elapsed days, requiring anchor + 90 days < exclusive observation cutoff. The outcome counts customers who placed another order within 90 days, even if the later invoice contains a different SKU. Each customer counts once per SKU. Censored buyers are excluded from the rate and explicitly counted. Among products with >=50 eligible buyers, high revenue means >= the 75th percentile of all-window product sales; low repeat means below the median product repeat rate. Thresholds are descriptive screening rules, not statistical significance or causal effects. See `product_followup.csv` and `product_priorities.csv`.

{product_table(t['product_priorities'])}

## Three defensible actions

1. **Test a second-order onboarding campaign**: finding 1 shows the value of subsequent orders, while finding 3 gives a {pooled:.2f}% mature 90-day baseline. Randomize eligible first buyers into contact and holdout; measure incremental 90-day repeat purchase, net revenue and discount cost. Do not claim an uplift before the experiment.
2. **Pilot a targeted win-back** among the {len(risk):,} inactive repeat customers (finding 4), prioritizing monetary value and checking consent and recent credits. Use a holdout; judge incremental net margin rather than opens. Historical revenue is not recoverable revenue.
3. **Inspect the post-purchase experience for product {product.stock_code} and the flagged SKUs** (finding 5): audit merchandise returns and basket context, then test a relevant follow-up offer. Its {product.repeat_90_pct:.2f}% rate is an association; seasonality, wholesale purchasing and buyer mix may explain it. Avoid delisting on this evidence alone.

Also prioritize the all-buyer screening list above: it directly answers the high-sales / low-follow-up question. Check credits and wholesale basket concentration before running a product-specific follow-up experiment; use a randomized holdout and incremental net margin once cost data are available.

## Revenue and data caveats

Identified credit lines total GBP **{audit['identified_credit_gbp']:,.2f}**; positive sales plus these signed credits are GBP **{audit['sales_plus_identified_credits_gbp']:,.2f}**. This reconciliation is NOT a net repeat-revenue attribution: original invoices cannot be linked reliably. Missing-ID sales are outside the customer KPI. Exact duplicate removal is an assumption, not proof of erroneous records. See `cleaning_audit.csv` and methodology.
'''
    (OUT/'executive-summary.md').write_text(summary,encoding='utf-8')
    readme = ROOT / 'README.md'
    text = readme.read_text(encoding='utf-8')
    begin, finish = '<!-- FINDINGS:START -->', '<!-- FINDINGS:END -->'
    findings = summary.split('## Five calculated findings\n\n')[1].split('\n## Three defensible actions')[0]
    text = text.split(begin)[0] + begin + '\n\n' + findings.strip() + '\n\n' + finish + text.split(finish)[1]
    readme.write_text(text, encoding='utf-8')


def product_table(products):
    lines=['| SKU | Product | Sales GBP | All buyers | Eligible 90d | Censored | Customers who placed another order within 90 days | Repeat 90d |','|---|---|---:|---:|---:|---:|---:|---:|']
    for x in products.head(10).itertuples():
        lines.append(f'| {x.stock_code} | {x.description} | {x.revenue_gbp:,.2f} | {x.all_buyers} | {x.eligible_buyers} | {x.censored_buyers} | {x.returning_buyers} | {x.repeat_90_pct:.2f}% |')
    return '\n'.join(lines) + '\n\nTop 10 flagged products by sales shown; full screening list: `product_priorities.csv`.'


if __name__ == '__main__':
    main()
