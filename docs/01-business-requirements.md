# Business Requirements Document (BRD) - FinTech Lakehouse

| Version | Date       | Author             | Status |
| ------- | ---------- | ------------------ | ------ |
| 1.0     | 2026-02-21 | Mohamed Abdellatef | Final  |
| 1.1     | 2026-02-28 | Mohamed Abdellatef | Final  |

> **Purpose:** To build a scalable, end-to-end Medallion data architecture that processes high-volume digital wallet transactions, enabling rapid fraud detection, user behavior analysis, and automated financial reconciliation.
> **Dataset:** Synthetic FinTech Payment Data (1M+ records, 7 core entities + 1 reference array).

---

## 1) Business Context

### 1.1 Scenario

A fast-growing digital payment platform operating across the MENA region (focusing on Egypt, Saudi Arabia, and the UAE) provides peer-to-peer (P2P) transfers, merchant payments, and multi-currency digital wallets. As transaction volumes rapidly scale to millions of records, the platform requires a robust, centralized data foundation to monitor financial health and intercept sophisticated fraudulent activities.

### 1.2 Business Problem

- **Data Silos:** User identity records (KYC), device fingerprints, and core transactions reside in disconnected raw formats, delaying comprehensive risk analysis.
- **Slow Fraud Detection:** Legacy systems fail to provide timely insights into complex fraud patterns (e.g., location jumping, device spoofing, velocity attacks).
- **Reconciliation Bottlenecks:** Complex multi-currency transactions across different timezones cause manual overhead and delays in financial reporting.

**Problem Statement**

> The lack of a centralized, conformed, and automated Lakehouse platform prevents the Risk and Finance teams from making rapid, data-driven decisions to protect user assets and optimize platform revenue.

### 1.3 Objectives (Success = Measurable)

| Objective                                   | Success Criteria                                                                                                                   |
| ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| **Consolidate Data Sources**                | 100% of the 7 raw entities are ingested into Bronze and curated in Silver daily; Gold star schema models are built for analytics-critical entities and KPIs.                                           |
| **Enable Multi-dimensional Fraud Analysis** | Reduce the data preparation time for Risk Analysts from days to hours by linking transactions to devices and KYC statuses.         |
| **Automate Financial Reconciliation**       | Deliver automated Total Payment Volume (TPV) and revenue aggregations with zero discrepancies while handling multi-currency conversions. |

---

## 2) Stakeholders & Use Cases

| Stakeholder                  | Decisions / Needs                                                                                              | Output                                 |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------- | -------------------------------------- |
| **Fraud & Risk Team**        | Identify suspicious transaction patterns (velocity, untrusted devices) to block compromised accounts.          | Daily Fraud Alert & Risk Dashboards    |
| **Finance & Reconciliation** | Reconcile daily transaction volumes, track liquidity, and calculate merchant fees accurately.                  | Automated TPV & Revenue Reports        |
| **Product & Growth Team**    | Understand user adoption of payment methods (e.g., Mada, Meeza) and wallet tiers to drive marketing campaigns. | User Behavior & Demographics Analytics |

**Primary Use Cases:**

1. Proactive Fraud Pattern Detection (Velocity, Location, Device).
2. Multi-currency Daily TPV and Revenue Aggregation.
3. KYC Verification Impact and Account Tier Analytics.

---

## 3) Business Questions

**Financial & Growth:**

1. What is the Total Payment Volume (TPV) and generated revenue (fees) per day, broken down by currency and merchant category?
2. Which payment methods (e.g., Visa, Mada, Meeza, Wallet Balance) have the highest success rates and adoption (share of successful transactions by provider "volume adoption" not share of users) across different user geographic locations?
3. What is the ratio of P2P transfers versus Merchant Payments, and how does this distribution vary between Basic and Platinum users?
4. What is the average transaction value (ATV) per country?

**Fraud & Risk:**

5. How many high-value transactions were initiated from newly registered, untrusted devices within 24 hours of account creation?
**Definition Note (Q5):**  
- "account creation" refers to the sender wallet account (`sender_account_id` → `accounts.created_at`), not `users.registration_date`.  
- "Newly registered device" = `devices.first_seen_at` within 24 hours of `accounts.created_at`.
- All time windows are evaluated using Silver UTC-standardized timestamps (see Section 5.4).

6. Which users exhibit "location jumping" patterns (e.g., transacting from two geographically distant locations within an impossible timeframe)?
**Definition Note (Q6):**

* **Transactions included:** All attempted transactions (all statuses).
* **Entity tracked:** `user_id` (sender user).
* **Event time:** Use `transaction_timestamp` (UTC per Section 5.4).
* **Location jumping rule:** A user is flagged if they have **two transactions** where:
  * Both transactions belong to the same `user_id`
  * **distance ≥ 500 km** AND **time difference ≤ 60 minutes**
    *(implies unrealistic travel between locations)*

> Note: distance is computed from `transactions.latitude` and `transactions.longitude`.

7. What is the correlation between rejected/pending KYC statuses and reversed or failed transactions?
8. Which active merchant accounts are receiving an unusually high volume of transactions from newly funded wallets (potential money laundering indicator)?

**Definition Note (Q8):**
* **Active merchant:** `merchants.is_active = True` 
* **Newly funded wallet:** A wallet is “newly funded” if it had a **Deposit** (`transaction_type='Deposit'`) within the last **24 hours** before the merchant payment.
* **High volume:** a merchant is flagged if it receives ≥ 50 transactions in a day from newly funded wallets.
* **Transactions included:** `receiver_type = 'merchant'` (Merchant payments only). 
* **Time window:** Evaluate volume **per day** (UTC per Section 5.4).

**User Behavior & Retention:**

9. How many daily/monthly active users (DAU/MAU) do we have, and what is the trend over time?
10. What percentage of users complete their first transaction within 7 days of registration?
**Definition Note (Q10):**
- First transaction = first successful transaction; denominator = all registered users.

11. What is the user retention rate at 30/60/90 days by country and user tier?
**Definition Note (Q11):**
- Retention = user has ≥1 successful transaction at 30/60/90 days after registration.

12. Which user tiers (Basic, Silver, Gold, Platinum) have the highest transaction frequency and volume?
**Definition Note (Q12):**
- Volume is reported per transaction currency (no cross-currency mixing);
frequency/volume are based on successful transactions.

**Device & Channel:**

13. What is the distribution of transactions by device type (iOS vs Android vs Web)?
14. Which device models have the highest fraud flag rates?
15. How does transaction success rate vary across different app versions?

**Operational & Data Quality:**

16. What is the current data freshness (hours since last Gold layer refresh)?
17. What percentage of records are quarantined due to data quality issues, and what are the top failure reasons?
18. Are there any orphan records (e.g., transactions referencing non-existent accounts or users)?

**Implementation Note:**  
Q16 and Q17 are operational KPIs produced by Silver/Gold monitoring outputs, not raw generator files alone.  
Planned supporting tables: `gold_refresh_audit`, `dq_quarantine`, `dq_metrics`.

---

## 4) KPI Definitions (Catalog)

> **Rule:** For ratio KPIs, compute as ratio of sums (not AVG of per-row ratios).

### 4.1 Financial KPIs

**KPI-01 Total Payment Volume (TPV)**

- Definition: Sum of all successful transaction amounts
- Formula: `SUM(amount) WHERE status = 'Success'`
- Grain: day/week/month; currency; country; merchant_category
- Filters: `status = 'Success'`
- Note: `merchant_category` is populated only when `receiver_type='merchant'`; otherwise NULL (may be shown as “Non-merchant” in reporting).

**KPI-02 Transaction Revenue (Fees)**

- Definition: Sum of all fee amounts collected
- Formula: `SUM(fee_amount) WHERE status = 'Success'`
- Grain: day/week/month; merchant_category; country
- Filters: `status = 'Success'`

**KPI-03 Average Transaction Value (ATV)**

- Definition: Average value per successful transaction
- Formula: `TPV / COUNT(DISTINCT transaction_id)`
- Computation basis: Silver deduplicated transactions keyed by `transaction_id`
- Grain: day/week/month; country; transaction_type
- Filters: `status = 'Success'`
- Note: For user behavior KPIs, “country” refers to sender user country (`users.country`).

**KPI-04 Transaction Success Rate**

- Definition: Percentage of attempted transactions that completed successfully
- Formula: `COUNT(status='Success') / COUNT(status IN ('Success','Failed','Pending','Reversed')) * 100`
- Grain: day; payment_method; country
- Filters: None

### 4.2 Fraud & Risk KPIs

**KPI-05 Fraud Flag Rate**

- Definition: Percentage of transactions flagged as suspicious
- Formula: `COUNT(is_flagged=True) / COUNT(*) * 100`
- Grain: day/week; fraud_pattern
- Filters: None

**KPI-06 Untrusted Device Transaction Rate**

- Definition: % of transactions from untrusted devices
- Formula: `COUNT(devices.is_trusted=False) / COUNT(*) * 100`
- Grain: day; country
- Filters: None

**KPI-07 High-Risk Transaction Amount**

- Definition: Sum of amounts from flagged transactions
- Formula: `SUM(amount) WHERE is_flagged = True`
- Grain: day/week
- Filters: `is_flagged = True`

### 4.3 User & Adoption KPIs

**KPI-08 Active Users (Daily/Monthly)**

- Definition: Distinct users with >=1 successful transaction
- Formula: `COUNT(DISTINCT user_id) WHERE status = 'Success'`
- Grain: day (DAU) / month (MAU)
- Filters: `status = 'Success'`

**KPI-09 KYC Verification Rate**

- Definition: % of active users with verified KYC status
- Formula: `COUNT(user_id WHERE is_active=True AND kyc_status='verified') / COUNT(user_id WHERE is_active=True) * 100`
- Grain: month; country
- Filters: `is_active = True`

**KPI-10 Payment Method Adoption**

- Definition: Distribution of transactions by payment method provider
- Formula: `COUNT(*) per provider / SUM(COUNT(*)) OVER (same grain) * 100`
- Grain: month; country
- Filters: `status = 'Success'`

### 4.4 Data Reliability KPIs (Pipeline Health)

**KPI-11 Gold Layer Freshness**

- Definition: Hours since last successful Gold layer refresh
- Formula: `NOW() - MAX(last_refresh_ts)`
- Target: `< 24 hours`

**KPI-12 Quarantine Rate**

- Definition: % of records failing DQ rules per entity
- Formula: `quarantined_rows / total_rows * 100`
- Target: `< 2%`

**KPI-13 Data Completeness**

- Definition: % of records with non-null critical fields
- Formula: `COUNT(critical_field IS NOT NULL) / COUNT(*) * 100`
- Target: `> 98%`

---

## 5) Semantic Rules (Locked Decisions)

### 5.1 KPI Status Scope (Locked)

- **Financial value KPIs (TPV, Fees, ATV):** Include `Success` only.
- **Attempt/operational KPIs (e.g., success rate, DQ/refresh metrics):** May include all attempt statuses when explicitly defined.
- **Rationale:** Money-movement KPIs must reflect completed value, while attempt/operational KPIs require full status coverage.

### 5.2 Fraud Flag Definition (Locked)

- **is_flagged = True** when ANY of these patterns detected:
  - `velocity`: >5 transactions in 10 minutes per `sender_account_id`
  - `amount`: Single transaction above threshold by transaction currency (threshold source: `fraud_rules` by currency; fallback = 50,000 in transaction currency; Gold may also calculate USD-equivalent thresholds)
  - `time`: Transaction between 02:00-05:00 local time using timezone derived from user country (fallback to UTC if country/timezone is missing)
  - `new_device`: First transaction from a new `device_id` for the sender account with amount > `fraud_rules.new_device_threshold` for that transaction currency (fallback = 10,000 in transaction currency)
  - `cross_border`: Transaction currency does not match `users.preferred_currency` for the sender account
- **Untrusted device** = `devices.is_trusted = False`
- **Rationale:** Aligns with industry-standard fraud detection heuristics. Cross-border rule addresses MENA-specific risk where compromised accounts are used from foreign jurisdictions.

### 5.3 Currency Policy (Locked)

- **All monetary values stored in:** Original transaction currency (EGP, SAR, AED, KWD, QAR)
- **No currency conversion applied** in Bronze/Silver layers
- **Gold layer:** May include USD-equivalent column for cross-country comparison (using daily exchange rate snapshot)
- **Rationale:** Preserving original currency prevents rounding errors and audit issues.

### 5.4 Timezone Policy (Locked)

- **Bronze/raw timestamps:** Stored as generated source timestamps (naive).
- **Silver timestamps:** Normalized to UTC and validated.
- **Gold timestamps:** Use Silver UTC-standardized timestamps.
- **Reporting day derived from:** `transaction_timestamp` truncated to DATE in UTC
- **Local time derivation:** Use user's `country` field to derive local timezone when needed
- **Rationale:** UTC standardization prevents timezone ambiguity in multi-region operations.

### 5.5 User Identification (Locked)

- **Primary user key:** `user_id` (UUID)
- **For deduplication:** `user_id` is unique; no separate `customer_unique_id` needed
- **Rationale:** Synthetic data already has clean user identity; real systems would need fuzzy matching.

### 5.6 Transaction Amount Definition (Locked)

- **Amount field includes:** Principal transaction value only
- **Fee field:** Stored separately as `fee_amount`
- **Total charged to user:** `amount + fee_amount`
- **Rationale:** Separating fees enables accurate revenue reporting and merchant settlement calculations.

---

## 6) Data Scope (Source Entities)

### 6.1 Entity Overview & Volume Estimates

| Entity | Description | ~Columns | Expected Records | Growth (daily) |
|--------|-------------|----------|-----------------|----------------|
| `users` | Customer profiles with MENA demographics (Arabic, Indian, Pakistani, Filipino, Western names), KYC status, tier, and geo | 16 | 50,000 | ~500 |
| `accounts` | Wallet/Savings accounts per user (1-2 per user), with currency, balance, and daily/monthly limits | 10 | ~62,500 | ~625 |
| `merchants` | Business entities with MENA-authentic names, category, risk score, fee percentage, and verification status | 14 | 2,000 | ~20 |
| `transactions` | Core payment events with sender, receiver, amount, fraud flags, device, IP, geolocation, and timestamps | 20 | 1,000,000 | ~50,000 |
| `devices` | Device fingerprints per user (1-3 per user), with type, model, OS, app version, and trust status | 11 | ~87,500 | ~875 |
| `kyc_records` | KYC verification records with document type (country-specific: Iqama, Emirates ID, etc.), status, and risk flags | 14 | 50,000 | ~500 |
| `payment_methods` | Linked cards/bank accounts per user (1-3 per user), with regional providers (Mada, Meeza, KNET) | 12 | ~80,000 | ~800 |

> **Note:** Volume figures reflect initial generation via the Python data generator. Daily growth rates are estimated for a production simulation scenario.

### 6.2 Polymorphic Receiver Pattern

The `transactions` table uses a **polymorphic receiver** pattern:

| `receiver_type` | `receiver_id` resolves to | Transaction Types | Description |
|-----------------|--------------------------|-------------------|-------------|
| `'account'` | `accounts.account_id` | P2P_Transfer | Person-to-person money transfer between wallets |
| `'merchant'` | `merchants.merchant_id` | Merchant_Payment | Payment to a business |
| `'self'` | `NULL` | Deposit, Withdrawal, Bill_Payment | Self-directed: user adds money to own wallet, cashes out, or pays a utility bill - no external receiver entity |

### 6.3 Raw Landing Format (Locked)

- Default raw output format is `CSV` for Bronze realism and ETL schema handling.
- `parquet` is optional for local experiments only.

### 6.4 Reference/Lookup

**`fraud_rules`** (reference list, not a generated raw table):

| Currency | High-Value Threshold | New-Device Threshold | Notes |
|----------|---------------------|----------------------|-------|
| EGP | 50,000 | 10,000 | Generator default |
| SAR | 20,000 | 5,000 | ~5x stronger than EGP |
| AED | 20,000 | 5,000 | Similar purchasing power to SAR |
| KWD | 5,000 | 1,500 | Highest denomination MENA currency |
| QAR | 20,000 | 5,000 | Similar to SAR/AED |

> **Note:** The data generator uses a flat fallback of 50,000 (high-value) / 10,000 (new-device) for all currencies. Silver/Gold layers should apply the currency-specific thresholds above.

---

## 7) Data Quality & Controls

### 7.1 Critical Record Rules (Quarantine)

Quarantine rows that violate:

- **Missing primary key for the entity:** (e.g., `users.user_id`, `accounts.account_id`, `merchants.merchant_id`, `transactions.transaction_id`)
- **Negative amounts:** `amount < 0` or `fee_amount < 0`
- **Invalid timestamps:** `completed_timestamp < transaction_timestamp`
- **Invalid status:** `status NOT IN ('Success', 'Failed', 'Pending', 'Reversed')`
- **Invalid KYC status:** `kyc_status NOT IN ('verified', 'pending', 'rejected')`
- **Orphan foreign keys:** e.g., `accounts.user_id`, `devices.user_id`, `payment_methods.user_id` not found in `users`; `transactions.sender_account_id` not found in `accounts`; `transactions.device_id` not found in `devices`; `transactions.payment_method_id` not found in `payment_methods`; conditional `transactions.receiver_id` not found in `accounts`/`merchants` based on `receiver_type`

**Quarantine table must store:**

- `entity_name`, `batch_date`, `dq_rule_name`
- `dq_reason`, `source_record_id`, `created_at`

### 7.2 Tests (Minimum)

**Uniqueness + Not Null:**

- `transactions.transaction_id` - unique in Silver layer (Bronze intentionally contains ~1% duplicates for testing), not null
- `users.user_id` - unique, not null
- `accounts.account_id` - unique, not null
- `merchants.merchant_id` - unique, not null

**Referential Integrity:**

- `transactions.sender_account_id` -> `accounts.account_id`
- `transactions.device_id` -> `devices.device_id`
- `transactions.payment_method_id` -> `payment_methods.payment_method_id`
- `transactions.receiver_id` -> `merchants.merchant_id` (when `receiver_type = 'merchant'`)
- `transactions.receiver_id` -> `accounts.account_id` (when `receiver_type = 'account'`)
- `transactions.receiver_id` IS NULL (when `receiver_type = 'self'`)
- `accounts.user_id` -> `users.user_id`
- `devices.user_id` -> `users.user_id`
- `kyc_records.user_id` -> `users.user_id`
- `payment_methods.user_id` -> `users.user_id`

**Accepted Values:**

- `transactions.status` IN ('Success', 'Failed', 'Pending', 'Reversed')
- `transactions.transaction_type` IN ('P2P_Transfer', 'Merchant_Payment', 'Deposit', 'Withdrawal', 'Bill_Payment')
- `users.kyc_status` IN ('verified', 'pending', 'rejected')
- `devices.device_type` IN ('ios', 'android', 'web')

---

## 8) Refresh, Auditability, and Observability

### 8.1 Refresh Expectations

- **Frequency:** Daily batch (for portfolio); production would be hourly or near-real-time
- **Completion time:** < 30 minutes for full refresh (1M transactions)
- **Backfill:** Supported via `batch_date` parameter in ADF
- **Idempotency:** Re-running same `batch_date` performs MERGE (upsert) - safe to retry
- **Watermark boundary:** Incremental loads read rows where event timestamp is `> last_successful_watermark` and `<= current_batch_cutoff`; apply a small configurable lookback window for late-arriving records.

### 8.2 SLA Targets

| SLA | Target | Escalation |
|-----|--------|------------|
| Gold layer daily refresh | Completed by **06:00 UTC** | Alert if not refreshed by 07:00 UTC |
| Quarantine alerts availability | Within **1 hour** of batch completion | Alert to Risk team if delayed |
| Pipeline failure notification | Within **15 minutes** of failure | Auto-retry once, then alert |

### 8.3 Non-Functional Requirements (NFRs)

- **Latency:** Daily batch must meet SLA targets defined in Section 8.2, with one automatic retry on failure.
- **Performance:** Gold dashboard queries p95 < 5 seconds for standard business filters.
- **Reliability:** >= 99% successful daily pipeline runs per calendar month.
- **Data Quality:** Quarantine rate < 2% and completeness > 98% on critical fields.
- **Cost Control:** Enforce portfolio compute budget cap and auto-terminate idle compute within 15 minutes.
- **Retention:** Bronze raw kept 90 days hot and archived to cold storage for 1 year; Silver/Gold retained for 2 years.
- **Security:** Restrict PII access with least-privilege RBAC; expose masked/hashed sensitive fields in analytics outputs.
- **Recoverability:** Re-run any `batch_date` idempotently; target recovery within 60 minutes.

### 8.4 Audit Tables

**load_audit:**
| Column | Type | Description |
|--------|------|-------------|
| run_id | STRING | Unique pipeline run ID |
| entity_name | STRING | Table being loaded |
| batch_date | DATE | Processing date |
| started_ts | TIMESTAMP | Run start time |
| finished_ts | TIMESTAMP | Run end time |
| status | STRING | success/failed |
| rows_read | INT | Input row count |
| rows_written | INT | Output row count |
| rows_quarantined | INT | DQ failures |
| error_message | STRING | Error details (if failed) |

**dq_metrics:**
| Column | Type | Description |
|--------|------|-------------|
| entity_name | STRING | Table name |
| batch_date | DATE | Processing date |
| total_rows | INT | Total processed |
| quarantine_count | INT | Failed DQ |
| quarantine_rate | FLOAT | % failed |
| top_failed_rules | STRING | Most common failures |
| null_rate_critical_fields | FLOAT | % nulls in critical fields |

### 8.5 BI Health Page Requirements

Dashboard must display:

- Last successful refresh timestamp
- Freshness in hours (with alert if > 24h)
- Row counts per layer (Bronze -> Silver -> Gold)
- Quarantine % with drill-down to top failure reasons
- Pipeline run history (last 7 days)

---

## 9) Analytics Data Model Summary

> Detailed design in [`06-data-model.md`](./06-data-model.md)
> Gold facts and dimensions are implemented as dbt models on top of Silver curated tables.

### 9.1 Grain Decisions (Locked)

| Fact Table          | Grain                         | Rationale                                |
| ------------------- | ----------------------------- | ---------------------------------------- |
| `fact_transactions` | 1 row per transaction         | Atomic level for detailed fraud analysis |
| `fact_user_daily_volume` | 1 row per user per day per currency | User activity and retention trends |
| `fact_merchant_daily_volume` | 1 row per merchant per day per currency | Merchant performance and reconciliation |
| `fact_fraud_alerts` | 1 row per flagged transaction | Filtered fact for risk team              |

### 9.2 Conceptual Facts & Dimensions

**Fact Tables:**

- `fact_transactions` - Core transaction metrics (amount, fee, status, fraud flags)
- `fact_user_daily_volume` - Aggregated daily TPV and transaction count per user
- `fact_merchant_daily_volume` - Aggregated daily TPV and transaction count per merchant
- `fact_fraud_alerts` - Subset of flagged transactions with pattern details

**Dimension Tables:**

- `dim_user` - User demographics, KYC status, tier, country
- `dim_merchant` - Merchant details, category, risk score
- `dim_account` - Account type, currency, limits
- `dim_device` - Device type, model, trust status
- `dim_payment_method` - Card/bank details, provider
- `dim_date` - Calendar dimension (date, week, month, quarter, year, weekday)
- `dim_geography` - Country, city (derived from user/merchant)

### 9.3 Slowly Changing Dimensions

| Dimension      | SCD Type | Rationale                                   |
| -------------- | -------- | ------------------------------------------- |
| `dim_user`     | Type 2   | Track KYC status changes over time          |
| `dim_merchant` | Type 2   | Track risk score changes                    |
| `dim_device`   | Type 1   | Device trust status overwrites (no history) |
| `dim_account`  | Type 1   | Balance/limit updates overwrite             |

---

## 10) Assumptions, Open Questions, Risks

### 10.1 Assumptions

- `transaction_timestamp` is event time for KPI and fact derivation.
- `completed_timestamp` may arrive late and can be corrected in Silver.
- Bronze stores source timestamps as generated; Silver standardizes to UTC.
- Daily baseline reporting uses UTC day unless a stakeholder requires local-country day.
- `sender_account_id` is the authoritative transaction owner for velocity and account-level risk logic.

### 10.2 Open Questions

- Should Finance default reporting day be UTC or local day per country?
- For high-value fraud thresholds, should rules remain currency-specific only or also enforce USD-equivalent checks in Gold?
- Should velocity and new-device logic be evaluated per `sender_account_id`, per `user_id`, or both?
- Should cross-border detection compare only against `users.preferred_currency`, or also against sender account currency and/or a country->currency mapping?

### 10.3 Risks

- Cross-border logic may create false positives for legitimate multi-currency behavior.
- Country-to-timezone mapping gaps can weaken local-time fraud detection quality.
- Rapid volume growth can threaten daily SLA if compute scaling policies are not tuned.
- Delayed upstream source arrivals can impact freshness and quarantine metrics.

---

## 11) Out of Scope & Future Considerations

The following items are acknowledged as important for production systems but are **not implemented** in this portfolio project:

- **PII Masking:** Defined as an NFR but not fully enforced in this portfolio implementation. Planned production approach uses masking/hashing in Silver and governed access in Gold.
- **Role-Based Access Control (RBAC):** Designed as an NFR, but not fully enforced in this portfolio implementation. Planned model: Bronze/Silver restricted to Data Engineering; Gold views exposed by role (Risk -> fraud, Finance -> revenue).
- **Data Retention Policy:** Defined as an NFR, but not technically enforced in this portfolio implementation. Planned production policy applies configurable TTL/archive controls.

---

