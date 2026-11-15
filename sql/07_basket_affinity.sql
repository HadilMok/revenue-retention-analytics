-- Basket co-occurrence among top 20 merchandise SKUs by invoice coverage.
-- Support and lift are descriptive, not a recommendation treatment effect.
WITH baskets AS (
 SELECT DISTINCT invoice_no,stock_code FROM sales
 WHERE regexp_full_match(stock_code,'[0-9]{5}[A-Za-z]*')
), popular AS (
 SELECT stock_code,count(*) AS baskets_with_sku FROM baskets
 GROUP BY stock_code ORDER BY baskets_with_sku DESC,stock_code LIMIT 20
), pairs AS (
 SELECT a.stock_code AS sku_a,b.stock_code AS sku_b,count(*) AS pair_baskets
 FROM baskets a JOIN baskets b ON a.invoice_no=b.invoice_no AND a.stock_code<b.stock_code
 JOIN popular p ON a.stock_code=p.stock_code JOIN popular q ON b.stock_code=q.stock_code
 GROUP BY a.stock_code,b.stock_code HAVING count(*)>=20
)
SELECT pairs.*,p.baskets_with_sku AS baskets_a,q.baskets_with_sku AS baskets_b,
 (SELECT count(*) FROM orders) AS total_baskets,
 100.0*pair_baskets/(SELECT count(*) FROM orders) AS support_pct,
 1.0*pair_baskets*(SELECT count(*) FROM orders)/(p.baskets_with_sku*q.baskets_with_sku) AS lift
FROM pairs JOIN popular p ON sku_a=p.stock_code JOIN popular q ON sku_b=q.stock_code
ORDER BY lift DESC, pair_baskets DESC;
