WITH classified AS (
 SELECT *, count(*) OVER (PARTITION BY customer_id) AS customer_orders FROM orders
)
SELECT count(*) AS orders, count(DISTINCT customer_id) AS customers,
 sum(revenue_pence)/100.0 AS revenue_gbp,
 sum(CASE WHEN order_number>=2 THEN revenue_pence ELSE 0 END)/100.0 AS repeat_revenue_gbp,
 100.0*sum(CASE WHEN order_number>=2 THEN revenue_pence ELSE 0 END)/sum(revenue_pence) AS repeat_revenue_pct,
 sum(CASE WHEN customer_orders>=2 THEN revenue_pence ELSE 0 END)/100.0 AS repeat_customer_revenue_gbp,
 100.0*sum(CASE WHEN customer_orders>=2 THEN revenue_pence ELSE 0 END)/sum(revenue_pence) AS repeat_customer_revenue_pct
FROM classified;
