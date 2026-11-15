# Added definitions and RFM verification

## Two repeat-revenue measures

Both use the same denominator: positive invoiced sales among identified customers, after duplicate/exclusion rules and before credits, within the documented window.

1. **Order-based**: sum revenue where customer order sequence >=2 / total revenue. First orders are excluded from the numerator even if the customer eventually repeats.
2. **Customer-based**: identify customers with >=2 observed invoices; include ALL of their invoices, including their first / total revenue. The difference is first-order revenue of future repeaters. Customers are classified retrospectively using the full window; do not use that status as a feature to predict the first purchase's outcome.

Both have independent pandas reconciliation. Customer-based share must be >= order-based share and <=100%. Preserve revenue.png; revenue_comparison.png adds the second definition alongside it.

## Product follow-up

The original products.csv remains a FIRST-BASKET exposure analysis. The added product_followup.csv includes ALL identified buyers of each merchandise SKU, one row per customer/SKU exposure internally. Anchor = that customer's first observed invoice containing that SKU. A subsequent invoice (higher customer order_number, including deterministic ties) identifies customers who placed another order within 90 days, whether or not the SKU is bought again. This measures subsequent customer activity, not SKU replenishment or causal retention lift.

Require anchor timestamp +90 days < exclusive observation end (2011-12-09 midnight). Later anchors are censored and excluded from numerator and denominator. Export all, eligible and censored buyer counts. A subsequent order placed beyond 90 days does not count in this outcome. A customer's repeated appearances in invoice lines or baskets do not increase their denominator for that SKU. The full product output's counts and outcomes are independently reconstructed in pandas.

Screen products with >=50 eligible buyers. Among those, high sales = all-window positive sales >=75th percentile of eligible-product revenue (pandas linear quantile); weak follow-up = 90-day repeat rate below the unweighted median across eligible products. These thresholds avoid an unspecified notion of 'high' or 'low'; they do not establish statistical significance. Export thresholds on every priority row. Revenue covers the full window, whereas retention covers mature buyers, explicitly labelled. No universal repeat-rate baseline across first-order cohorts and SKU buyers is assumed: these are different populations.

Merchandise codes follow five digits with optional alphabetic suffix, a documented heuristic that excludes POST/M service adjustments from product screening, but not from otherwise eligible sales totals. Customers appear under multiple SKUs; product exposure counts are not additive. Check wholesale purchasing, seasonality and credits before taking product action.

## RFM and clients at risk

Snapshot: 2011-12-09, after excluding that incomplete day. Recency = calendar days since last retained invoice; frequency = distinct retained invoices, not number of lines or units; monetary = summed positive sales, not profit or net receipts. All three metrics are independently recalculated in pandas.

| Score | Recency R (smaller is better) | Frequency F | Monetary M (GBP) |
|---|---|---|---|
| 3 | <=30 days | >=5 invoices | >=1000 |
| 2 | 31–90 days | 2–4 invoices | 300 to <1000 |
| 1 | >90 days | 1 invoice | <300 |

Score direction is consistent: 3 means stronger observed engagement/value. Segments apply mutually exclusive rules in this priority: at-risk repeat (R>90 days and F>=2), dormant one-time (R>90 and F=1), champions (R<=30, F>=5, M>=1000), recent one-time (remaining F=1), active repeat (remaining). Segment names describe the whole rule, not a learned score. Monetary value prioritizes outreach WITHIN the at-risk list rather than determining inactivity.

`at_risk_customers.csv` is sorted by descending historical monetary value. It is not a list of certain churners and historical revenue is not promised future recoverable revenue. There is no labelled contractual churn event in this dataset. The 90-day threshold is a transparent heuristic; individual purchase cadence and customer tenure could improve it in a later extension. No supervised model is claimed. Unit tests check the exact 90-day boundary, an inactive repeater, an inactive one-time customer and a monetary threshold. The pipeline independently checks every RFM score and every segment assignment.

## Basket affinity

SQL 07 deduplicates invoice/SKU presence, selects the 20 SKUs with highest invoice coverage and reports pairs with >=20 joint baskets. Support = pair baskets / all retained orders. Lift = P(A and B)/(P(A)P(B)), using the same order universe. Lift >1 means more co-occurrence than independence in this sample, not proof that a bundle increases sales. This is supporting basket evidence; no revenue is summed across pair joins.
