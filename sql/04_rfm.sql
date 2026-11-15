WITH metrics AS (
 SELECT customer_id, date_diff('day', max(order_date)::DATE, (SELECT observation_end::DATE FROM settings)) AS recency_days,
 count(*) AS frequency, sum(revenue_pence)/100.0 AS monetary_gbp
 FROM orders GROUP BY customer_id
), scored AS (
 SELECT *, CASE WHEN recency_days<=30 THEN 3 WHEN recency_days<=90 THEN 2 ELSE 1 END AS r_score,
 CASE WHEN frequency>=5 THEN 3 WHEN frequency>=2 THEN 2 ELSE 1 END AS f_score,
 CASE WHEN monetary_gbp>=1000 THEN 3 WHEN monetary_gbp>=300 THEN 2 ELSE 1 END AS m_score
 FROM metrics
)
SELECT *, CASE WHEN recency_days>90 AND frequency>=2 THEN 'At-risk repeat'
 WHEN recency_days>90 THEN 'Dormant one-time'
 WHEN recency_days<=30 AND frequency>=5 AND monetary_gbp>=1000 THEN 'Champions'
 WHEN frequency=1 THEN 'Recent one-time' ELSE 'Active repeat' END AS segment
FROM scored;
