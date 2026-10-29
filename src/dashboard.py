"""
Build a single-file interactive HTML dashboard (Plotly) with a state filter.

Open reports/dashboard.html in any browser (it loads Plotly from a CDN, so an
internet connection is needed the first time). Host it free with GitHub Pages.
"""
from __future__ import annotations

import json

import pandas as pd
import plotly.graph_objects as go

from src.config import PALETTE as C, REPORTS_DIR

LAYOUT = dict(
    font=dict(family="Inter, Segoe UI, Arial, sans-serif", size=12, color=C["ink"]),
    paper_bgcolor="white", plot_bgcolor="white", margin=dict(l=50, r=20, t=50, b=50),
    title=dict(x=0, font=dict(size=15)), hoverlabel=dict(font_size=12),
)


def _fig(fig: go.Figure, title: str, height: int = 380) -> dict:
    fig.update_layout(title_text=title, height=height, **{k: v for k, v in LAYOUT.items() if k != "title"},
                      title_x=0)
    fig.update_xaxes(showgrid=False, linecolor="#B8C0CC")
    fig.update_yaxes(gridcolor="#E6EAF0", zeroline=False)
    return json.loads(fig.to_json())


def build(sql: dict[str, pd.DataFrame], insights: dict) -> str:
    cat = sql["category_pareto"].head(12)
    state = sql["state_performance"]
    delay = sql["delay_vs_review"]
    seg = sql["rfm_segment_summary"]
    coh = sql["cohort_retention"]
    coh = coh[(coh["cohort_size"] >= 300) & (coh["month_index"].between(1, 12))]
    sellers = sql["seller_scorecard"]
    pay = sql["payment_mix"]
    wh = sql["weekday_hour"]
    nvr = sql["new_vs_returning"]

    figs: dict[str, dict] = {}

    f = go.Figure(go.Bar(x=cat["category"].str.replace("_", " "), y=cat["revenue"], marker_color=C["primary"],
                         name="Revenue", hovertemplate="%{x}<br>R$%{y:,.0f}<extra></extra>"))
    f.add_scatter(x=cat["category"].str.replace("_", " "), y=cat["cumulative_share_pct"], yaxis="y2", mode="lines+markers",
                  line=dict(color=C["accent"], width=3), name="Cumulative %", hovertemplate="%{y:.1f}%<extra></extra>")
    f.update_layout(yaxis2=dict(overlaying="y", side="right", range=[0, 105], tickvals=[0, 25, 50, 75, 100], ticksuffix="%", showgrid=False),
                    legend=dict(orientation="h", y=1.12), xaxis_tickangle=-40)
    figs["category"] = _fig(f, "Top categories: revenue and cumulative share (Pareto)")

    f = go.Figure(go.Bar(x=state["customer_state"], y=state["revenue"], marker_color=C["primary"],
                         hovertemplate="%{x}: R$%{y:,.0f}<extra></extra>"))
    figs["state_rev"] = _fig(f, "Revenue by customer state")

    f = go.Figure(go.Scatter(
        x=state["avg_delivery_days"], y=state["late_pct"], mode="markers+text", text=state["customer_state"],
        textposition="top center", marker=dict(size=10 + 60 * state["revenue"] / state["revenue"].max(),
                                               color=state["avg_review"], colorscale="RdYlGn", cmin=3.4, cmax=4.4,
                                               showscale=True, colorbar=dict(title="Avg review"), line=dict(color="white", width=1)),
        hovertemplate="%{text}<br>%{x:.1f} days, %{y:.1f}% late<extra></extra>"))
    f.update_layout(xaxis_title="Average delivery days", yaxis_title="Late deliveries (%)")
    figs["state_service"] = _fig(f, "Delivery speed vs punctuality by state (bubble = revenue)")

    colors = [C["good"], "#E9C46A", C["accent"], "#D1603D", C["bad"]]
    f = go.Figure(go.Bar(x=delay["delay_bucket"].str.replace(r"^\d\. ", "", regex=True), y=delay["avg_review"],
                         marker_color=colors, text=delay["avg_review"].round(2), textposition="outside",
                         customdata=delay[["pct_1_2_star", "orders"]],
                         hovertemplate="%{x}<br>avg %{y:.2f}<br>%{customdata[0]}% rated 1-2 stars<br>%{customdata[1]:,} orders<extra></extra>"))
    f.update_yaxes(range=[0, 5.3])
    figs["delay"] = _fig(f, "Average review score by delivery delay")

    f = go.Figure()
    f.add_bar(y=seg["segment"], x=seg["customer_pct"], orientation="h", name="% of customers", marker_color="#A9C1DB")
    f.add_bar(y=seg["segment"], x=seg["revenue_pct"], orientation="h", name="% of revenue", marker_color=C["primary"])
    f.update_layout(barmode="group", yaxis=dict(autorange="reversed"), legend=dict(orientation="h", y=1.12), xaxis_ticksuffix="%")
    figs["rfm"] = _fig(f, "RFM segments: share of customers vs share of revenue")

    piv = coh.pivot(index="cohort_month", columns="month_index", values="retention_pct")
    f = go.Figure(go.Heatmap(z=piv.values, x=[f"+{c}" for c in piv.columns], y=piv.index, colorscale="Blues",
                             colorbar=dict(title="% returned"), hovertemplate="Cohort %{y}, month %{x}: %{z:.2f}%<extra></extra>"))
    f.update_yaxes(autorange="reversed")
    figs["cohort"] = _fig(f, "Cohort retention (% of first-time buyers who purchase again)", 460)

    names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    p2 = wh.pivot(index="dow", columns="hour", values="orders").fillna(0).reindex([1, 2, 3, 4, 5, 6, 0])
    f = go.Figure(go.Heatmap(z=p2.values, x=p2.columns, y=[names[i] for i in p2.index], colorscale="YlOrBr",
                             hovertemplate="%{y} %{x}:00 = %{z} orders<extra></extra>"))
    f.update_yaxes(autorange="reversed")
    figs["heat"] = _fig(f, "When customers order (day x hour)", 320)

    flag_colors = {"Healthy": C["good"], "Watch: late deliveries": "#E9C46A", "Watch: low reviews": C["accent"],
                   "Action: low reviews + late": C["bad"]}
    f = go.Figure()
    for flag, col in flag_colors.items():
        sub = sellers[sellers["health_flag"] == flag]
        f.add_scatter(x=sub["late_pct"], y=sub["avg_review"], mode="markers", name=f"{flag} ({len(sub)})",
                      marker=dict(color=col, size=6 + 30 * sub["revenue"] / sellers["revenue"].max(), opacity=0.7,
                                  line=dict(color="white", width=0.5)),
                      customdata=sub[["orders", "revenue", "seller_state"]],
                      hovertemplate="%{customdata[2]} seller<br>%{customdata[0]} orders, R$%{customdata[1]:,.0f}<br>"
                                    "late %{x}%, review %{y}<extra></extra>")
    f.update_layout(xaxis_title="Late deliveries (%)", yaxis_title="Average review", legend=dict(orientation="h", y=-0.2))
    figs["sellers"] = _fig(f, "Seller health (sellers with 30+ delivered orders)", 420)

    f = go.Figure(go.Pie(labels=pay["payment_type"].str.replace("_", " "), values=pay["payment_value"], hole=0.55,
                         marker=dict(colors=[C["primary"], C["accent"], "#A9C1DB", C["neutral"]])))
    figs["payment"] = _fig(f, "Payment method share (by value)", 340)

    f = go.Figure()
    f.add_bar(x=nvr["purchase_month"], y=nvr["new_customer_orders"], name="First-time buyers", marker_color=C["primary"])
    f.add_bar(x=nvr["purchase_month"], y=nvr["repeat_orders"], name="Repeat buyers", marker_color=C["accent"])
    f.update_layout(barmode="stack", legend=dict(orientation="h", y=1.12))
    figs["nvr"] = _fig(f, "Orders per month: first-time vs repeat buyers", 340)

    payload = {
        "figs": figs,
        "state_monthly": sql["state_monthly"].to_dict(orient="records"),
        "states": ["All states"] + sorted(sql["state_monthly"]["state"].unique().tolist()),
        "colors": C,
    }
    kpi = insights["kpi"]
    banner = ("DEMO DATA: synthetic dataset with the Olist schema. Re-run the pipeline on the real Kaggle files for real results."
              if insights.get("synthetic") else "Data: Olist Brazilian E-Commerce public dataset (Kaggle), 2016-2018.")
    html = TEMPLATE.replace("__PAYLOAD__", json.dumps(payload)).replace("__BANNER__", banner) \
                   .replace("__BANNER_CLASS__", "demo" if insights.get("synthetic") else "real") \
                   .replace("__TOTAL_ORDERS__", f"{int(kpi['total_orders']):,}")
    out = REPORTS_DIR / "dashboard.html"
    out.write_text(html, encoding="utf-8")
    return str(out)


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Olist E-Commerce Analytics Dashboard</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js" charset="utf-8"></script>
<style>
:root{--primary:#1F4E79;--accent:#F28E2B;--ink:#1B2430;--muted:#6B7686;--bg:#F4F6FA;--card:#fff;--line:#E3E8F0}
*{box-sizing:border-box}body{margin:0;font-family:Inter,"Segoe UI",Arial,sans-serif;background:var(--bg);color:var(--ink)}
header{background:var(--primary);color:#fff;padding:18px 28px;display:flex;flex-wrap:wrap;gap:14px;align-items:center;justify-content:space-between}
header h1{margin:0;font-size:20px}header p{margin:2px 0 0;font-size:13px;opacity:.85}
select{padding:8px 12px;border-radius:8px;border:0;font-size:14px}
.banner{padding:8px 28px;font-size:13px}.banner.demo{background:#FFF3CD;color:#7A5B00}.banner.real{background:#E3F4EA;color:#1F6B3B}
main{max-width:1280px;margin:0 auto;padding:20px 20px 40px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-bottom:18px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.kpi .l{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}.kpi .v{font-size:26px;font-weight:700;margin-top:4px}
nav{display:flex;gap:6px;margin-bottom:14px;flex-wrap:wrap}
nav button{background:#fff;border:1px solid var(--line);padding:9px 16px;border-radius:999px;cursor:pointer;font-size:14px;color:var(--ink)}
nav button.on{background:var(--primary);color:#fff;border-color:var(--primary)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(480px,1fr));gap:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:6px 8px;min-width:0}
.card.wide{grid-column:1/-1}.tab{display:none}.tab.on{display:block}
footer{color:var(--muted);font-size:12px;text-align:center;padding:14px}
@media(max-width:560px){.grid{grid-template-columns:1fr}}
</style></head><body>
<header><div><h1>Olist E-Commerce Analytics</h1><p>Sales, customers and delivery performance &middot; __TOTAL_ORDERS__ orders</p></div>
<label>State: <select id="state"></select></label></header>
<div class="banner __BANNER_CLASS__">__BANNER__</div>
<main>
<div class="kpis" id="kpis"></div>
<nav id="nav"><button data-t="t1" class="on">Sales</button><button data-t="t2">Customers</button><button data-t="t3">Delivery &amp; sellers</button></nav>
<section class="tab on" id="t1"><div class="grid">
<div class="card wide"><div id="monthly"></div></div>
<div class="card"><div id="category"></div></div><div class="card"><div id="state_rev"></div></div>
<div class="card"><div id="payment"></div></div><div class="card"><div id="heat"></div></div></div></section>
<section class="tab" id="t2"><div class="grid">
<div class="card"><div id="rfm"></div></div><div class="card"><div id="nvr"></div></div>
<div class="card wide"><div id="cohort"></div></div></div></section>
<section class="tab" id="t3"><div class="grid">
<div class="card"><div id="delay"></div></div><div class="card"><div id="state_service"></div></div>
<div class="card wide"><div id="sellers"></div></div></div></section>
</main>
<footer>Built with SQL (SQLite), Python (pandas, scikit-learn) and Plotly. Revenue = item price excl. freight.</footer>
<script>
const P=__PAYLOAD__;const cfg={responsive:true,displaylogo:false};
const fmt=n=>n>=1e6?"R$"+(n/1e6).toFixed(2)+"M":n>=1e3?"R$"+(n/1e3).toFixed(0)+"K":"R$"+n.toFixed(0);
const sel=document.getElementById("state");P.states.forEach(s=>sel.add(new Option(s,s)));
function rows(){const s=sel.value;return s==="All states"?P.state_monthly:P.state_monthly.filter(r=>r.state===s)}
function render(){
  const r=rows();const sum=k=>r.reduce((a,x)=>a+(x[k]||0),0);
  const orders=sum("orders"),rev=sum("revenue"),dl=sum("delivered"),late=sum("late"),rs=sum("review_sum"),rn=sum("review_n"),dd=sum("delivery_days_sum");
  const cards=[["Revenue",fmt(rev)],["Orders",orders.toLocaleString()],["Avg order value",orders?"R$"+(rev/orders).toFixed(0):"-"],
   ["Avg review",rn?(rs/rn).toFixed(2)+" / 5":"-"],["Late deliveries",dl?(100*late/dl).toFixed(1)+"%":"-"],["Avg delivery",dl?(dd/dl).toFixed(1)+" days":"-"]];
  document.getElementById("kpis").innerHTML=cards.map(c=>`<div class="kpi"><div class="l">${c[0]}</div><div class="v">${c[1]}</div></div>`).join("");
  const byM={};r.forEach(x=>{byM[x.purchase_month]=(byM[x.purchase_month]||0)+x.revenue});
  const months=Object.keys(byM).sort(),vals=months.map(m=>byM[m]);
  const ma=vals.map((_,i)=>{const w=vals.slice(Math.max(0,i-2),i+1);return w.reduce((a,b)=>a+b,0)/w.length});
  Plotly.react("monthly",[{x:months,y:vals,type:"bar",name:"Revenue",marker:{color:"#A9C1DB"},hovertemplate:"%{x}<br>R$%{y:,.0f}<extra></extra>"},
   {x:months,y:ma,type:"scatter",mode:"lines+markers",name:"3-month avg",line:{color:P.colors.primary,width:3}}],
   {title:{text:"Monthly revenue"+(sel.value==="All states"?"":" - "+sel.value),x:0,font:{size:15}},height:360,margin:{l:60,r:20,t:50,b:50},
    paper_bgcolor:"white",plot_bgcolor:"white",legend:{orientation:"h",y:1.12},yaxis:{gridcolor:"#E6EAF0"},font:{family:"Inter,Segoe UI,Arial",color:P.colors.ink}},cfg);
}
sel.onchange=render;
for(const k in P.figs){const el=document.getElementById(k);if(el){const f=P.figs[k];Plotly.newPlot(el,f.data,f.layout,cfg)}}
render();
document.querySelectorAll("#nav button").forEach(b=>b.onclick=()=>{
  document.querySelectorAll("#nav button").forEach(x=>x.classList.remove("on"));b.classList.add("on");
  document.querySelectorAll(".tab").forEach(t=>t.classList.remove("on"));document.getElementById(b.dataset.t).classList.add("on");
  window.dispatchEvent(new Event("resize"));});
</script></body></html>
"""
