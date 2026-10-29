"""
Turn the computed numbers into written findings.

Writes reports/insights.md and refreshes the block between
<!-- INSIGHTS:START --> and <!-- INSIGHTS:END --> in README.md, so the numbers
in the README always match the data the pipeline was last run on.
"""
from __future__ import annotations

import re

import pandas as pd

from src.config import REPORTS_DIR, ROOT


def _p(p: float) -> str:
    return "p < 0.001" if p < 0.001 else f"p = {p:.3f}"


def _brl(x: float) -> str:
    return f"R${x / 1e6:.2f}M" if x >= 1e6 else f"R${x / 1e3:.0f}K"


def build_text(sql: dict[str, pd.DataFrame], ins: dict) -> str:
    k, g, cat, geo = ins["kpi"], ins["growth"], ins["categories"], ins["geography"]
    ret, rfm, dl, sel, t, mdl = ins["retention"], ins["rfm"], ins["delivery"], ins["sellers"], ins["test"], ins["model"]
    m = sql["monthly_revenue"]
    growth_x = m.iloc[-1]["revenue"] / m.iloc[0]["revenue"]
    top_driver = max(mdl["odds_ratios"], key=lambda r: r["odds_ratio_per_sd"])
    n_action = sel["flags"].get("Action: low reviews + late", 0)

    banner = (
        "> **Demo data.** The figures below were computed on a *synthetic* dataset that mirrors the Olist schema. "
        "Run the pipeline on the real Kaggle files to get real numbers (this section updates itself).\n\n"
        if ins["synthetic"] else
        "> Figures below were computed on the public **Olist Brazilian E-Commerce** dataset.\n\n"
    )

    lines = [banner, "### Headline metrics\n",
             "| Metric | Value |", "|---|---|",
             f"| Orders analysed | {int(k['valid_orders']):,} |",
             f"| Unique customers | {int(k['unique_customers']):,} |",
             f"| Revenue (excl. freight) | {_brl(k['revenue'])} |",
             f"| Average order value | R${k['avg_order_value']:.0f} |",
             f"| Average review score | {k['avg_review_score']:.2f} / 5 |",
             f"| Late deliveries | {k['late_delivery_pct']:.1f}% |",
             f"| Average delivery time | {k['avg_delivery_days']:.1f} days |",
             f"| Customers who ordered more than once | {k['repeat_customer_pct']:.1f}% |", "",
             "### Key findings\n",
             f"1. **Strong growth with a seasonal spike.** Monthly revenue grew about {growth_x:.0f}x over {len(m)} months; "
             f"{g['spike_month']} jumped {g['spike_mom_pct']:.0f}% over the previous month, and the highest month was {g['peak_month']} ({_brl(g['peak_revenue'])}).",
             f"2. **Revenue is concentrated.** {cat['n_class_a']} of {cat['n_categories']} categories deliver 70% of revenue "
             f"(largest: *{cat['top'].replace('_', ' ')}*, {cat['top_share_pct']:.1f}%), and state **{geo['top_state']}** alone "
             f"accounts for {geo['top_state_share_pct']:.0f}% of revenue.",
             f"3. **Late delivery is the clearest driver of unhappy customers.** On-time orders average {dl['on_time_avg_review']:.2f} stars; "
             f"orders delivered 15+ days late average {dl['very_late_avg_review']:.2f}, and {dl['very_late_pct_1_2_star']:.0f}% of them get 1-2 stars. "
             f"Late orders score {abs(t['mean_diff']):.2f} stars lower on average (95% bootstrap CI {t['ci95_low']} to {t['ci95_high']}; "
             f"Mann-Whitney {_p(t['p_value'])}).",
             f"4. **Retention is the biggest untapped opportunity.** Only {ret['repeat_customer_pct']:.1f}% of customers ever buy twice and "
             f"{ret['month1_retention_pct']:.2f}% return in the month after their first order. Repeat buyers generate "
             f"{ret['repeat_revenue_pct_last6m']:.1f}% of revenue in the last six months.",
             f"5. **High-value customers are drifting away.** The *At-Risk High-Value* RFM segment is {rfm['at_risk_customer_pct']:.0f}% of customers "
             f"but {rfm['at_risk_revenue_pct']:.0f}% of historical revenue; true *Champions* are only {rfm['champions_customer_pct']:.1f}% of customers.",
             f"6. **Geography drives service quality.** *{geo['slowest_state']}* has the highest late rate among states with 100+ orders ({geo['slowest_state_late_pct']:.0f}%), and "
             f"*{geo['highest_freight_state']}* has the heaviest freight burden ({geo['highest_freight_pct']:.0f}% of item value).",
             f"7. **Seller quality is uneven.** {n_action} of {sel['n_scored']} established sellers have both poor reviews and late deliveries.",
             f"8. **Payments.** Credit cards carry {ins['payments']['credit_card_value_pct']:.0f}% of payment value "
             f"with an average of {ins['payments']['avg_installments_card']:.1f} instalments.",
             f"9. **Driver model.** A class-balanced logistic regression flags bad reviews with ROC-AUC {mdl['auc']:.2f}; the strongest predictor is "
             f"*{top_driver['label'].lower()}* (odds ratio {top_driver['odds_ratio_per_sd']:.2f} per standard deviation). This is association, not proof of causation.",
             "", "### Recommendations\n",
             f"- **Reset delivery promises** for slow regions such as {geo['slowest_state']}: under-promise and over-deliver to protect review scores.",
             f"- **Run a seller improvement programme** starting with the {n_action} sellers flagged *Action* in the scorecard.",
             f"- **Launch a win-back campaign** (coupon or free shipping) for the At-Risk High-Value segment, and a post-purchase journey to lift second-order rate.",
             f"- **Plan capacity ahead of seasonal peaks** (the {g['spike_month']} spike, +{g['spike_mom_pct']:.0f}% in one month) to keep delivery times flat.",
             f"- **Test free-shipping thresholds** in high-freight states ({geo['highest_freight_state']}) to lift conversion.",
             "", "### Data validation\n"]
    for c in ins["cross_checks"]:
        lines.append(f"- {'PASS' if c['passed'] else 'FAIL'}: {c['check']} (SQL {c['sql']:,} vs pandas {c['pandas']:,})")
    return "\n".join(lines) + "\n"


def write(sql: dict[str, pd.DataFrame], ins: dict) -> None:
    text = build_text(sql, ins)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "insights.md").write_text(text)
    readme = ROOT / "README.md"
    if readme.exists():
        body = readme.read_text()
        new = re.sub(r"(<!-- INSIGHTS:START -->).*?(<!-- INSIGHTS:END -->)",
                     lambda mo: f"{mo.group(1)}\n{text}\n{mo.group(2)}", body, flags=re.S)
        readme.write_text(new)
