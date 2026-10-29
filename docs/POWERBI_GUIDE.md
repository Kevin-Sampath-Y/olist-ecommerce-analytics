# Building the Power BI version (optional, about 90 minutes)

Many job descriptions list **Power BI** or **Tableau**. The HTML dashboard in this repo already works, but a `.pbix` file lets you say "built in Power BI" truthfully. Power BI Desktop is free (Windows only; on Mac use Tableau Public instead, steps at the end).

## 1. Load the data
Power BI Desktop > Get data > Text/CSV, load these from `data/processed/bi/`:
`fact_orders.csv`, `fact_order_items.csv`, `dim_customer_rfm.csv`, `dim_seller_scorecard.csv`, plus `agg_state_performance.csv`.

In Power Query set types: dates to *Date*, money and ratios to *Decimal number*, `review_score` to *Whole number*. Create a Date table:

```DAX
DateTable = CALENDAR(DATE(2017,1,1), DATE(2018,8,31))
```
Relate `DateTable[Date]` to `fact_orders[purchase_date]` (one-to-many), and `fact_orders[order_id]` to `fact_order_items[order_id]`.

## 2. Measures (Modeling > New measure)

```DAX
Revenue = CALCULATE(SUM(fact_orders[items_value]), NOT fact_orders[order_status] IN {"canceled","unavailable"})
Orders = CALCULATE(DISTINCTCOUNT(fact_orders[order_id]), NOT fact_orders[order_status] IN {"canceled","unavailable"})
AOV = DIVIDE([Revenue], [Orders])
Customers = DISTINCTCOUNT(fact_orders[customer_unique_id])
Avg Review = AVERAGE(fact_orders[review_score])
Late % = DIVIDE(CALCULATE(SUM(fact_orders[is_late]), fact_orders[order_status]="delivered"), CALCULATE(COUNTROWS(fact_orders), fact_orders[order_status]="delivered"))
Revenue MoM % = VAR prev = CALCULATE([Revenue], DATEADD(DateTable[Date], -1, MONTH)) RETURN DIVIDE([Revenue]-prev, prev)
Revenue 3M Avg = AVERAGEX(DATESINPERIOD(DateTable[Date], MAX(DateTable[Date]), -3, MONTH), [Revenue])
```

## 3. Report pages
1. **Executive overview**: 5 KPI cards (Revenue, Orders, AOV, Avg Review, Late %), line chart Revenue + Revenue 3M Avg by month, map or bar by state, slicers for State and Year.
2. **Customers**: bar of customers vs revenue by RFM `segment`, cohort matrix (Matrix visual from `agg_cohort_retention.csv`, rows `cohort_month`, columns `month_index`, values `retention_pct`, conditional formatting on).
3. **Delivery and sellers**: column chart Avg Review by delay bucket, scatter `late_pct` vs `avg_review` from the seller scorecard coloured by `health_flag`, table of flagged sellers.

Design rules: 3 colours maximum, titles that state the takeaway, no 3D, consistent number formats, a tooltip page if you have time.

## 4. Publish
Save `olist_dashboard.pbix` into a `powerbi/` folder in the repo, export 3 page screenshots (File > Export > PDF, or Snipping Tool) into `reports/figures/`, and reference them in the README. Don't upload the `.pbix` if it exceeds 100 MB.

## Tableau Public (Mac or Windows)
Same data folder, connect with Text file, build the same three pages, then File > Save to Tableau Public and put the link in the README.
