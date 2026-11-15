-- Product presence on FIRST basket; each customer counted once per product.
-- 90-day mature customers only. Associations are not causal effects.
WITH firsts AS (
 SELECT * FROM orders WHERE order_number=1
 AND order_date+INTERVAL '90 days' < (SELECT observation_end FROM settings)
), exposures AS (
 SELECT DISTINCT f.customer_id, s.stock_code, f.order_date
 FROM firsts f JOIN sales s USING(invoice_no, customer_id)
 WHERE regexp_full_match(s.stock_code, '[0-9]{5}[A-Za-z]*')
), outcomes AS (
 SELECT e.customer_id, e.stock_code,
 max(CASE WHEN o.order_number>=2 AND o.order_date<=e.order_date+INTERVAL '90 days' THEN 1 ELSE 0 END) AS returned
 FROM exposures e JOIN orders o USING(customer_id) GROUP BY e.customer_id,e.stock_code
), revenues AS (
 SELECT stock_code, sum(amount_pence)/100.0 AS revenue_gbp, min(description) AS description
 FROM sales GROUP BY stock_code
)
SELECT r.*, count(*) AS eligible_first_buyers, 100.0*avg(o.returned) AS repeat_90_pct
FROM outcomes o JOIN revenues r USING(stock_code)
GROUP BY r.stock_code,r.revenue_gbp,r.description HAVING count(*)>=50
ORDER BY revenue_gbp DESC;
