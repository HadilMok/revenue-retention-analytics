# Portfolio brief: requirements and deliverable review

The original PDF is not present in the workspace. This review uses the roadmap text copied into the conversation (the requested pages 2–3), not a visual inspection of the PDF. Page numbering and any omitted requirements cannot be verified without the source PDF.

| Requirement from supplied brief | Initial state | Completed / evidence |
|---|---|---|
| Public documented dataset, stable customers, dates and amounts | Present | Real UCI workbook, attribution, SHA256 and observed repeat purchases in `reports/validation.json` |
| Revenue decomposition | Only order-based repeat share | Preserved `revenue.png` (78.9%); added two definitions side by side in `revenue_comparison.png`, SQL 02 and kpis.csv |
| Cohort retention 30/60/90 days | Present | SQL 03, cohorts.csv, cohorts.png; complete monthly-cohort maturity; independent pandas checks |
| Products generating revenue with weak repeat behavior | First-basket buyers only; single relative comparison | Added all-SKU-buyer follow-up, explicit mature/censored counts, thresholds, `product_priorities.csv`, SQL 06 and product_followup.png. First-basket view remains available separately |
| RFM segmentation | Present | Independent validation of every R/F/M metric, score and segment; SQL 04; boundary tests |
| Interpretable churn proxy | Present but no action-list export | `at_risk_customers.csv`; repeat frequency >=2 and recency >90 days; historical heuristic, not churn probability |
| Product affinity / basket comparison | First-basket associations only | SQL 07, basket_affinity.csv: invoice-level co-occurrence, support and lift for popular merchandise SKUs |
| Three defensible actions | Present | Refreshed executive-summary.md links the two repeat metrics, mature cohorts, at-risk customers and flagged products to proposed experiments |
| README with business question and five headline findings | Present | English README with generated findings and reproducible commands |
| /sql with clean queries | Present | Seven ordered SQL files |
| /notebooks OR /analysis reproducible work | Present | analysis/run.py and analysis/test_sql.py; notebook is not mandatory |
| Data dictionary | Present | docs/data-dictionary.md, extended for new outputs |
| Dashboard screenshots / polished visual story | Separate chart PNGs | Added static overview `reports/figures/dashboard.png`; individual PNGs and README visual story. No hosted dashboard required by supplied brief |
| requirements.txt OR pyproject.toml | Present | requirements.txt plus full recorded requirements-lock.txt |
| Short executive-summary.md | Present | Five numbered calculated findings and three numbered evidence-linked recommendations; product evidence table included |
| Tests and limitations | Present | Runtime validations plus six adversarial SQL tests; integer-pence reconciliation, join checks, censoring, RFM and independent product outcomes |
| Optional two-minute demo GIF/video | Not present | Optional; interview script in docs/entretien.md supports recording. No video or published URL claimed |

The one-week sequence is an execution suggestion rather than an additional deliverable. Advanced ML, payments tables, categories, Power BI, Metabase and hosted publication are not mandatory in the supplied brief. No unsupported source fields are invented. The repository is prepared for public GitHub publication; see its Git remote for the published location.

## How to verify

Run `analysis/run.py`, then `python -m unittest discover -s analysis -p 'test_*.py'` with the project virtual environment. Inspect `reports/validation.json` for the current successful checks and the generated CSVs for denominators. Reconcile order- and customer-based revenue in kpis.csv; verify product priority thresholds and mature/censored counts; use the PNG overview for review.
