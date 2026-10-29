"""
Publication-quality static charts (PNG) for the README and LinkedIn posts.

Chart titles are written as takeaways ("action titles") and are generated from
the data, so they stay correct when the pipeline is re-run on the real dataset.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
import seaborn as sns

from src.config import FIGURES_DIR, PALETTE as C

plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#B8C0CC", "axes.labelcolor": C["ink"], "xtick.color": C["ink"], "ytick.color": C["ink"],
    "font.size": 10.5, "axes.titlesize": 13, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "axes.grid": True, "grid.color": "#E6EAF0", "grid.linewidth": 0.8, "axes.axisbelow": True,
    "figure.dpi": 110, "savefig.dpi": 170, "savefig.bbox": "tight",
})


def _save(fig: plt.Figure, name: str, footer: str | None = None, y: float = -0.02) -> str:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    if footer:
        fig.text(0.01, y, footer, fontsize=8.5, color=C["neutral"], ha="left", va="top")
    path = FIGURES_DIR / name
    fig.savefig(path)
    plt.close(fig)
    return str(path)


def _brl(x, _pos=None) -> str:
    if abs(x) >= 1e6:
        return f"R${x / 1e6:.1f}M"
    if abs(x) >= 1e3:
        return f"R${x / 1e3:.0f}K"
    return f"R${x:.0f}"


# ---------------------------------------------------------------------------
def fig_monthly_revenue(sql: dict) -> str:
    m = sql["monthly_revenue"].copy().reset_index(drop=True)
    # biggest month-over-month jump after the launch ramp-up = seasonal spike candidate
    cand = m.iloc[3:]
    spike_i = int(cand["revenue_mom_pct"].idxmax())
    spike = m.loc[spike_i]
    fig, ax = plt.subplots(figsize=(10, 4.8))
    x = np.arange(len(m))
    colors = [C["accent"] if i == spike_i else "#A9C1DB" for i in range(len(m))]
    ax.bar(x, m["revenue"], color=colors, width=0.72, label="Monthly revenue")
    ax.plot(x, m["revenue_3m_avg"], color=C["primary"], lw=2.4, marker="o", ms=4, label="3-month moving average")
    ax.set_xticks(x)
    ax.set_xticklabels(m["purchase_month"], rotation=60, ha="right")
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(_brl))
    ax.annotate(f"{spike['purchase_month']}: +{spike['revenue_mom_pct']:.0f}% vs prior month",
                xy=(spike_i, spike["revenue"]), xytext=(-150, 18), textcoords="offset points",
                fontsize=9.5, color=C["ink"], arrowprops=dict(arrowstyle="-", color=C["neutral"]))
    ax.set_ylim(0, m["revenue"].max() * 1.12)
    growth = m.iloc[-1]["revenue"] / m.iloc[0]["revenue"]
    ax.set_title(f"Monthly revenue grew {growth:.0f}x in {len(m)} months; {spike['purchase_month']} shows a sharp seasonal spike")
    ax.legend(frameon=False, loc="upper left")
    ax.grid(axis="x", visible=False)
    return _save(fig, "01_monthly_revenue.png", "Revenue = item price excluding freight; canceled/unavailable orders removed.", y=-0.1)


def fig_category_pareto(sql: dict, top_n: int = 15) -> str:
    c = sql["category_pareto"].head(top_n)
    n_a = int((sql["category_pareto"]["abc_class"] == "A").sum())
    total = len(sql["category_pareto"])
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(c))
    ax.bar(x, c["revenue"], color=[C["primary"] if a == "A" else "#A9C1DB" for a in c["abc_class"]], width=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels(c["category"].str.replace("_", " "), rotation=45, ha="right")
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(_brl))
    ax.grid(axis="x", visible=False)
    ax2 = ax.twinx()
    ax2.plot(x, c["cumulative_share_pct"], color=C["accent"], marker="o", lw=2)
    ax2.axhline(70, color=C["neutral"], ls="--", lw=1)
    ax2.text(len(c) - 0.5, 71.5, "70% of revenue", ha="right", fontsize=9, color=C["neutral"])
    ax2.set_ylim(0, 105)
    ax2.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax2.grid(False)
    ax2.spines["right"].set_visible(True)
    ax2.spines["right"].set_color("#B8C0CC")
    ax.set_title(f"{n_a} of {total} categories (dark bars, class A) generate 70% of revenue")
    return _save(fig, "02_category_pareto.png", "Class A = categories needed to reach the first 70% of cumulative revenue.", y=-0.2)


def fig_geography(sql: dict) -> str:
    s = sql["state_performance"].copy()
    top = s.head(10).iloc[::-1]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.8), gridspec_kw={"width_ratios": [1, 1.15]})
    share = 100 * s["revenue"] / s["revenue"].sum()
    ax1.barh(top["customer_state"], 100 * top["revenue"] / s["revenue"].sum(), color=C["primary"])
    ax1.xaxis.set_major_formatter(mtick.PercentFormatter())
    ax1.set_title(f"{s.iloc[0]['customer_state']} alone = {share.iloc[0]:.0f}% of revenue")
    ax1.grid(axis="y", visible=False)
    sc = ax2.scatter(s["avg_delivery_days"], s["late_pct"], s=40 + 900 * s["revenue"] / s["revenue"].max(),
                     c=s["avg_review"], cmap="RdYlGn", edgecolor="white", linewidth=0.8, alpha=0.9, vmin=3.4, vmax=4.4)
    for _, r in s.head(3).iterrows():
        ax2.annotate(r["customer_state"], (r["avg_delivery_days"], r["late_pct"]), xytext=(5, 4),
                     textcoords="offset points", fontsize=8.5)
    far = s.loc[s["late_pct"].idxmax()]
    ax2.annotate(far["customer_state"], (far["avg_delivery_days"], far["late_pct"]), xytext=(5, 4),
                 textcoords="offset points", fontsize=8.5)
    ax2.xaxis.set_major_formatter(mtick.FormatStrFormatter("%.0f d"))
    ax2.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax2.set_xlabel("Average delivery time")
    ax2.set_ylabel("Orders delivered late")
    ax2.set_title("Remote states: slower, later, lower rated")
    cb = fig.colorbar(sc, ax=ax2, pad=0.01)
    cb.set_label("Average review score")
    fig.tight_layout()
    return _save(fig, "03_geography.png", "Bubble size = revenue. Colour = average review score.")


def fig_delay_vs_review(sql: dict) -> str:
    d = sql["delay_vs_review"].copy()
    labels = d["delay_bucket"].str.replace(r"^\d\. ", "", regex=True)
    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    colors = [C["good"], "#E9C46A", C["accent"], "#D1603D", C["bad"]]
    bars = ax.bar(labels, d["avg_review"], color=colors, width=0.62)
    for b, (_, r) in zip(bars, d.iterrows()):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.06, f"{r['avg_review']:.2f}",
                ha="center", fontweight="bold")
        ax.text(b.get_x() + b.get_width() / 2, 0.15, f"{r['pct_1_2_star']:.0f}% rated\n1-2 stars\n(n={int(r['orders']):,})",
                ha="center", color="white", fontsize=8.8, fontweight="bold")
    ax.set_ylim(0, 5.2)
    ax.set_ylabel("Average review score (1-5)")
    drop = d.iloc[0]["avg_review"] - d.iloc[-1]["avg_review"]
    ax.set_title(f"Late deliveries destroy satisfaction: {drop:.1f} stars lost when an order is 15+ days late")
    ax.grid(axis="x", visible=False)
    return _save(fig, "04_delay_vs_review.png", "Delay measured against the delivery date promised at checkout.")


def fig_rfm(sql: dict) -> str:
    s = sql["rfm_segment_summary"].sort_values("revenue_pct")
    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    y = np.arange(len(s))
    h = 0.38
    ax.barh(y + h / 2, s["customer_pct"], height=h, color="#A9C1DB", label="% of customers")
    ax.barh(y - h / 2, s["revenue_pct"], height=h, color=C["primary"], label="% of revenue")
    ax.set_yticks(y)
    ax.set_yticklabels(s["segment"])
    ax.xaxis.set_major_formatter(mtick.PercentFormatter())
    for i, (_, r) in enumerate(s.iterrows()):
        ax.text(r["revenue_pct"] + 0.4, i - h / 2, f"{r['revenue_pct']:.0f}%", va="center", fontsize=9)
        ax.text(r["customer_pct"] + 0.4, i + h / 2, f"{r['customer_pct']:.0f}%", va="center", fontsize=9, color=C["neutral"])
    risk = sql["rfm_segment_summary"].set_index("segment").loc["At-Risk High-Value"]
    ax.set_title(f"At-risk high-value customers: {risk['customer_pct']:.0f}% of the base, {risk['revenue_pct']:.0f}% of revenue")
    ax.legend(frameon=False, loc="lower right")
    ax.grid(axis="y", visible=False)
    return _save(fig, "05_rfm_segments.png", "RFM: recency & monetary quintiles + rule-based frequency (97% of customers buy once).")


def fig_cohort(sql: dict, max_months: int = 12) -> str:
    c = sql["cohort_retention"]
    c = c[(c["cohort_size"] >= 300) & (c["month_index"] >= 1) & (c["month_index"] <= max_months)]
    piv = c.pivot(index="cohort_month", columns="month_index", values="retention_pct")
    piv = piv[piv.index <= piv.index[-1]]
    fig, ax = plt.subplots(figsize=(11, 6.2))
    sns.heatmap(piv, ax=ax, cmap="Blues", annot=True, fmt=".1f", annot_kws={"size": 7.5},
                cbar_kws={"label": "% of cohort that bought again"}, linewidths=0.4, linecolor="white")
    avg_m1 = c[c["month_index"] == 1]
    m1 = 100 * avg_m1["active_customers"].sum() / avg_m1["cohort_size"].sum()
    ax.set_title(f"Retention is near zero: only {m1:.1f}% of customers return in the month after their first order")
    ax.set_xlabel("Months since first purchase")
    ax.set_ylabel("Cohort (month of first purchase)")
    ax.grid(False)
    return _save(fig, "06_cohort_retention.png", "Each row is a cohort of first-time buyers; cells show the % who bought again.")


def fig_weekday_hour(sql: dict) -> str:
    w = sql["weekday_hour"]
    piv = w.pivot(index="dow", columns="hour", values="orders").fillna(0)
    names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    piv.index = [names[i] for i in piv.index]
    piv = piv.reindex(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
    fig, ax = plt.subplots(figsize=(11, 3.9))
    sns.heatmap(piv, ax=ax, cmap="YlOrBr", cbar_kws={"label": "Orders"}, linewidths=0.3, linecolor="white")
    ax.set_title("Customers shop on weekdays, late morning to evening")
    ax.set_xlabel("Hour of day")
    ax.set_ylabel("")
    ax.grid(False)
    return _save(fig, "07_weekday_hour.png")


def fig_sellers(sql: dict) -> str:
    s = sql["seller_scorecard"]
    palette = {"Healthy": C["good"], "Watch: late deliveries": "#E9C46A",
               "Watch: low reviews": C["accent"], "Action: low reviews + late": C["bad"]}
    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    for flag, color in palette.items():
        sub = s[s["health_flag"] == flag]
        ax.scatter(sub["late_pct"], sub["avg_review"], s=18 + 500 * sub["revenue"] / s["revenue"].max(),
                   color=color, alpha=0.65, edgecolor="white", linewidth=0.6, label=f"{flag} ({len(sub)})")
    ax.axhline(3.8, color=C["neutral"], ls="--", lw=1)
    ax.axvline(12, color=C["neutral"], ls="--", lw=1)
    ax.xaxis.set_major_formatter(mtick.PercentFormatter())
    ax.set_xlabel("Orders delivered late")
    ax.set_ylabel("Average review score")
    n_act = int((s["health_flag"] == "Action: low reviews + late").sum())
    ax.set_title(f"{n_act} of {len(s)} established sellers combine poor reviews with late deliveries")
    ax.legend(frameon=False, loc="lower left", fontsize=9)
    return _save(fig, "08_seller_health.png", "Sellers with 30+ delivered orders. Bubble size = revenue.")


def fig_drivers(insights: dict) -> str:
    o = pd.DataFrame(insights["model"]["odds_ratios"]).sort_values("odds_ratio_per_sd")
    fig, ax = plt.subplots(figsize=(9, 3.8))
    ax.barh(o["label"], o["odds_ratio_per_sd"] - 1, left=1,
            color=[C["bad"] if v > 1 else C["good"] for v in o["odds_ratio_per_sd"]], height=0.55)
    ax.axvline(1, color=C["ink"], lw=1)
    for i, v in enumerate(o["odds_ratio_per_sd"]):
        ax.text(v + (0.03 if v >= 1 else -0.03), i, f"{v:.2f}x", va="center", ha="left" if v >= 1 else "right", fontsize=9.5)
    ax.set_xlabel("Odds ratio for a bad review (1-2 stars), per 1 std-dev increase")
    top = o.iloc[-1]
    ax.set_title(f"Biggest driver of bad reviews: {top['label'].lower()}")
    ax.grid(axis="y", visible=False)
    return _save(fig, "09_review_drivers.png",
                 f"Logistic regression, class-balanced. Hold-out ROC-AUC = {insights['model']['auc']:.2f}. Association, not proof of causation.")


def make_all(sql: dict, insights: dict, verbose: bool = True) -> list[str]:
    paths = [
        fig_monthly_revenue(sql), fig_category_pareto(sql), fig_geography(sql), fig_delay_vs_review(sql),
        fig_rfm(sql), fig_cohort(sql), fig_weekday_hour(sql), fig_sellers(sql), fig_drivers(insights),
    ]
    if verbose:
        for p in paths:
            print("  saved", p.split("olist-ecommerce-analytics/")[-1])
    return paths
