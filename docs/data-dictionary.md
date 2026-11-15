# Data dictionary

## Raw workbook (one invoice/product line)

| Source | Clean name | Type / unit | Meaning |
|---|---|---|---|
| InvoiceNo | invoice_no | string | Invoice identifier; C prefix denotes cancellation |
| StockCode | stock_code | string | Product code; preserve nonnumeric codes |
| Description | description | nullable string | Product label, may vary for a SKU |
| Quantity | quantity | integer | Units; negative quantities are credit/adjustment candidates |
| InvoiceDate | invoice_date | naive timestamp | Invoice creation time |
| UnitPrice | unit_price | numeric GBP | Unit selling price |
| CustomerID | customer_id | nullable string | Documented stable customer identifier |
| Country | country | string | Customer country |

## Derived tables (DuckDB: data/processed/retail.duckdb)

| Table / grain | Fields | Definition |
|---|---|---|
| sales / retained invoice line | raw clean names, amount_pence | Positive sales, known ID, no C invoice; amount_pence = rounded quantity × price × 100 |
| credits / deduplicated credit line | raw fields, amount_pence, exclusion_reason | C invoices OR negative quantities; may lack customer ID |
| settings / one row | observation_end | Exclusive midnight cutoff; last source date excluded |
| orders / one invoice | invoice_no, customer_id, order_date, revenue_pence, order_number | Summed positive lines; timestamp minimum; customer sequence starts at 1 |
| customer_rfm / one customer | customer_id, recency_days, frequency, monetary_gbp, r_score, f_score, m_score, segment | Snapshot metrics and heuristic segments; see methodology |

## Exported reports

| File / grain | Fields and units |
|---|---|
| kpis.csv / one row | orders; customers; revenue_gbp; repeat_revenue_gbp; repeat_revenue_pct (0–100) |
| cohorts.csv / monthly cohort × eligible horizon | cohort (first observed month); days (30/60/90); customers (denominator); returning_customers; retention_pct (0–100 cumulative) |
| rfm.csv / customer | Same fields as customer_rfm |
| segments.csv / segment | segment; customers; revenue_gbp (historical, not future opportunity) |
| products.csv / product with >=50 mature first buyers | stock_code; description; revenue_gbp (all-window); eligible_first_buyers; repeat_90_pct (any subsequent SKU, 0–100) |
| cleaning_audit.csv / exclusion reason | exclusion_reason (priority classification); rows; amount_pence (signed); after deduplication, before cutoff |
| customer_coverage.csv / identified status | customer_scope; rows; revenue_pence; revenue_gbp; positive sales before customer exclusion, within observation window |
| invoice_timestamp_audit.csv / invoice with multiple timestamps | invoice_no; min; max; nunique (timestamp count); date is normalized to first line in orders |
| validation.json / run | Source/hash, versions, raw/duplicate counts, cutoff, credit diagnostics, successful assertions |

CSV amounts use a decimal point. GBP means pounds sterling. No foreign-exchange conversion. Reports are regenerated, never edited manually.

## Review additions

| Output | Added fields / grain |
|---|---|
| kpis.csv | repeat_customer_revenue_gbp and repeat_customer_revenue_pct: all invoices of customers with >=2 observed invoices, including first |
| product_followup.csv / SKU | stock_code, description, revenue_gbp (all-window); all_buyers; eligible_buyers (full 90d since first SKU purchase); censored_buyers; returning_buyers (any later invoice within 90d); repeat_90_pct = returning / eligible ×100 |
| product_priorities.csv / flagged SKU | Product-followup fields plus high_revenue_threshold_gbp (eligible-products' revenue Q75) and low_repeat_threshold_pct (eligible-products' median repeat rate); requires >=50 eligible buyers |
| at_risk_customers.csv / customer | RFM fields, restricted to recency_days>90 and frequency>=2; sorted by monetary_gbp descending |
| basket_affinity.csv / SKU pair | sku_a, sku_b, pair_baskets, baskets_a, baskets_b, total_baskets, support_pct, lift; among top 20 SKU invoice frequencies, minimum 20 joint baskets |

See review-methodology.md for follow-up eligibility, score boundaries and retrospective classification caveats.
