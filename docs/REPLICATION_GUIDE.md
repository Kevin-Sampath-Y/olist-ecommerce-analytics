# Replication guide: run this project on your own computer and publish it

Follow these steps in order. Total time: about 60-90 minutes the first time.

## Step 1. Install the tools (one time)

| Tool | Get it | Check it worked |
|---|---|---|
| Python 3.10+ | python.org/downloads (Windows: tick **"Add Python to PATH"**) | `python --version` |
| Git | git-scm.com | `git --version` |
| VS Code (editor) | code.visualstudio.com, then install the *Python* and *Jupyter* extensions | opens |
| GitHub account | github.com | you can log in |

Windows tip: use **PowerShell** or the VS Code terminal. Mac/Linux: use Terminal. If `python` is not found on Mac/Linux, use `python3`.

## Step 2. Get the project onto your machine

Download the zip I gave you and unzip it, e.g. to `C:\Projects\olist-ecommerce-analytics` (Windows) or `~/Projects/olist-ecommerce-analytics` (Mac). Open that folder in VS Code (File > Open Folder) and open a terminal inside it (Terminal > New Terminal).

## Step 3. Create an isolated Python environment

```bash
python -m venv .venv
# Windows PowerShell:   .venv\Scripts\Activate.ps1
# Windows cmd:          .venv\Scripts\activate.bat
# Mac / Linux:          source .venv/bin/activate
pip install -r requirements.txt
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then retry. You should see `(.venv)` at the start of the prompt.

## Step 4. Download the REAL dataset (important)

The numbers I computed while building this project came from **synthetic demo data** with the same structure as Olist, because the real files are behind a Kaggle login. For your resume and LinkedIn you must use the real data so that every number is genuinely yours.

1. Create a free account at kaggle.com.
2. Open https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce and click **Download** (a zip of ~45 MB).
3. Unzip it. You get 9 CSV files:
   `olist_customers_dataset.csv`, `olist_geolocation_dataset.csv`, `olist_order_items_dataset.csv`, `olist_order_payments_dataset.csv`, `olist_order_reviews_dataset.csv`, `olist_orders_dataset.csv`, `olist_products_dataset.csv`, `olist_sellers_dataset.csv`, `product_category_name_translation.csv`
4. Copy all 9 into the project's `data/raw/` folder.
5. **Delete** the file `data/raw/_SYNTHETIC_DATA.txt` and the demo CSVs it came with (the real files simply overwrite same-named demo files, but delete the marker file so the project knows the data is real).

## Step 5. Run the whole pipeline

```bash
python run_pipeline.py
```

It takes roughly 1-3 minutes on the real data (the geolocation table has 1 million rows). When it finishes you have:

- `reports/dashboard.html`: open it in your browser
- `reports/figures/`: 9 PNG charts
- `reports/insights.md`: findings and recommendations with YOUR real numbers
- `README.md`: the "Key findings" section has refreshed itself with the real numbers
- `data/processed/bi/`: CSVs for Power BI / Tableau

Also run the tests: `pytest -q` (expect all green).

### If something goes wrong

| Symptom | Fix |
|---|---|
| `Missing raw files in data/raw/` | A CSV is missing or misnamed. Names must match exactly (see Step 4). |
| `ModuleNotFoundError` | The virtual environment is not active, or `pip install -r requirements.txt` did not finish. |
| Charts show odd months at the edges | Expected: analysis is limited to 2017-01 to 2018-08 where data is complete. |
| A SQL query errors on real data | Copy the error and ask me; the usual cause is a small schema difference. |

## Step 6. Read and understand it (this is what interviewers test)

Spend an hour on this; it matters more than the upload.

1. Open `notebooks/01_eda_and_analysis.ipynb` in VS Code and run it top to bottom.
2. Read each SQL file in `sql/` and be able to explain, in plain words: what a CTE is, why `customer_unique_id` is used instead of `customer_id`, what `NTILE(5)` and `LAG()` do, and why the RFM frequency score is rule-based.
3. Be ready to answer: *Why Mann-Whitney instead of a t-test? What does an odds ratio of 1.5 mean? What are the limits of this analysis?* (Answers are in the notebook and README.)
4. Change something small yourself (a different late threshold, another chart, a new SQL query) and re-run. Having made at least one change of your own makes the project truly yours.

## Step 7. Personalise before publishing

- `README.md`: replace `<your-username>` and `<your-handle>` with your real GitHub and LinkedIn names.
- `LICENSE`: check the name.
- Take 2-3 screenshots of the dashboard (state filter in action) and save them in `reports/figures/` as `dashboard_overview.png`; add one to the top of the README with `![Dashboard](reports/figures/dashboard_overview.png)`.

## Step 8. Publish on GitHub

1. On github.com click **New repository**. Name: `olist-ecommerce-analytics`. Public. Do NOT add a README or .gitignore (you already have them).
2. In your project terminal:

```bash
git init
git add .
git commit -m "Olist e-commerce analytics: SQL, Python and dashboard"
git branch -M main
git remote add origin https://github.com/Kevin-Sampath-Y/olist-ecommerce-analytics.git
git push -u origin main
```

(GitHub may ask you to sign in or create a personal access token the first time.)

3. Check the repo page: README renders, images show, `data/raw/` has no big CSVs (the `.gitignore` handles that).
4. Add repo **Topics** (gear icon next to About): `data-analysis`, `sql`, `python`, `pandas`, `data-visualization`, `ecommerce`, `rfm-analysis`, `cohort-analysis`, `sqlite`. Add a one-line description.
5. Optional: host the dashboard. Settings > Pages > Branch `main`, folder `/ (root)`; your dashboard will be at `https://<your-username>.github.io/olist-ecommerce-analytics/reports/dashboard.html`. Put that link in the README and on your resume.

## Step 9. Announce it

See `docs/RESUME_AND_LINKEDIN.md` for resume bullets, a LinkedIn post template and interview talking points.

## Step 10. Pin it

On your GitHub profile, click **Customize your pins** and pin this repo first. Recruiters usually look at pinned repos only.
