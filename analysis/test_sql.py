"""Small adversarial fixtures: boundary dates, split lines and customer joins."""
from pathlib import Path
import unittest
import duckdb

SQL = Path(__file__).resolve().parents[1] / 'sql'


class SqlDefinitionsTest(unittest.TestCase):
    def setUp(self):
        self.con = duckdb.connect()
        self.con.execute("CREATE TABLE settings AS SELECT TIMESTAMP '2021-05-02' observation_end")
        self.con.execute('CREATE TABLE sales(invoice_no VARCHAR, customer_id VARCHAR, invoice_date TIMESTAMP, amount_pence BIGINT)')
        self.con.execute("""INSERT INTO sales VALUES
        ('A','1','2021-01-01 10:00',1000), ('A','1','2021-01-01 10:00',500),
        ('B','1','2021-01-31 10:00',2000),
        ('C','2','2021-01-20 10:00',4000),
        ('D','3','2021-02-01 10:00',1000),
        ('E','3','2021-05-01 09:59',1000)""")
        self.con.execute((SQL/'01_orders.sql').read_text())

    def tearDown(self):
        self.con.close()

    def test_split_lines_do_not_become_repeat_orders(self):
        self.assertEqual(self.con.execute("SELECT revenue_pence,order_number FROM orders WHERE invoice_no='A'").fetchone(),(1500,1))
        self.assertEqual(self.con.execute('SELECT count(*) FROM orders').fetchone()[0],5)

    def test_first_order_of_repeat_customer_excluded_from_numerator(self):
        k=self.con.execute((SQL/'02_revenue.sql').read_text()).df().iloc[0]
        self.assertEqual(k.repeat_revenue_gbp,30)
        self.assertEqual(k.revenue_gbp,95)
        self.assertEqual(k.repeat_customer_revenue_gbp,55)

    def test_rfm_risk_boundary_and_frequency(self):
        self.con.execute("CREATE TABLE orders_backup AS SELECT * FROM orders")
        self.con.execute('DELETE FROM orders')
        self.con.execute("""INSERT INTO orders VALUES
        ('X','old_repeat','2021-01-01',10000,1),('Y','old_repeat','2021-01-31',20000,2),
        ('Z','boundary_repeat','2021-01-01',10000,1),('W','boundary_repeat','2021-02-01',20000,2),
        ('V','old_once','2021-01-01',10000,1)""")
        r=self.con.execute((SQL/'04_rfm.sql').read_text()).df().set_index('customer_id')
        self.assertEqual(r.loc['old_repeat','segment'],'At-risk repeat')
        self.assertEqual(r.loc['boundary_repeat','recency_days'],90)
        self.assertEqual(r.loc['boundary_repeat','segment'],'Active repeat')
        self.assertEqual(r.loc['old_once','segment'],'Dormant one-time')
        self.assertEqual(r.loc['old_repeat','m_score'],2)

    def test_product_followup_deduplicates_and_censors(self):
        self.con.execute("ALTER TABLE sales ADD COLUMN stock_code VARCHAR DEFAULT '12345'")
        self.con.execute("ALTER TABLE sales ADD COLUMN description VARCHAR DEFAULT 'Fixture product'")
        p=self.con.execute((SQL/'06_product_followup.sql').read_text()).df().iloc[0]
        self.assertEqual(p.all_buyers,3)
        self.assertEqual(p.eligible_buyers,2)
        self.assertEqual(p.censored_buyers,1)
        self.assertEqual(p.returning_buyers,1)
        self.assertEqual(p.repeat_90_pct,50)

    def test_exact_30_day_boundary_and_nonreturner_denominator(self):
        c=self.con.execute((SQL/'03_cohorts.sql').read_text()).df()
        cell=c[(c.cohort.astype(str).eq('2021-01-01')) & c.days.eq(30)].iloc[0]
        self.assertEqual(cell.customers,2)
        self.assertEqual(cell.returning_customers,1)
        self.assertEqual(cell.retention_pct,50)

    def test_whole_month_maturity_not_only_early_buyers(self):
        c=self.con.execute((SQL/'03_cohorts.sql').read_text()).df()
        self.assertFalse(((c.cohort.astype(str).eq('2021-02-01')) & c.days.eq(90)).any())
        self.assertTrue(((c.cohort.astype(str).eq('2021-01-01')) & c.days.eq(90)).any())


if __name__=='__main__':
    unittest.main()
