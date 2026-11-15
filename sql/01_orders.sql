-- One row per invoice BEFORE ranking or joining customer attributes.
CREATE OR REPLACE TABLE orders AS
WITH aggregated AS (
 SELECT invoice_no, customer_id, min(invoice_date) AS order_date,
        sum(amount_pence)::BIGINT AS revenue_pence
 FROM sales GROUP BY invoice_no, customer_id
)
SELECT *, row_number() OVER(PARTITION BY customer_id ORDER BY order_date, invoice_no) AS order_number
FROM aggregated;
