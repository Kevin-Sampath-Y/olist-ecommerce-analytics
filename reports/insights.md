> Figures below were computed on the public **Olist Brazilian E-Commerce** dataset.


### Headline metrics

| Metric | Value |
|---|---|
| Orders analysed | 98,199 |
| Unique customers | 94,983 |
| Revenue (excl. freight) | R$13.49M |
| Average order value | R$137 |
| Average review score | 4.12 / 5 |
| Late deliveries | 8.1% |
| Average delivery time | 12.6 days |
| Customers who ordered more than once | 3.0% |

### Key findings

1. **Strong growth with a seasonal spike.** Monthly revenue grew about 7x over 20 months; 2017-11 jumped 52% over the previous month, and the highest month was 2017-11 (R$1.00M).
2. **Revenue is concentrated.** 13 of 74 categories deliver 70% of revenue (largest: *health beauty*, 9.3%), and state **SP** alone accounts for 38% of revenue.
3. **Late delivery is the clearest driver of unhappy customers.** On-time orders average 4.29 stars; orders delivered 15+ days late average 1.72, and 78% of them get 1-2 stars. Late orders score 1.73 stars lower on average (95% bootstrap CI -1.76 to -1.69; Mann-Whitney p < 0.001).
4. **Retention is the biggest untapped opportunity.** Only 3.0% of customers ever buy twice and 0.45% return in the month after their first order. Repeat buyers generate 3.1% of revenue in the last six months.
5. **High-value customers are drifting away.** The *At-Risk High-Value* RFM segment is 15% of customers but 29% of historical revenue; true *Champions* are only 1.3% of customers.
6. **Geography drives service quality.** *AL* has the highest late rate among states with 100+ orders (24%), and *MA* has the heaviest freight burden (26% of item value).
7. **Seller quality is uneven.** 31 of 627 established sellers have both poor reviews and late deliveries.
8. **Payments.** Credit cards carry 78% of payment value with an average of 3.5 instalments.
9. **Driver model.** A class-balanced logistic regression flags bad reviews with ROC-AUC 0.73; the strongest predictor is *total delivery time (days)* (odds ratio 1.82 per standard deviation). This is association, not proof of causation.

### Recommendations

- **Reset delivery promises** for slow regions such as AL: under-promise and over-deliver to protect review scores.
- **Run a seller improvement programme** starting with the 31 sellers flagged *Action* in the scorecard.
- **Launch a win-back campaign** (coupon or free shipping) for the At-Risk High-Value segment, and a post-purchase journey to lift second-order rate.
- **Plan capacity ahead of seasonal peaks** (the 2017-11 spike, +52% in one month) to keep delivery times flat.
- **Test free-shipping thresholds** in high-freight states (MA) to lift conversion.

### Data validation

- PASS: Revenue (SQL vs pandas) (SQL 13,494,400.74 vs pandas 13,494,400.74)
- PASS: Valid orders (SQL 98,199 vs pandas 98,199)
- PASS: Unique customers (SQL 94,983 vs pandas 94,983)
- PASS: Late delivery % (SQL 8.11 vs pandas 8.11)
- PASS: RFM customers (view vs unique customers) (SQL 94,983 vs pandas 94,983)
