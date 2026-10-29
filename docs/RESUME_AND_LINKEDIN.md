# Resume, LinkedIn and interview material

**Golden rule:** only write numbers produced by YOUR run on the REAL dataset (see `reports/insights.md` after Step 5 of the replication guide). The bracketed values below are placeholders you fill in from your own output. Interviewers ask about every line.

## Resume entry (Projects section)

**Olist E-Commerce Analytics | SQL, Python, pandas, scikit-learn, Plotly, SQLite** | [GitHub link] | [Dashboard link]
- Designed a SQLite database for [~100K] orders across 9 tables; wrote CTE and window-function queries (`LAG`, `NTILE`, `RANK`, `ROW_NUMBER`) to compute revenue trends, Pareto category analysis and seller scorecards.
- Showed that orders delivered 15+ days late score [X] stars lower than on-time orders (Mann-Whitney, bootstrap 95% CI), and quantified drivers of 1-2 star reviews with a logistic regression (ROC-AUC [0.xx]).
- Segmented [N] customers with an RFM model adapted to a [97%] one-time-buyer base; identified an at-risk high-value segment holding [X]% of revenue and recommended a win-back campaign.
- Built cohort retention analysis, an interactive Plotly dashboard with state filter, and a pytest suite validating SQL results against independent pandas calculations.

(Use 3-4 bullets. Each: action + method + result.)

## ATS keywords to include in your Skills section (only those you can defend)
SQL, SQLite, PostgreSQL (if you practised it), Python, pandas, NumPy, SciPy, scikit-learn, Matplotlib, Seaborn, Plotly, Power BI (if you built the .pbix), Tableau, Jupyter, Git, GitHub, Data Cleaning, Exploratory Data Analysis, RFM Segmentation, Cohort Analysis, Hypothesis Testing, Logistic Regression, Data Visualization, Dashboarding, pytest.

## LinkedIn post template

> I just finished a data project I'm proud of: analysing 100K orders from a Brazilian marketplace (Olist) end to end.
>
> What I found:
> 📦 Orders that arrive 15+ days late average [X] stars vs [Y] for on-time ones
> 🔁 Only [Z]% of customers ever buy a second time
> 💰 A single customer segment ("at-risk high-value") holds [W]% of revenue
>
> What I built: a SQLite database + SQL analysis (CTEs, window functions), RFM segmentation, cohort retention, a logistic regression for review drivers, and an interactive dashboard.
>
> One thing that surprised me: [your own surprise, e.g. why standard RFM frequency scoring fails when 97% of customers buy once].
>
> Code, dashboard and write-up: [GitHub link]
>
> I'm looking for a data analyst / data science internship. If your team is hiring, I'd love to chat.
> #DataAnalytics #SQL #Python #DataScience #Internship

Attach: the delay-vs-review chart (04) or the dashboard screenshot as the image. Post on a weekday morning IST and reply to every comment.

## Interview talking points (60-second version)
"I wanted to understand what drives satisfaction and retention at a marketplace. I loaded nine tables into SQLite, defined metrics once in SQL views, and found that delivery delay is the strongest signal of bad reviews. Customer retention was very low, so I adapted RFM scoring because standard frequency quintiles don't work when almost everyone buys once. I validated my SQL against pandas, tested the delay effect statistically, and packaged everything with tests and a dashboard."

## Questions to prepare for
1. Why `customer_unique_id` instead of `customer_id`?
2. Explain a CTE and a window function with an example from your project.
3. Why a Mann-Whitney test instead of a t-test for review scores?
4. What does an odds ratio of 1.5 mean? Does it prove causation?
5. How did you handle orders with multiple reviews? Canceled orders? Missing categories?
6. How would you extend it (CLV, NLP on reviews, delivery-time prediction)?
7. What would you do differently with more time or data (margins, marketing spend)?
