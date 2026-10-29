"""
Generate a synthetic dataset that mirrors the schema of the Olist Brazilian
E-Commerce dataset (Kaggle: olistbr/brazilian-ecommerce).

WHY THIS EXISTS
---------------
The real dataset is hosted on Kaggle and requires a login to download. This
generator lets the pipeline run end to end anywhere (CI, a fresh clone, a
machine with no Kaggle account). It produces the same 9 CSV files with the same
file names and column names, so every script and SQL query in this repo runs
unchanged on the real data.

IMPORTANT: figures produced from this synthetic data are NOT real business
results. For any number you quote publicly (README, resume, LinkedIn), download
the real dataset and re-run the pipeline. See README.md -> "Using the real data".

Usage:
    python src/generate_synthetic_data.py --orders 40000 --seed 42
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"

# (state, share of customers, lat, lng) - shares approximate Olist's skew toward SP
STATES = [
    ("SP", 0.420, -23.55, -46.63), ("RJ", 0.129, -22.91, -43.17),
    ("MG", 0.117, -19.92, -43.94), ("RS", 0.055, -30.03, -51.23),
    ("PR", 0.051, -25.43, -49.27), ("SC", 0.037, -27.59, -48.55),
    ("BA", 0.034, -12.97, -38.50), ("DF", 0.021, -15.79, -47.88),
    ("ES", 0.020, -20.32, -40.34), ("GO", 0.020, -16.68, -49.25),
    ("PE", 0.017, -8.05, -34.88), ("CE", 0.013, -3.73, -38.52),
    ("PA", 0.010, -1.46, -48.49), ("MT", 0.009, -15.60, -56.10),
    ("MA", 0.007, -2.53, -44.30), ("MS", 0.007, -20.47, -54.62),
    ("PB", 0.005, -7.12, -34.86), ("RN", 0.005, -5.79, -35.21),
    ("PI", 0.004, -5.09, -42.80), ("AL", 0.004, -9.67, -35.74),
    ("SE", 0.003, -10.91, -37.07), ("TO", 0.003, -10.18, -48.33),
    ("RO", 0.002, -8.76, -63.90), ("AM", 0.002, -3.12, -60.02),
    ("AC", 0.001, -9.97, -67.81), ("AP", 0.001, 0.03, -51.07),
    ("RR", 0.001, 2.82, -60.67),
]

# (english name, portuguese name, share of items, median price BRL, weight g, photos)
CATEGORIES = [
    ("bed_bath_table", "cama_mesa_banho", 0.098, 90, 2200),
    ("health_beauty", "beleza_saude", 0.087, 130, 800),
    ("sports_leisure", "esporte_lazer", 0.078, 90, 1500),
    ("furniture_decor", "moveis_decoracao", 0.075, 80, 4000),
    ("computers_accessories", "informatica_acessorios", 0.070, 100, 700),
    ("housewares", "utilidades_domesticas", 0.062, 75, 1800),
    ("watches_gifts", "relogios_presentes", 0.054, 200, 500),
    ("telephony", "telefonia", 0.042, 60, 300),
    ("garden_tools", "ferramentas_jardim", 0.040, 85, 3500),
    ("auto", "automotivo", 0.038, 95, 1800),
    ("toys", "brinquedos", 0.037, 85, 1100),
    ("cool_stuff", "cool_stuff", 0.033, 110, 900),
    ("perfumery", "perfumaria", 0.031, 80, 400),
    ("baby", "bebes", 0.028, 85, 1500),
    ("electronics", "eletronicos", 0.026, 70, 600),
    ("stationery", "papelaria", 0.025, 55, 500),
    ("fashion_bags_accessories", "fashion_bolsas_e_acessorios", 0.022, 80, 600),
    ("pet_shop", "pet_shop", 0.018, 75, 2500),
    ("office_furniture", "moveis_escritorio", 0.014, 190, 12000),
    ("home_appliances", "eletrodomesticos", 0.019, 140, 5000),
    ("books_general_interest", "livros_interesse_geral", 0.012, 45, 450),
    ("musical_instruments", "instrumentos_musicais", 0.010, 170, 2000),
    ("construction_tools_construction", "construcao_ferramentas_construcao", 0.010, 120, 3500),
    ("luggage_accessories", "bagagem_acessorios", 0.008, 140, 1800),
    ("small_appliances", "eletroportateis", 0.010, 190, 2500),
]

STATUS_WEIGHTS = {"delivered": 0.972, "shipped": 0.011, "canceled": 0.006,
                  "unavailable": 0.006, "invoiced": 0.003, "processing": 0.002}


def _ids(rng: np.random.Generator, n: int) -> np.ndarray:
    """32-char hex ids, like the real dataset."""
    raw = rng.integers(0, 16**8, size=(n, 4), dtype=np.int64)
    return np.array(["".join(f"{v:08x}" for v in row) for row in raw])


def generate(n_orders: int = 40_000, seed: int = 42) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)

    # ------------------------------------------------------------------ geography
    st_codes = np.array([s[0] for s in STATES])
    st_p = np.array([s[1] for s in STATES]); st_p = st_p / st_p.sum()

    # ------------------------------------------------------------------ customers
    # ~3% of people buy twice - the real dataset is famous for very low repeat rate
    n_people = int(n_orders / 1.034)
    person_ids = _ids(rng, n_people)
    person_state = rng.choice(st_codes, size=n_people, p=st_p)
    person_zip = rng.integers(1000, 99999, size=n_people)
    person_city = np.array([f"city_{s.lower()}_{z % 40:02d}" for s, z in zip(person_state, person_zip)])

    # orders per person: 1 for most, 2+ for a few
    extra = rng.random(n_people) < 0.030
    orders_per_person = np.where(extra, 1 + rng.integers(1, 3, size=n_people), 1)
    owner = np.repeat(np.arange(n_people), orders_per_person)
    if len(owner) >= n_orders:
        owner = owner[:n_orders]
    else:
        pad = rng.integers(0, n_people, size=n_orders - len(owner))
        owner = np.concatenate([owner, pad])
    rng.shuffle(owner)
    n = len(owner)

    order_ids = _ids(rng, n)
    customer_ids = _ids(rng, n)  # per-order id, exactly like Olist

    customers = pd.DataFrame({
        "customer_id": customer_ids,
        "customer_unique_id": person_ids[owner],
        "customer_zip_code_prefix": person_zip[owner],
        "customer_city": person_city[owner],
        "customer_state": person_state[owner],
    })

    # ------------------------------------------------------------------ order dates
    # Growth from Jan 2017 to Aug 2018, Black Friday spike in Nov 2017
    months = pd.period_range("2017-01", "2018-08", freq="M")
    base = np.linspace(0.12, 1.0, len(months)) ** 1.1
    bump = np.ones(len(months))
    bump[list(months).index(pd.Period("2017-11"))] = 1.65
    bump[list(months).index(pd.Period("2018-05"))] = 1.10
    w = base * bump; w = w / w.sum()
    month_idx = rng.choice(len(months), size=n, p=w)
    day_off = rng.integers(0, 28, size=n)
    dow_bias = rng.choice([0, 1, 2, 3, 4, 5, 6], size=n, p=[.17, .17, .16, .15, .14, .09, .12])
    purchase = (pd.to_datetime([str(months[i].start_time.date()) for i in month_idx])
                + pd.to_timedelta(day_off, unit="D"))
    # nudge to the biased weekday
    shift = (dow_bias - purchase.dayofweek.to_numpy()) % 7
    purchase = purchase + pd.to_timedelta(shift, unit="D")
    hour_p = np.array([.8, .4, .2, .1, .1, .2, .6, 1.5, 3.2, 4.8, 6.0, 6.5, 6.2, 6.0, 6.3,
                       6.5, 6.4, 5.8, 5.5, 6.0, 7.0, 7.5, 5.2, 2.5]); hour_p = hour_p / hour_p.sum()
    hours = rng.choice(24, size=n, p=hour_p)
    purchase = purchase + pd.to_timedelta(hours, unit="h") + pd.to_timedelta(rng.integers(0, 3600, size=n), unit="s")
    purchase = pd.DatetimeIndex(np.minimum(pd.DatetimeIndex(purchase).to_numpy(),
                                           np.datetime64("2018-08-28T12:00:00", "ns")))

    status = rng.choice(list(STATUS_WEIGHTS), size=n, p=list(STATUS_WEIGHTS.values()))

    # ------------------------------------------------------------------ geography -> delivery
    cust_state = customers["customer_state"].to_numpy()
    far = np.isin(cust_state, ["RR", "AP", "AM", "AC", "RO", "PA", "MA", "PI", "TO", "AL", "SE", "CE", "RN", "PB"])
    mid = np.isin(cust_state, ["BA", "PE", "MT", "MS", "GO", "DF", "ES", "SC", "RS", "PR"])
    base_days = np.where(far, 18.0, np.where(mid, 12.0, 8.0))
    transit = rng.gamma(shape=4.0, scale=base_days / 4.0)
    # a late tail: ~8% orders have big problems
    problem = rng.random(n) < np.where(far, 0.16, 0.07)
    transit = transit + np.where(problem, rng.gamma(2.5, 6.0, size=n), 0)
    approve_h = rng.gamma(2.0, 4.0, size=n)
    carrier_days = rng.gamma(2.5, 1.2, size=n) + 0.5

    approved = purchase + pd.to_timedelta(approve_h, unit="h")
    to_carrier = approved + pd.to_timedelta(carrier_days, unit="D")
    delivered = purchase + pd.to_timedelta(transit + carrier_days * 0.5, unit="D")
    delivered = delivered.where(delivered > to_carrier, to_carrier + pd.Timedelta(days=2))
    # promised date: seller/platform estimate with a buffer, tighter in the south-east
    est_buffer = np.where(far, 17.0, np.where(mid, 12.5, 10.0)) + rng.normal(0, 2.5, size=n)
    estimated = purchase + pd.to_timedelta(base_days + est_buffer, unit="D")
    estimated = estimated.floor("D") + pd.Timedelta(hours=23, minutes=59, seconds=59)

    is_deliv = status == "delivered"
    is_shipped_like = np.isin(status, ["shipped", "delivered"])
    orders = pd.DataFrame({
        "order_id": order_ids,
        "customer_id": customer_ids,
        "order_status": status,
        "order_purchase_timestamp": purchase,
        "order_approved_at": approved,
        "order_delivered_carrier_date": to_carrier.where(is_shipped_like),
        "order_delivered_customer_date": delivered.where(is_deliv),
        "order_estimated_delivery_date": estimated,
    })
    # a sliver of missing approvals / carrier dates, as in the real data
    orders.loc[rng.random(n) < 0.0016, "order_approved_at"] = pd.NaT
    orders.loc[rng.random(n) < 0.0018, "order_delivered_carrier_date"] = pd.NaT

    # ------------------------------------------------------------------ sellers
    n_sellers = max(300, n // 32)
    seller_ids = _ids(rng, n_sellers)
    seller_state_p = np.array([.60, .08, .08, .05, .05, .03, .02, .02, .02, .02, .03])
    seller_states = np.array(["SP", "RJ", "MG", "RS", "PR", "SC", "BA", "DF", "ES", "GO", "PE"])
    sellers = pd.DataFrame({
        "seller_id": seller_ids,
        "seller_zip_code_prefix": rng.integers(1000, 99999, size=n_sellers),
        "seller_city": [f"city_seller_{i % 60:02d}" for i in range(n_sellers)],
        "seller_state": rng.choice(seller_states, size=n_sellers, p=seller_state_p / seller_state_p.sum()),
    })
    # seller activity is heavy-tailed (a few sellers do most of the volume)
    seller_activity = rng.pareto(1.3, size=n_sellers) + 0.2
    seller_activity = seller_activity / seller_activity.sum()
    # seller quality - some are consistently bad, drives review scores later
    seller_quality = np.clip(rng.normal(0, 1, size=n_sellers), -2.5, 2.5)

    # ------------------------------------------------------------------ products
    n_products = max(1500, n // 3)
    cat_en = np.array([c[0] for c in CATEGORIES]); cat_pt = np.array([c[1] for c in CATEGORIES])
    cat_p = np.array([c[2] for c in CATEGORIES]); cat_p = cat_p / cat_p.sum()
    cat_price = np.array([c[3] for c in CATEGORIES], dtype=float)
    cat_weight = np.array([c[4] for c in CATEGORIES], dtype=float)
    prod_cat_idx = rng.choice(len(CATEGORIES), size=n_products, p=cat_p)
    prod_price = np.exp(rng.normal(np.log(cat_price[prod_cat_idx]), 0.75))
    prod_price = np.clip(np.round(prod_price, 2), 4.9, 6500)
    weight = np.clip(np.round(np.exp(rng.normal(np.log(cat_weight[prod_cat_idx]), 0.8))), 50, 40000)
    products = pd.DataFrame({
        "product_id": _ids(rng, n_products),
        "product_category_name": cat_pt[prod_cat_idx],
        "product_name_lenght": rng.integers(20, 70, size=n_products),
        "product_description_lenght": rng.integers(150, 2500, size=n_products),
        "product_photos_qty": rng.choice([1, 2, 3, 4, 5, 6], size=n_products, p=[.45, .25, .13, .08, .05, .04]),
        "product_weight_g": weight.astype(int),
        "product_length_cm": rng.integers(16, 60, size=n_products),
        "product_height_cm": rng.integers(2, 40, size=n_products),
        "product_width_cm": rng.integers(11, 50, size=n_products),
    })
    # ~1.8% of products have no category, like the real data
    products.loc[rng.random(n_products) < 0.018,
                 ["product_category_name", "product_name_lenght", "product_description_lenght", "product_photos_qty"]] = np.nan

    translation = pd.DataFrame({
        "product_category_name": cat_pt,
        "product_category_name_english": cat_en,
    })

    # ------------------------------------------------------------------ order items
    n_items = 1 + rng.choice([0, 1, 2, 3], size=n, p=[.883, .097, .014, .006])
    item_order_idx = np.repeat(np.arange(n), n_items)
    item_no = np.concatenate([np.arange(1, k + 1) for k in n_items])
    item_prod_idx = rng.integers(0, n_products, size=len(item_order_idx))
    item_seller_idx = rng.choice(n_sellers, size=len(item_order_idx), p=seller_activity)
    price = prod_price[item_prod_idx] * np.exp(rng.normal(0, 0.06, size=len(item_order_idx)))
    price = np.round(np.clip(price, 0.85, 6735), 2)
    cust_far = far[item_order_idx]; cust_mid = mid[item_order_idx]
    freight = (7.5 + weight[item_prod_idx] / 1000 * 1.9
               + np.where(cust_far, 14.0, np.where(cust_mid, 7.5, 3.0))
               + rng.gamma(2.0, 1.8, size=len(item_order_idx)))
    freight = np.round(np.clip(freight, 0, 410), 2)
    shipping_limit = (orders["order_approved_at"].fillna(orders["order_purchase_timestamp"])
                      .to_numpy()[item_order_idx] + pd.to_timedelta(rng.integers(2, 6, size=len(item_order_idx)), unit="D").to_numpy())
    order_items = pd.DataFrame({
        "order_id": order_ids[item_order_idx],
        "order_item_id": item_no,
        "product_id": products["product_id"].to_numpy()[item_prod_idx],
        "seller_id": seller_ids[item_seller_idx],
        "shipping_limit_date": shipping_limit,
        "price": price,
        "freight_value": freight,
    })

    # ------------------------------------------------------------------ payments
    order_total = (pd.Series(price + freight).groupby(item_order_idx).sum()
                   .reindex(range(n)).to_numpy())
    pay_type = rng.choice(["credit_card", "boleto", "voucher", "debit_card"], size=n, p=[.735, .195, .055, .015])
    installments = np.where(
        pay_type == "credit_card",
        np.clip(np.round(rng.gamma(1.1, 3.2, size=n)).astype(int) + 1, 1, 24) *
        np.where(order_total > 150, 1, (rng.random(n) < .45)),
        1,
    )
    installments = np.maximum(installments, 1)
    pay_rows = []
    pay_main = pd.DataFrame({
        "order_id": order_ids, "payment_sequential": 1, "payment_type": pay_type,
        "payment_installments": installments, "payment_value": np.round(order_total, 2),
    })
    # ~2.9% of orders are split with a voucher (sequential 2)
    split = rng.random(n) < 0.029
    split_amt = np.round(order_total * rng.uniform(0.1, 0.5, size=n), 2)
    pay_main.loc[split, "payment_value"] = np.round(order_total[split] - split_amt[split], 2)
    pay_second = pd.DataFrame({
        "order_id": order_ids[split], "payment_sequential": 2, "payment_type": "voucher",
        "payment_installments": 1, "payment_value": split_amt[split],
    })
    order_payments = pd.concat([pay_main, pay_second], ignore_index=True)

    # ------------------------------------------------------------------ reviews
    # Score depends on lateness (strongest driver), seller quality, and noise.
    actual_vs_est = (delivered - estimated).total_seconds().to_numpy() / 86400
    late_days = np.where(is_deliv, actual_vs_est, 0)
    first_seller = np.zeros(n, dtype=int)
    first_mask = item_no == 1
    first_seller[item_order_idx[first_mask]] = item_seller_idx[first_mask]
    q = seller_quality[first_seller]
    latent = (4.50 - 0.11 * np.clip(late_days, 0, 40) - 0.9 * (late_days > 0)
              + 0.30 * q + rng.normal(0, 1.30, size=n))
    latent = np.where(status == "canceled", latent - 1.6, latent)
    latent = np.where(~is_deliv & (status != "canceled"), latent - 0.8, latent)
    score = np.clip(np.round(latent), 1, 5).astype(int)
    # ~99% of orders have a review row; ~58% of reviews have free-text comments
    has_rev = rng.random(n) < 0.985
    rv = np.where(has_rev)[0]
    answer_lag = rng.gamma(1.4, 2.0, size=len(rv))
    rev_created = (delivered.where(is_deliv, purchase + pd.Timedelta(days=15)).to_numpy()[rv]
                   + pd.to_timedelta(rng.integers(0, 4, size=len(rv)), unit="D").to_numpy())
    comments = np.where(rng.random(len(rv)) < 0.42, None, "comment")
    order_reviews = pd.DataFrame({
        "review_id": _ids(rng, len(rv)),
        "order_id": order_ids[rv],
        "review_score": score[rv],
        "review_comment_title": np.where(comments == None, None, "title"),  # noqa: E711
        "review_comment_message": np.where(comments == None, None, "message"),  # noqa: E711
        "review_creation_date": pd.to_datetime(rev_created).floor("D"),
        "review_answer_timestamp": pd.to_datetime(rev_created) + pd.to_timedelta(answer_lag, unit="D"),
    })

    # ------------------------------------------------------------------ geolocation
    geo_rows = []
    s_lookup = {s[0]: (s[2], s[3]) for s in STATES}
    uz = pd.DataFrame({"z": np.concatenate([customers["customer_zip_code_prefix"], sellers["seller_zip_code_prefix"]]),
                       "s": np.concatenate([customers["customer_state"], rng.choice(seller_states, size=len(sellers))])}).drop_duplicates("z")
    lat = uz["s"].map(lambda s: s_lookup[s][0]).to_numpy() + rng.normal(0, 0.6, size=len(uz))
    lng = uz["s"].map(lambda s: s_lookup[s][1]).to_numpy() + rng.normal(0, 0.6, size=len(uz))
    geolocation = pd.DataFrame({
        "geolocation_zip_code_prefix": uz["z"].to_numpy(),
        "geolocation_lat": lat, "geolocation_lng": lng,
        "geolocation_city": [f"city_{s.lower()}" for s in uz["s"]],
        "geolocation_state": uz["s"].to_numpy(),
    })

    return {
        "olist_customers_dataset": customers,
        "olist_geolocation_dataset": geolocation,
        "olist_order_items_dataset": order_items,
        "olist_order_payments_dataset": order_payments,
        "olist_order_reviews_dataset": order_reviews,
        "olist_orders_dataset": orders,
        "olist_products_dataset": products,
        "olist_sellers_dataset": sellers,
        "product_category_name_translation": translation,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--orders", type=int, default=40_000, help="approx. number of orders")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=RAW_DIR)
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    tables = generate(args.orders, args.seed)
    for name, df in tables.items():
        df.to_csv(args.out / f"{name}.csv", index=False)
        print(f"wrote {name}.csv  ({len(df):,} rows)")
    (args.out / "_SYNTHETIC_DATA.txt").write_text(
        "These CSVs were generated by src/generate_synthetic_data.py, not downloaded from Kaggle.\n"
        "Delete this file and the CSVs, then add the real Olist files to use real data.\n")


if __name__ == "__main__":
    main()
