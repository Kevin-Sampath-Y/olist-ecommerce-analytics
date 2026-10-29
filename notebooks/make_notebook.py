"""Builds notebooks/01_eda_and_analysis.ipynb (run once; then executed with nbconvert)."""
import nbformat as nbf

nb = nbf.v4.new_notebook()
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
cells = [
md("""# Olist E-Commerce: Exploratory Analysis and Business Insights

**Goal:** understand what drives revenue, customer satisfaction and retention for a Brazilian online marketplace, and turn the answers into recommendations.

**Approach:** raw CSVs -> SQLite database -> SQL views/queries (single source of truth for metric definitions) -> pandas / scikit-learn for statistics and modelling.

> Run `python run_pipeline.py` first so the database exists. All numbers in this notebook are computed live from it."""),
code("""import sqlite3, warnings
import pandas as pd, numpy as np
import matplotlib.pyplot as plt, seaborn as sns
from pathlib import Path
warnings.filterwarnings("ignore")
pd.set_option("display.float_format", "{:,.2f}".format, "display.width", 140)
sns.set_theme(style="whitegrid", context="notebook")

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
con = sqlite3.connect(ROOT / "data" / "olist.db")
q = lambda sql: pd.read_sql_query(sql, con)
SYNTHETIC = (ROOT / "data" / "raw" / "_SYNTHETIC_DATA.txt").exists()
print("Using SYNTHETIC demo data" if SYNTHETIC else "Using real Olist data")"""),
md("## 1. Data overview and quality\nRow counts per table and null rates for the columns that matter."),
code("""tables = ["customers","orders","order_items","order_payments","order_reviews","products","sellers","geolocation","category_translation"]
pd.DataFrame({"rows":[q(f"SELECT COUNT(*) n FROM {t}")["n"][0] for t in tables]}, index=tables)"""),
code("""checks = {
 "orders missing approval timestamp": "SELECT COUNT(*) FROM orders WHERE order_approved_at IS NULL",
 "delivered orders without delivery date": "SELECT COUNT(*) FROM orders WHERE order_status='delivered' AND order_delivered_customer_date IS NULL",
 "delivered BEFORE purchase (impossible)": "SELECT COUNT(*) FROM orders WHERE order_delivered_customer_date < order_purchase_timestamp",
 "products without category": "SELECT COUNT(*) FROM products WHERE product_category_name IS NULL",
 "items with price <= 0": "SELECT COUNT(*) FROM order_items WHERE price <= 0",
 "orders with more than one review": "SELECT COUNT(*) FROM (SELECT order_id FROM order_reviews GROUP BY order_id HAVING COUNT(*)>1)",
 "orders with no line items": "SELECT COUNT(*) FROM orders WHERE order_id NOT IN (SELECT order_id FROM order_items)",
}
pd.Series({k: con.execute(v).fetchone()[0] for k, v in checks.items()}, name="count").to_frame()"""),
md("""**Cleaning decisions**
- Canceled / unavailable orders are excluded from revenue metrics.
- Orders with several reviews keep only the latest (view `v_order_review`).
- Products without a category are labelled `unknown` rather than dropped, to keep revenue totals complete.
- `customer_id` is generated per order; every customer metric uses `customer_unique_id`."""),
md("## 2. Headline KPIs"),
code("""pd.read_csv(ROOT/"data/processed/sql_kpi_summary.csv").T.rename(columns={0:"value"})"""),
md("## 3. Revenue trend"),
code("""m = pd.read_csv(ROOT/"data/processed/sql_monthly_revenue.csv")
fig, ax = plt.subplots(figsize=(10,4))
ax.bar(m.purchase_month, m.revenue, color="#A9C1DB"); ax.plot(m.purchase_month, m.revenue_3m_avg, color="#1F4E79", lw=2.5, marker="o")
ax.set_title("Monthly revenue (bars) and 3-month moving average"); plt.xticks(rotation=60, ha="right"); plt.show()
m.sort_values("revenue_mom_pct", ascending=False).head(3)[["purchase_month","revenue","revenue_mom_pct"]]"""),
md("## 4. Product categories (Pareto)"),
code("""c = pd.read_csv(ROOT/"data/processed/sql_category_pareto.csv")
print(f"{(c.abc_class=='A').sum()} of {len(c)} categories make up the first 70% of revenue")
c.head(10)[["category","revenue","revenue_share_pct","cumulative_share_pct","abc_class"]]"""),
md("## 5. Delivery performance and customer satisfaction\nThe key business question: **does late delivery hurt reviews, and by how much?**"),
code("""d = pd.read_csv(ROOT/"data/processed/sql_delay_vs_review.csv"); d"""),
code("""from scipy import stats
o = q("SELECT is_late, review_score FROM v_orders_enriched WHERE order_status='delivered' AND review_score IS NOT NULL")
late, ontime = o[o.is_late==1].review_score, o[o.is_late==0].review_score
u, p = stats.mannwhitneyu(late, ontime)
print(f"Mean review  on-time: {ontime.mean():.2f}   late: {late.mean():.2f}   difference: {late.mean()-ontime.mean():.2f}")
print(f"Mann-Whitney U p-value: {p:.2e}  (reviews are ordinal 1-5, so a rank test is more appropriate than a t-test)")"""),
md("""## 6. Customer behaviour
Olist's well-known quirk: almost all customers buy **once**. That makes "frequency" a weak RFM dimension, so the scoring rule treats frequency explicitly (see `sql/04_customer_analytics.sql`)."""),
code("""seg = pd.read_csv(ROOT/"data/processed/sql_rfm_segment_summary.csv"); seg"""),
code("""coh = pd.read_csv(ROOT/"data/processed/sql_cohort_retention.csv")
coh = coh[(coh.cohort_size>=300)&(coh.month_index.between(1,12))]
piv = coh.pivot(index="cohort_month", columns="month_index", values="retention_pct")
plt.figure(figsize=(10,5)); sns.heatmap(piv, cmap="Blues", annot=True, fmt=".1f", annot_kws={"size":7}); plt.title("Cohort retention (% buying again)"); plt.show()"""),
md("## 7. What predicts a bad review? (logistic regression)"),
code("""import json
ins = json.load(open(ROOT/"reports/insights.json"))
print("Hold-out ROC-AUC:", ins["model"]["auc"])
pd.DataFrame(ins["model"]["odds_ratios"])[["label","odds_ratio_per_sd"]]"""),
md("""**Reading the odds ratios:** a value of 1.5 means a one-standard-deviation increase in that feature multiplies the odds of a 1-2 star review by 1.5, holding the others fixed. This shows association, not causation.

## 8. Takeaways
See `reports/insights.md` for the written findings and recommendations (generated from these same numbers), and `reports/dashboard.html` for the interactive dashboard."""),
]
nb["cells"] = cells
nb["metadata"]["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
nbf.write(nb, "notebooks/01_eda_and_analysis.ipynb")
