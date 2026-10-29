"""
Statistical analysis and modelling on top of the SQL layer.

What this module adds beyond SQL
  1. Cross-checks: re-computes headline numbers in pandas and compares them to
     the SQL results (guards against silent SQL logic errors).
  2. Hypothesis test: do late deliveries get lower review scores? (Mann-Whitney U,
     bootstrap confidence interval, effect size)
  3. Driver model: logistic regression predicting a bad review (1-2 stars)
     from logistics and order features; reports odds ratios per 1 std-dev.
  4. Collects every headline number into one `insights` dict used by the
     charts, dashboard and auto-generated report.
"""
from __future__ import annotations

import json
import sqlite3

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from src.config import DB_PATH, PROCESSED_DIR, RAW_DIR, REPORTS_DIR

RNG_SEED = 42


# --------------------------------------------------------------------------- loading
def load_orders(con: sqlite3.Connection) -> pd.DataFrame:
    df = pd.read_sql_query("SELECT * FROM v_orders_enriched", con,
                           parse_dates=["purchased_at", "delivered_at", "estimated_at"])
    return df


def is_synthetic() -> bool:
    return (RAW_DIR / "_SYNTHETIC_DATA.txt").exists()


# --------------------------------------------------------------------------- 1. cross-checks
def cross_check(orders: pd.DataFrame, sql: dict[str, pd.DataFrame]) -> list[dict]:
    """Recompute key metrics with pandas and compare with the SQL output."""
    valid = orders[~orders["order_status"].isin(["canceled", "unavailable"]) & orders["items_value"].notna()]
    delivered = orders[orders["order_status"] == "delivered"]
    kpi = sql["kpi_summary"].iloc[0]

    checks = [
        ("Revenue (SQL vs pandas)", float(kpi["revenue"]), round(float(valid["items_value"].sum()), 2)),
        ("Valid orders", int(kpi["valid_orders"]), int(len(valid))),
        ("Unique customers", int(kpi["unique_customers"]), int(valid["customer_unique_id"].nunique())),
        ("Late delivery %", float(kpi["late_delivery_pct"]),
         round(100 * (delivered["delivered_at"] > delivered["estimated_at"]).mean(), 2)),
        ("RFM customers (view vs unique customers)", int(len(sql["customer_rfm"])),
         int(valid["customer_unique_id"].nunique())),
    ]
    out = []
    for name, sql_val, pd_val in checks:
        ok = bool(np.isclose(sql_val, pd_val, rtol=1e-6, atol=0.011))
        out.append({"check": name, "sql": sql_val, "pandas": pd_val, "passed": ok})
    return out


# --------------------------------------------------------------------------- 2. hypothesis test
def late_vs_ontime_test(orders: pd.DataFrame, n_boot: int = 2000) -> dict:
    d = orders[(orders["order_status"] == "delivered") & orders["review_score"].notna()]
    late = d.loc[d["is_late"] == 1, "review_score"].to_numpy(dtype=float)
    ontime = d.loc[d["is_late"] == 0, "review_score"].to_numpy(dtype=float)

    u, p = stats.mannwhitneyu(late, ontime, alternative="two-sided")
    # rank-biserial correlation: -1 .. 1 (negative => late orders rate lower)
    rank_biserial = 2 * u / (len(late) * len(ontime)) - 1

    rng = np.random.default_rng(RNG_SEED)
    diffs = np.empty(n_boot)
    for b in range(n_boot):
        diffs[b] = (rng.choice(late, len(late)).mean() - rng.choice(ontime, len(ontime)).mean())
    lo, hi = np.percentile(diffs, [2.5, 97.5])

    return {
        "n_late": int(len(late)), "n_ontime": int(len(ontime)),
        "mean_late": round(float(late.mean()), 2), "mean_ontime": round(float(ontime.mean()), 2),
        "mean_diff": round(float(late.mean() - ontime.mean()), 2),
        "ci95_low": round(float(lo), 2), "ci95_high": round(float(hi), 2),
        "p_value": float(p), "rank_biserial": round(float(rank_biserial), 3),
    }


# --------------------------------------------------------------------------- 3. driver model
FEATURES = {
    "delay_days": "Days late vs promised date",
    "delivery_days": "Total delivery time (days)",
    "freight_ratio": "Freight as % of item value",
    "log_value": "Order value (log)",
    "n_items": "Items in order",
}


def review_driver_model(orders: pd.DataFrame) -> dict:
    d = orders[(orders["order_status"] == "delivered") & orders["review_score"].notna()
               & orders["items_value"].notna() & (orders["items_value"] > 0)].copy()
    d["bad_review"] = (d["review_score"] <= 2).astype(int)
    d["delay_days"] = d["delay_days"].clip(-30, 60)
    d["freight_ratio"] = (d["freight_value"] / d["items_value"]).clip(0, 3)
    d["log_value"] = np.log1p(d["items_value"])

    # Real data has a few "delivered" orders with no delivery date (and other gaps),
    # which leaves NaN/inf in the features. Drop those rows: models can't use them.
    d = d.replace([np.inf, -np.inf], np.nan).dropna(subset=list(FEATURES))
    X = d[list(FEATURES)].astype(float)
    y = d["bad_review"]
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, random_state=RNG_SEED, stratify=y)
    scaler = StandardScaler().fit(X_tr)
    model = LogisticRegression(max_iter=1000, class_weight="balanced")
    model.fit(scaler.transform(X_tr), y_tr)
    auc = roc_auc_score(y_te, model.predict_proba(scaler.transform(X_te))[:, 1])

    odds = pd.DataFrame({
        "feature": list(FEATURES), "label": list(FEATURES.values()),
        "odds_ratio_per_sd": np.exp(model.coef_[0]),
    }).sort_values("odds_ratio_per_sd", ascending=False)

    return {
        "auc": round(float(auc), 3),
        "bad_review_rate_pct": round(100 * float(y.mean()), 1),
        "n": int(len(d)),
        "odds_ratios": odds.round(3).to_dict(orient="records"),
    }


# --------------------------------------------------------------------------- 4. insights
def build_insights(sql: dict[str, pd.DataFrame], test: dict, model: dict, checks: list[dict]) -> dict:
    k = sql["kpi_summary"].iloc[0].to_dict()
    m = sql["monthly_revenue"]
    cat = sql["category_pareto"]
    state = sql["state_performance"]
    seg = sql["rfm_segment_summary"].set_index("segment")
    coh = sql["cohort_retention"]
    delay = sql["delay_vs_review"]
    sellers = sql["seller_scorecard"]
    pay = sql["payment_mix"]
    gap = sql["repeat_gap"]
    nvr = sql["new_vs_returning"]

    # growth: compare the last 3 full months vs the same 3 months a year earlier
    last3 = m.tail(3)["revenue"].sum()
    prev3 = m.iloc[-15:-12]["revenue"].sum() if len(m) >= 15 else np.nan
    yoy = round(100 * (last3 / prev3 - 1), 1) if prev3 and not np.isnan(prev3) else None
    peak = m.loc[m["revenue"].idxmax()]

    n_a = int((cat["abc_class"] == "A").sum())
    top_cat = cat.iloc[0]
    top_state = state.iloc[0]
    sp_share = round(100 * float(top_state["revenue"]) / float(state["revenue"].sum()), 1)
    big = state[state["orders"] >= 100]          # ignore tiny states: rates there are too noisy
    far = big.loc[big["late_pct"].idxmax()]
    freight_hi = big.loc[big["freight_pct_of_revenue"].idxmax()]
    spike = m.iloc[3:].loc[m.iloc[3:]["revenue_mom_pct"].idxmax()]

    m1 = coh[coh["month_index"] == 1]
    ret_m1 = round(float((m1["active_customers"].sum() / m1["cohort_size"].sum()) * 100), 2)

    risk = seg.loc["At-Risk High-Value"] if "At-Risk High-Value" in seg.index else None
    flagged = sellers["health_flag"].value_counts().to_dict()

    on_time = delay.iloc[0]
    very_late = delay.iloc[-1]

    insights = {
        "synthetic": is_synthetic(),
        "kpi": {kk: (float(v) if isinstance(v, (int, float, np.floating, np.integer)) else v) for kk, v in k.items()},
        "growth": {
            "yoy_last3_pct": yoy,
            "peak_month": str(peak["purchase_month"]), "peak_revenue": float(peak["revenue"]),
            "spike_month": str(spike["purchase_month"]), "spike_mom_pct": float(spike["revenue_mom_pct"]),
        },
        "categories": {
            "n_categories": int(len(cat)), "n_class_a": n_a,
            "top": str(top_cat["category"]), "top_share_pct": float(top_cat["revenue_share_pct"]),
        },
        "geography": {
            "top_state": str(top_state["customer_state"]), "top_state_share_pct": sp_share,
            "slowest_state": str(far["customer_state"]), "slowest_state_late_pct": float(far["late_pct"]),
            "highest_freight_state": str(freight_hi["customer_state"]),
            "highest_freight_pct": float(freight_hi["freight_pct_of_revenue"]),
        },
        "payments": {
            "credit_card_value_pct": float(pay.loc[pay["payment_type"] == "credit_card", "value_share_pct"].sum()),
            "avg_installments_card": float(pay.loc[pay["payment_type"] == "credit_card", "avg_installments"].sum()),
        },
        "retention": {
            "month1_retention_pct": ret_m1,
            "repeat_customer_pct": float(k["repeat_customer_pct"]),
            "repeat_revenue_pct_last6m": round(float(nvr.tail(6)["repeat_revenue"].sum() / nvr.tail(6)["revenue"].sum() * 100), 1),
            "median_gap_bucket": str(gap.loc[gap["customers"].idxmax(), "gap_bucket"]),
        },
        "rfm": {
            "at_risk_customer_pct": float(risk["customer_pct"]) if risk is not None else None,
            "at_risk_revenue_pct": float(risk["revenue_pct"]) if risk is not None else None,
            "champions_customer_pct": float(seg.loc["Champions", "customer_pct"]) if "Champions" in seg.index else None,
            "champions_revenue_pct": float(seg.loc["Champions", "revenue_pct"]) if "Champions" in seg.index else None,
        },
        "delivery": {
            "on_time_avg_review": float(on_time["avg_review"]), "very_late_avg_review": float(very_late["avg_review"]),
            "very_late_pct_1_2_star": float(very_late["pct_1_2_star"]),
            "very_late_bucket": str(very_late["delay_bucket"]),
        },
        "sellers": {"n_scored": int(len(sellers)), "flags": {str(a): int(b) for a, b in flagged.items()}},
        "test": test,
        "model": model,
        "cross_checks": checks,
    }
    return insights


def run(sql: dict[str, pd.DataFrame] | None = None, verbose: bool = True) -> dict:
    if sql is None:
        sql = {p.stem.removeprefix("sql_"): pd.read_csv(p) for p in PROCESSED_DIR.glob("sql_*.csv")}
    con = sqlite3.connect(DB_PATH)
    try:
        orders = load_orders(con)
    finally:
        con.close()

    checks = cross_check(orders, sql)
    test = late_vs_ontime_test(orders)
    model = review_driver_model(orders)
    insights = build_insights(sql, test, model, checks)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "insights.json").write_text(json.dumps(insights, indent=2, default=float))
    if verbose:
        for c in checks:
            print(f"  [{'PASS' if c['passed'] else 'FAIL'}] {c['check']}: sql={c['sql']} pandas={c['pandas']}")
        print(f"  late vs on-time review diff {test['mean_diff']} (95% CI {test['ci95_low']}..{test['ci95_high']}), p={test['p_value']:.2e}")
        print(f"  driver model AUC {model['auc']}")
    return insights


if __name__ == "__main__":
    run()
