-- One exposure per customer / SKU, anchored at their first purchase of that SKU.
-- Outcome: any later invoice, even another SKU, within 90 elapsed days.
WITH exposures AS (
 SELECT s.stock_code, o.customer_id, min(o.order_number) AS anchor_number
 FROM sales s JOIN orders o USING(invoice_no, customer_id)
 WHERE regexp_full_match(s.stock_code, '[0-9]{5}[A-Za-z]*')
 GROUP BY s.stock_code, o.customer_id
), anchors AS (
 SELECT e.*, o.order_date AS anchor_date,
 o.order_date+INTERVAL '90 days' < (SELECT observation_end FROM settings) AS mature
 FROM exposures e JOIN orders o ON e.customer_id=o.customer_id AND e.anchor_number=o.order_number
), outcomes AS (
 SELECT a.stock_code, a.customer_id, a.mature,
 max(CASE WHEN o.order_number>a.anchor_number
 AND o.order_date<=a.anchor_date+INTERVAL '90 days' THEN 1 ELSE 0 END) AS returned
 FROM anchors a JOIN orders o USING(customer_id)
 GROUP BY a.stock_code,a.customer_id,a.mature
), counts AS (
 SELECT stock_code, count(*) AS all_buyers,
 count(*) FILTER(WHERE mature) AS eligible_buyers,
 count(*) FILTER(WHERE NOT mature) AS censored_buyers,
 sum(CASE WHEN mature THEN returned ELSE 0 END)::BIGINT AS returning_buyers
 FROM outcomes GROUP BY stock_code
), revenues AS (
 SELECT stock_code,min(description) AS description,sum(amount_pence)/100.0 AS revenue_gbp
 FROM sales GROUP BY stock_code
)
SELECT r.*, c.all_buyers,c.eligible_buyers,c.censored_buyers,c.returning_buyers,
 100.0*c.returning_buyers/nullif(c.eligible_buyers,0) AS repeat_90_pct
FROM counts c JOIN revenues r USING(stock_code) ORDER BY revenue_gbp DESC;
