# Analytical decisions

## Scope and source

Original, non-synthetic [UCI Online Retail](https://archive.ics.uci.edu/dataset/352/online-retail), Daqing Chen (2015), DOI [10.24432/C5BW33](https://doi.org/10.24432/C5BW33), CC BY 4.0. Transactions from 1 December 2010 to 9 December 2011, UK gift retailer with many wholesale customers. CustomerID is the documented customer identifier, not an inferred email/name match. No categories or acquisition channels exist: analyse StockCode products without inventing categories. Source has no payment or cost tables; do not infer profit.

## Preparation

Preserve the downloaded workbook and record its SHA256 in validation.json. Remove exact duplicates on all eight source fields; identical lines could be legitimate split lines, so this is an explicit assumption. Mutually exclusive exclusion reasons, in priority order: C-prefixed invoice; negative quantity; zero quantity; nonpositive price; missing customer ID. Audit gives signed amounts and counts AFTER duplicate removal, BEFORE observation cutoff. Do not impute customer identities. Positive sales with missing IDs cannot be classified as first or repeat and are excluded from the KPI, not called new customers.

Last date in the source is incomplete. End the observation window at its midnight, exclusive. Exclude that day from sales and credit diagnostics; settings records the cutoff. No timezone is documented; use naive source time consistently. Monetary calculations use Quantity × UnitPrice rounded to integer pence per line (half away from zero); integer sums allow exact revenue checks. This is a line-rounding policy, not a claimed accounting standard.

## Sales, cancellations and merchandise returns

Main KPI is positive invoiced sales among identified customers, not accounting net revenue. All C invoices and negative quantities are outside purchase counts. Signed credit totals are reported separately, with known customer IDs and the same observation cutoff. They may contain adjustments; no guaranteed original invoice reference exists. Do not fabricate FIFO matching or subtract credits from an arbitrary next order. A purchase fully refunded through merchandise returns still counts as an observed positive purchase in the main definition. True retained net revenue would require reliable merchandise-return-to-order matching. No margin or tax completeness claim is made.

## Order grain and repeat revenue

Aggregate retained lines to (invoice_no, customer_id) before ranking. Assert invoices have one customer. The source has 30 retained invoices spanning two timestamps one minute apart: keep one invoice dated at its first line, export these cases in invoice_timestamp_audit.csv, and fail if any span exceeds one minute. Order sequence = date/time then invoice number for deterministic ties; simultaneous invoices can be split purchases. Repeat revenue includes only order_number >= 2, not the first order of customers who later repeat. First means first OBSERVED: existing clients before December 2010 are left truncated. This is not customer lifetime revenue or a causal value of retention.

## Cohorts

Monthly cohort = month of first observed positive order. For horizon H, the repeat-purchase outcome is any subsequent invoice by first_timestamp + H days, inclusive. This is cumulative repeat purchase, not activity specifically on day H or in month H. Eligibility requires cohort calendar month end + H days < exclusive cutoff, conservatively giving every possible entrant enough follow-up. Grey cells mean unobserved, not zero. Different horizons include different cohorts; compare the common mature cohort set when discussing evolution. For a pooled 90-day rate use the number of customers who placed another order within 90 days / summed eligible customers for the 90-day pooled rate, never an unweighted average. First-month clients may include established customers; seasonality and wholesale behavior confound cohort ranking. Small denominators are labelled; no significance or causal improvement claims.

## RFM and inactivity

Snapshot is exclusive cutoff date. R = days since last observed order date; F = distinct positive invoices; M = positive sales GBP. R scores: <=30 / 31–90 / >90 days -> 3/2/1. F: >=5 / 2–4 / 1 -> 3/2/1. M: >=1000 / 300–999.99 / <300 GBP -> 3/2/1. Thresholds are transparent business heuristics, not fitted or validated predictions. Segment priority: inactive repeat (>90 days, F>=2), dormant one-time (>90 days), champions (R<=30, F>=5, M>=1000), recent one-time (F=1), active repeat (remaining). Longer tenure creates more opportunity to accumulate F/M. Inactivity is a churn proxy for a non-contractual business, not observed churn or probability. No machine learning is justified without a prediction cutoff, temporal holdout and business loss definition.

## Products

First-basket product exposure is distinct customer × product. Only customers whose individual first order has full 90-day follow-up are eligible. Product repeat rate means subsequent purchase of ANY product within 90 days, not repurchase of the same SKU. Only >=50 exposed buyers reported. Product comparisons retain codes with five digits and optional letter suffixes; this heuristic excludes service codes such as POST (postage) and M (manual) from product recommendations. They remain in the sales KPI when otherwise eligible. Revenue is all-window product sales, whereas repeat outcome is mature first buyers: label both. Descriptions may vary; alphabetically first description is a display label only. Customers may appear under several products; no additive product attribution. Basket mix, tenure and season explain associations; test offers before claiming effects.

## Validation

Execution fails on broken uniqueness, order consistency, line/order revenue reconciliation, customer joins changing counts/revenue, ranking mismatch, missing repeated orders or insufficient history. Every cohort numerator and denominator is independently recalculated in pandas. Validation results, versions, hash and cutoff are saved in reports/validation.json. SQL product joins aggregate exposures first; product revenue is a separate one-row-per-SKU table.
