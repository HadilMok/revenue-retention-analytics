# Executive summary

Real UCI Online Retail transactions, not synthetic data. Observation ends before 2011-12-09; GBP positive sales among identified customers. These are historical observations, not forecasts.

## Five calculated findings

1. **78.88%** of GBP **8,702,879.23** positive sales comes from the second observed order onward (GBP **6,864,616.10**). Evidence: `kpis.csv`, `sql/02_revenue.sql`.
2. Customers with at least two observed orders generate **92.95%** of sales (**GBP 8,088,980.94**), INCLUDING their first orders. **2,843/4,337 customers (65.55%)** are repeat buyers. This differs from finding 1 by **14.07 percentage points**. Evidence: `rfm.csv`, `kpis.csv`.
3. Mature cohorts have a pooled 90-day repeat rate of **47.45%**. Highest: **2010-12**, **59.55%** (527/885); lowest: **2011-05**, **38.38%** (109/284). Evidence: `cohorts.csv`. Seasonality and left truncation prevent a causal ranking of acquisition quality.
4. **603 repeat customers** have not bought for more than 90 days. They generated GBP **677,953.16**, **7.79%** of historical sales. Evidence: `rfm.csv`, `segments.csv`. This is an inactivity proxy, not a churn probability.
5. The high-sales / low-repeat screen flags **149 products**. The highest-revenue flagged SKU is **22423 (REGENCY CAKESTAND 3 TIER)**: GBP **142,137.25** sales, **425/691 mature buyers (61.51%)** who placed another order within 90 days of their first purchase of that SKU; **190** buyers lack follow-up. High sales threshold: **GBP 7,093.72**; low repeat threshold: **67.31%**. Evidence: `product_priorities.csv`, `product_followup.csv`. Buyers can appear under multiple SKUs; these counts are not additive.

### Additional product diagnosis: all buyers, not only first baskets

Anchor each customer/SKU at the first observed purchase of that SKU; follow for 90 elapsed days, requiring anchor + 90 days < exclusive observation cutoff. The outcome counts customers who placed another order within 90 days, even if the later invoice contains a different SKU. Each customer counts once per SKU. Censored buyers are excluded from the rate and explicitly counted. Among products with >=50 eligible buyers, high revenue means >= the 75th percentile of all-window product sales; low repeat means below the median product repeat rate. Thresholds are descriptive screening rules, not statistical significance or causal effects. See `product_followup.csv` and `product_priorities.csv`.

| SKU | Product | Sales GBP | All buyers | Eligible 90d | Censored | Customers who placed another order within 90 days | Repeat 90d |
|---|---|---:|---:|---:|---:|---:|---:|
| 22423 | REGENCY CAKESTAND 3 TIER | 142,137.25 | 881 | 691 | 190 | 425 | 61.51% |
| 85123A | CREAM HANGING HEART T-LIGHT HOLDER | 100,544.50 | 856 | 690 | 166 | 405 | 58.70% |
| 85099B | JUMBO BAG RED RETROSPOT | 85,019.74 | 635 | 471 | 164 | 307 | 65.18% |
| 47566 | PARTY BUNTING | 68,785.23 | 708 | 610 | 98 | 388 | 63.61% |
| 84879 | ASSORTED COLOUR BIRD ORNAMENT | 56,385.99 | 678 | 481 | 197 | 305 | 63.41% |
| 22502 | PICNIC BASKET WICKER 60 PIECES | 47,348.35 | 175 | 173 | 2 | 106 | 61.27% |
| 22386 | JUMBO BAG PINK POLKADOT | 37,236.46 | 372 | 292 | 80 | 194 | 66.44% |
| 22197 | POPCORN HOLDER | 37,111.08 | 407 | 286 | 121 | 175 | 61.19% |
| 82484 | WOOD BLACK BOARD ANT WHITE FINISH | 34,414.71 | 285 | 228 | 57 | 141 | 61.84% |
| 22720 | SET OF 3 CAKE TINS PANTRY DESIGN  | 33,230.30 | 640 | 480 | 160 | 309 | 64.38% |

Top 10 flagged products by sales shown; full screening list: `product_priorities.csv`.

## Three defensible actions

1. **Test a second-order onboarding campaign**: finding 1 shows the value of subsequent orders, while finding 3 gives a 47.45% mature 90-day baseline. Randomize eligible first buyers into contact and holdout; measure incremental 90-day repeat purchase, net revenue and discount cost. Do not claim an uplift before the experiment.
2. **Pilot a targeted win-back** among the 603 inactive repeat customers (finding 4), prioritizing monetary value and checking consent and recent credits. Use a holdout; judge incremental net margin rather than opens. Historical revenue is not recoverable revenue.
3. **Inspect the post-purchase experience for product 22423 and the flagged SKUs** (finding 5): audit merchandise returns and basket context, then test a relevant follow-up offer. Its 61.51% rate is an association; seasonality, wholesale purchasing and buyer mix may explain it. Avoid delisting on this evidence alone.

Also prioritize the all-buyer screening list above: it directly answers the high-sales / low-follow-up question. Check credits and wholesale basket concentration before running a product-specific follow-up experiment; use a randomized holdout and incremental net margin once cost data are available.

## Revenue and data caveats

Identified credit lines total GBP **-439,900.40**; positive sales plus these signed credits are GBP **8,262,978.83**. This reconciliation is NOT a net repeat-revenue attribution: original invoices cannot be linked reliably. Missing-ID sales are outside the customer KPI. Exact duplicate removal is an assumption, not proof of erroneous records. See `cleaning_audit.csv` and methodology.
