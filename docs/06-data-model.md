# Data Model (Star Schema)

| Version | Date       | Author             | Status |
| ------- | ---------- | ------------------ | ------ |
| 1.0     | 2026-03-01 | Mohamed Abdellatef | Final  |

> **Layer:** Gold (built on Silver curated tables via dbt)
> **Schema type:** Dimensional star schema optimized for BI query performance
> **Implementation:** dbt models on Databricks / Delta Lake

---

## 1) Design Principles

| Principle | Decision |
|---|---|
| **Schema** | Star schema — facts surrounded by denormalized dimensions |
| **Surrogate keys** | Hash-based: SCD1/static dimensions use `MD5(natural_key)`; SCD2 dimensions use `MD5(concat(natural_key, valid_from))` |
| **Natural keys** | Preserved on every dimension for traceability (e.g., `user_id` alongside `user_sk`) |
| **SCD strategy** | Type 2 for dimensions with business-critical history; Type 1 for all others. Facts resolve SCD2 dimensions with point-in-time (as-of) joins using the fact timestamp or grain date (see Section 6) |
| **Currency policy** | All monetary values in original transaction currency (no conversion in Gold); optional `amount_usd` for cross-country comparison |
| **Timestamp policy** | All timestamps are Silver UTC-standardized (see BRD Section 5.4) |
| **Reporting day** | `transaction_timestamp` truncated to DATE in UTC |
| **Naming convention** | `fact_` prefix for facts, `dim_` prefix for dimensions, `_sk` suffix for surrogate keys |

---

## 2) Grain Decisions (Locked - per BRD 9.1)

| Fact Table | Grain | Rationale | Source |
|---|---|---|---|
| `fact_transactions` | 1 row per transaction attempt | Atomic level for detailed fraud analysis and financial KPIs | `silver_transactions` |
| `fact_user_daily_volume` | 1 row per user per day per currency | User activity trends, DAU/MAU, retention analysis | `silver_transactions` aggregated |
| `fact_merchant_daily_volume` | 1 row per merchant per day per currency | Merchant performance, reconciliation, AML monitoring | `silver_transactions` aggregated |
| `fact_fraud_alerts` | 1 row per flagged transaction | Filtered fact for Risk team dashboards | `silver_transactions` WHERE `is_flagged = True` |

---

## 3) Fact Tables

### 3.1 `fact_transactions`

> **Grain:** 1 row per deduplicated transaction attempt
> **Source:** `silver_transactions` (1:1 mapping after dedup)
> **BRD support:** KPI-01 (TPV), KPI-02 (Revenue), KPI-03 (ATV), KPI-04 (Success Rate), KPI-05 (Fraud Rate), KPI-06 (Untrusted Device Rate), KPI-07 (High-Risk Amount), KPI-10 (Payment Method Adoption), Q10 (first transaction within 7 days)

| Column | Type | Description | Source / Logic |
|---|---|---|---|
| `transaction_id` | STRING | Primary key (natural business key) | `silver_transactions.transaction_id` - UUID, unique after Silver dedup |
| `date_sk` | STRING | FK -> `dim_date` | `MD5(full_date)`, where `full_date = transaction_date` |
| `user_sk` | STRING | FK -> `dim_user` | Store `dim_user.user_sk` resolved by an as-of join on `user_id` where `transaction_timestamp_utc >= valid_from` and `< COALESCE(valid_to, '9999-12-31')` |
| `account_sk` | STRING | FK -> `dim_account` | `MD5(sender_account_id)` |
| `merchant_sk` | STRING | FK -> `dim_merchant` | Store `dim_merchant.merchant_sk` when `receiver_type = 'merchant'`; resolve by as-of join on `merchant_id = receiver_id` using `transaction_timestamp_utc`; else NULL |
| `device_sk` | STRING | FK -> `dim_device` | `MD5(device_id)` |
| `payment_method_sk` | STRING | FK -> `dim_payment_method` | `MD5(payment_method_id)` |
| `geography_sk` | STRING | FK -> `dim_geography` | `MD5(concat(user_country, user_city))` - sender user location |
| `transaction_type` | STRING | Transaction type | `P2P_Transfer`, `Merchant_Payment`, `Deposit`, `Withdrawal`, `Bill_Payment` |
| `receiver_type` | STRING | Receiver entity type | `account`, `merchant`, `self` |
| `status` | STRING | Transaction status | `Success`, `Failed`, `Pending`, `Reversed` |
| `amount` | DECIMAL(15,2) | Principal amount (original currency) | `silver_transactions.amount` |
| `fee_amount` | DECIMAL(15,2) | Fee charged (original currency) | `silver_transactions.fee_amount` |
| `total_charged` | DECIMAL(15,2) | Total = amount + fee | Calculated: `amount + fee_amount` |
| `currency` | STRING | Transaction currency | `EGP`, `SAR`, `AED`, `KWD`, `QAR` |
| `is_flagged` | BOOLEAN | Fraud flag | `silver_transactions.is_flagged` |
| `fraud_pattern` | STRING | Fraud pattern label | `velocity`, `amount`, `time`, `new_device`, `cross_border`, or NULL |
| `risk_score` | DECIMAL(4,3) | Risk score | 0.000 to 1.000 |
| `is_trusted_device` | BOOLEAN | Current device trust status | `dim_device.is_trusted` via device join (SCD1; no historical trust-state tracking) |
| `transaction_timestamp_utc` | TIMESTAMP | Event timestamp (UTC) | `silver_transactions.transaction_timestamp_utc` |
| `completed_timestamp_utc` | TIMESTAMP | Completion timestamp (UTC) | `silver_transactions.completed_timestamp_utc` |
| `transaction_date` | DATE | Reporting date (UTC) | `CAST(transaction_timestamp_utc AS DATE)` |
| `transaction_hour` | INTEGER | Hour of day (UTC, 0-23) | `HOUR(transaction_timestamp_utc)` |
| `ip_address` | STRING | Client IP | `silver_transactions.ip_address` |
| `latitude` | DECIMAL(10,6) | Latitude | `silver_transactions.latitude` |
| `longitude` | DECIMAL(10,6) | Longitude | `silver_transactions.longitude` |

**Measures:** `amount`, `fee_amount`, `total_charged`, `risk_score`
**Degenerate dimensions:** `transaction_type`, `receiver_type`, `status`, `currency`, `fraud_pattern`

---

### 3.2 `fact_user_daily_volume`

> **Grain:** 1 row per user per day per currency
> **Source:** `silver_transactions` aggregated by `user_id` + `transaction_date` + `currency`
> **BRD support:** KPI-08 (DAU/MAU), Q9, Q11 (retention), Q12 (tier frequency + volume)

| Column | Type | Description | Source / Logic |
|---|---|---|---|
| `user_daily_sk` | STRING | Surrogate key | `MD5(concat(user_id, transaction_date, currency))` |
| `user_sk` | STRING | FK -> `dim_user` | Store `dim_user.user_sk` resolved by an end-of-day as-of join on `user_id` using `transaction_date 23:59:59 UTC` |
| `date_sk` | STRING | FK -> `dim_date` | `MD5(full_date)`, where `full_date = transaction_date` |
| `geography_sk` | STRING | FK -> `dim_geography` | `MD5(concat(user_country, user_city))` |
| `transaction_date` | DATE | Activity date | `CAST(transaction_timestamp_utc AS DATE)` |
| `txn_count` | INTEGER | Total transactions (all statuses) | `COUNT(*)` |
| `success_count` | INTEGER | Successful transactions | `COUNT(*) WHERE status = 'Success'` |
| `failed_count` | INTEGER | Failed transactions | `COUNT(*) WHERE status = 'Failed'` |
| `total_amount` | DECIMAL(15,2) | Sum of successful amounts | `SUM(amount) WHERE status = 'Success'` |
| `total_fees` | DECIMAL(15,2) | Sum of successful fees | `SUM(fee_amount) WHERE status = 'Success'` |
| `avg_amount` | DECIMAL(15,2) | Average successful transaction value | `total_amount / NULLIF(success_count, 0)` |
| `flagged_count` | INTEGER | Flagged transactions | `COUNT(*) WHERE is_flagged = True` |
| `currency` | STRING | Transaction currency | Grouped by currency |

---

### 3.3 `fact_merchant_daily_volume`

> **Grain:** 1 row per merchant per day per currency
> **Source:** `silver_transactions` WHERE `receiver_type = 'merchant'`, aggregated by `receiver_id` + `transaction_date` + `currency`
> **BRD support:** Q1 (TPV by merchant_category), Q8 (high-volume merchants), KPI-01, KPI-02

| Column | Type | Description | Source / Logic |
|---|---|---|---|
| `merchant_daily_sk` | STRING | Surrogate key | `MD5(concat(receiver_id, transaction_date, currency))` - `receiver_id = merchant_id` |
| `merchant_sk` | STRING | FK -> `dim_merchant` | Store `dim_merchant.merchant_sk` resolved by an end-of-day as-of join on `merchant_id = receiver_id` using `transaction_date 23:59:59 UTC` |
| `date_sk` | STRING | FK -> `dim_date` | `MD5(full_date)`, where `full_date = transaction_date` |
| `geography_sk` | STRING | FK -> `dim_geography` | `MD5(concat(merchant_country, merchant_city))` |
| `transaction_date` | DATE | Activity date | `CAST(transaction_timestamp_utc AS DATE)` |
| `txn_count` | INTEGER | Total merchant payment transactions | `COUNT(*)` |
| `success_count` | INTEGER | Successful merchant payments | `COUNT(*) WHERE status = 'Success'` |
| `total_amount` | DECIMAL(15,2) | Sum of successful amounts | `SUM(amount) WHERE status = 'Success'` |
| `total_fees` | DECIMAL(15,2) | Sum of successful fees | `SUM(fee_amount) WHERE status = 'Success'` |
| `distinct_senders` | INTEGER | Unique sender accounts | `COUNT(DISTINCT sender_account_id)` |
| `newly_funded_txn_count` | INTEGER | Transactions from newly funded wallets | `COUNT(*) WHERE sender had Deposit within 24h` |
| `currency` | STRING | Transaction currency | Grouped by currency |

---

### 3.4 `fact_fraud_alerts`

> **Grain:** 1 row per flagged transaction
> **Source:** `silver_transactions` WHERE `is_flagged = True`
> **BRD support:** KPI-05 (Fraud Rate), KPI-07 (High-Risk Amount), Q5 (new device), Q6 (location jumping), Q7 (KYC correlation)

| Column | Type | Description | Source / Logic |
|---|---|---|---|
| `transaction_id` | STRING | Primary key + FK -> `fact_transactions` | `silver_transactions.transaction_id` |
| `user_sk` | STRING | FK -> `dim_user` | Store `dim_user.user_sk` resolved by an as-of join on `user_id` using `transaction_timestamp_utc` |
| `account_sk` | STRING | FK -> `dim_account` | `MD5(sender_account_id)` |
| `device_sk` | STRING | FK -> `dim_device` | `MD5(device_id)` |
| `merchant_sk` | STRING | FK -> `dim_merchant` | Store `dim_merchant.merchant_sk` when merchant; resolve by as-of join on `merchant_id = receiver_id` using `transaction_timestamp_utc`; else NULL |
| `date_sk` | STRING | FK -> `dim_date` | `MD5(full_date)`, where `full_date = transaction_date` |
| `geography_sk` | STRING | FK -> `dim_geography` | `MD5(concat(user_country, user_city))` |
| `fraud_pattern` | STRING | Detected pattern | `velocity`, `amount`, `time`, `new_device`, `cross_border` |
| `amount` | DECIMAL(15,2) | Transaction amount | `silver_transactions.amount` |
| `currency` | STRING | Transaction currency | `silver_transactions.currency` |
| `risk_score` | DECIMAL(4,3) | Risk score | `silver_transactions.risk_score` |
| `is_trusted_device` | BOOLEAN | Current device trust status | `dim_device.is_trusted` (SCD1; no historical trust-state tracking) |
| `user_kyc_status` | STRING | User KYC at time of transaction | Denormalized from the as-of-resolved `dim_user` row referenced by `user_sk` |
| `user_tier` | STRING | User tier at time of transaction | Denormalized from the as-of-resolved `dim_user` row referenced by `user_sk` |
| `transaction_timestamp_utc` | TIMESTAMP | Event timestamp | `silver_transactions.transaction_timestamp_utc` |
| `transaction_date` | DATE | Reporting date | `CAST(transaction_timestamp_utc AS DATE)` |
| `latitude` | DECIMAL(10,6) | Transaction latitude | For location jumping analysis |
| `longitude` | DECIMAL(10,6) | Transaction longitude | For location jumping analysis |

---

## 4) Dimension Tables

### 4.1 `dim_user` (SCD Type 2)

> **Natural key:** `user_id`
> **Tracked changes:** `kyc_status`, `user_tier`, `is_active` - a new row is created when any of these change
> **BRD support:** Q3 (tier distribution), Q9-Q12 (user behavior & retention), KPI-08 (DAU/MAU), KPI-09 (KYC rate)

| Column | Type | Description |
|---|---|---|
| `user_sk` | STRING | Surrogate key: `MD5(concat(user_id, valid_from))` |
| `user_id` | STRING | Natural key (UUID) |
| `first_name` | STRING | First name |
| `last_name` | STRING | Last name |
| `email` | STRING | Email address (nullable) |
| `country` | STRING | Country code: `EG`, `SA`, `AE`, `KW`, `QA` |
| `city` | STRING | City |
| `preferred_currency` | STRING | Preferred currency |
| `kyc_status` | STRING | KYC state: `verified`, `pending`, `rejected` |
| `user_tier` | STRING | Tier: `basic`, `silver`, `gold`, `platinum` |
| `is_active` | BOOLEAN | Active flag |
| `registration_ts_utc` | TIMESTAMP | User registration timestamp (UTC) |
| `registration_date` | DATE | Derived reporting date: `CAST(registration_ts_utc AS DATE)` |
| `valid_from` | TIMESTAMP | SCD2: row validity start |
| `valid_to` | TIMESTAMP | SCD2: row validity end (NULL = current) |
| `is_current` | BOOLEAN | SCD2: True if active row |

---

### 4.2 `dim_merchant` (SCD Type 2)

> **Natural key:** `merchant_id`
> **Tracked changes:** `risk_score`, `is_active`, `is_verified` - a new row is created when any of these change
> **BRD support:** Q1 (TPV by merchant_category), Q8 (high-volume merchants)

| Column | Type | Description |
|---|---|---|
| `merchant_sk` | STRING | Surrogate key: `MD5(concat(merchant_id, valid_from))` |
| `merchant_id` | STRING | Natural key (UUID) |
| `merchant_name` | STRING | Display name |
| `merchant_category` | STRING | Category: `Retail`, `Food & Beverage`, `Utilities`, `Travel`, `E-commerce`, `Gaming`, `Healthcare`, `Education` |
| `business_type` | STRING | Entity type: `individual`, `company`, `enterprise` |
| `country` | STRING | Country code |
| `city` | STRING | City |
| `risk_score` | DECIMAL(4,3) | Risk score (0.000-1.000) |
| `fee_percentage` | DECIMAL(4,2) | Fee % (1.50-3.50) |
| `monthly_limit` | INTEGER | Monthly cap |
| `is_verified` | BOOLEAN | Verification status |
| `is_active` | BOOLEAN | Active status |
| `registration_date` | DATE | Registration date |
| `valid_from` | TIMESTAMP | SCD2: row validity start |
| `valid_to` | TIMESTAMP | SCD2: row validity end (NULL = current) |
| `is_current` | BOOLEAN | SCD2: True if active row |

---

### 4.3 `dim_account` (SCD Type 1)

> **Natural key:** `account_id`
> **SCD1:** Balance and limit changes overwrite - no history needed
> **BRD support:** Links transactions to users (2-hop: txn -> account -> user)

| Column | Type | Description |
|---|---|---|
| `account_sk` | STRING | Surrogate key: `MD5(account_id)` |
| `account_id` | STRING | Natural key (UUID) |
| `user_id` | STRING | Owner user_id |
| `account_type` | STRING | `Wallet`, `Savings` |
| `currency` | STRING | Account currency |
| `balance` | DECIMAL(15,2) | Current balance |
| `daily_limit` | INTEGER | Daily limit |
| `monthly_limit` | INTEGER | Monthly limit |
| `status` | STRING | `active`, `frozen` |
| `created_at` | TIMESTAMP | Account creation timestamp |

---

### 4.4 `dim_device` (SCD Type 1)

> **Natural key:** `device_id`
> **SCD1:** Trust status overwrites - no history
> **BRD support:** Q13 (device distribution), Q14 (fraud by device), Q15 (success by app version), KPI-06 (untrusted device rate)

| Column | Type | Description |
|---|---|---|
| `device_sk` | STRING | Surrogate key: `MD5(device_id)` |
| `device_id` | STRING | Natural key (UUID) |
| `user_id` | STRING | Owner user_id |
| `device_type` | STRING | `ios`, `android`, `web` |
| `device_model` | STRING | Model/browser label |
| `os_version` | STRING | OS/browser version |
| `app_version` | STRING | App version |
| `device_fingerprint` | STRING | Fingerprint hash |
| `is_trusted` | BOOLEAN | Trust signal |
| `first_seen_at` | TIMESTAMP | First seen |
| `last_seen_at` | TIMESTAMP | Last seen |

---

### 4.5 `dim_payment_method` (SCD Type 1)

> **Natural key:** `payment_method_id`
> **SCD1:** Verification and active status overwrite
> **BRD support:** Q2 (success/adoption by method), KPI-04 (success rate by method), KPI-10 (adoption)

| Column | Type | Description |
|---|---|---|
| `payment_method_sk` | STRING | Surrogate key: `MD5(payment_method_id)` |
| `payment_method_id` | STRING | Natural key (UUID) |
| `user_id` | STRING | Owner user_id |
| `method_type` | STRING | `debit_card`, `credit_card`, `bank_account`, `wallet_balance` |
| `provider` | STRING | `visa`, `mastercard`, `amex`, `mada`, `meeza`, `knet`, `internal_wallet`, etc. |
| `last_four_digits` | STRING | Last 4 digits (nullable) |
| `expiry_date` | DATE | Expiration (nullable) |
| `is_default` | BOOLEAN | Default method flag |
| `is_verified` | BOOLEAN | Verification status |
| `is_active` | BOOLEAN | Active status |
| `added_at` | TIMESTAMP | When method was added |

---

### 4.6 `dim_date`

> **Type:** Static calendar dimension (no SCD - seeded once)
> **Range:** Covers full data range + 1 year forward
> **BRD support:** All time-based KPIs and grains (day/week/month/quarter)

| Column | Type | Description |
|---|---|---|
| `date_sk` | STRING | Surrogate key: `MD5(full_date)` |
| `full_date` | DATE | Calendar date |
| `day_of_month` | INTEGER | Day (1-31) |
| `day_of_week` | INTEGER | Day of week (1=Mon, 7=Sun) |
| `day_name` | STRING | Monday, Tuesday, etc. |
| `is_weekend` | BOOLEAN | Saturday or Sunday |
| `week_of_year` | INTEGER | ISO week number |
| `month_num` | INTEGER | Month number (1-12) |
| `month_name` | STRING | January, February, etc. |
| `quarter` | INTEGER | Quarter (1-4) |
| `year` | INTEGER | Year |
| `year_month` | STRING | `YYYY-MM` format for grouping |

---

### 4.7 `dim_geography`

> **Type:** Static dimension (no SCD - seeded from reference data)
> **BRD support:** All KPIs with country/city grain, timezone derivation

| Column | Type | Description |
|---|---|---|
| `geography_sk` | STRING | Surrogate key: `MD5(concat(country, city))` |
| `country` | STRING | Country code: `EG`, `SA`, `AE`, `KW`, `QA` |
| `country_name` | STRING | Full country name |
| `city` | STRING | City name |
| `currency` | STRING | Local currency |
| `timezone` | STRING | IANA timezone (e.g., `Africa/Cairo`, `Asia/Riyadh`) |

---

## 5) Monitoring & Audit Tables

> These tables support KPI-11 (Freshness), KPI-12 (Quarantine Rate), KPI-13 (Completeness), and BRD questions Q16-Q18.

### 5.1 `gold_refresh_audit`

| Column | Type | Description |
|---|---|---|
| `run_id` | STRING | Unique pipeline run ID |
| `model_name` | STRING | dbt model name |
| `batch_date` | DATE | Processing date |
| `started_ts` | TIMESTAMP | Run start time |
| `finished_ts` | TIMESTAMP | Run end time |
| `status` | STRING | `success`, `failed` |
| `rows_affected` | INTEGER | Rows written |
| `execution_time_seconds` | FLOAT | Duration |

### 5.2 `dq_quarantine`

| Column | Type | Description |
|---|---|---|
| `entity_name` | STRING | Source table |
| `batch_date` | DATE | Processing date |
| `source_record_id` | STRING | Source business key |
| `dq_rule_id` | STRING | Failed rule ID (e.g., `TXN-006`) |
| `dq_reason` | STRING | Human-readable reason |
| `quarantined_at` | TIMESTAMP | Quarantine timestamp |

### 5.3 `dq_metrics`

| Column | Type | Description |
|---|---|---|
| `entity_name` | STRING | Table name |
| `batch_date` | DATE | Processing date |
| `total_rows` | INTEGER | Total processed |
| `quarantine_count` | INTEGER | Failed DQ count |
| `quarantine_rate` | FLOAT | % failed |
| `top_failed_rules` | STRING | Most common failures |
| `null_rate_critical_fields` | FLOAT | % nulls in critical fields |

---

## 6) Surrogate Key Strategy

| Decision | Choice | Rationale |
|---|---|---|
| **Method** | Hash by entity type | Deterministic - SCD1/static dimensions use `MD5(natural_key)`; SCD2 dimensions use `MD5(concat(natural_key, valid_from))` |
| **Fact PKs** | Natural key (`transaction_id`) | UUID is already unique - hashing adds no value. Aggregated facts use composite hash: `MD5(concat(key1, key2, ...))` |
| **SCD2 dim keys** | `MD5(concat(natural_key, valid_from))` | Unique per version of a slowly changing dimension row |
| **SCD2 fact FKs** | Store resolved dimension SK | Event-level facts use as-of joins on fact timestamp; daily aggregates use end-of-day UTC snapshot for the grain date |
| **SCD1 keys** | `MD5(natural_key)` | No version tracking - one SK per entity |
| **Collision risk** | Negligible | MD5 collision probability ~= 0 for < 1B rows |
| **Alternative** | `SHA-256` if security-sensitive | MD5 is sufficient for dimensional modeling |

---

## 7) Relationships Overview

- `fact_transactions` joins to `dim_date`, `dim_user`, `dim_account`, `dim_merchant`, `dim_device`, `dim_payment_method`, and `dim_geography`.
- `fact_user_daily_volume` joins to `dim_date`, `dim_user`, and `dim_geography`.
- `fact_merchant_daily_volume` joins to `dim_date`, `dim_merchant`, and `dim_geography`.
- `fact_fraud_alerts` reuses the same conformed dimensions as `fact_transactions`, including `dim_account`, for risk-focused analysis.

---

## 8) BRD-to-Model Traceability

| BRD Question / KPI | Primary Fact | Key Dimensions |
|---|---|---|
| Q1: TPV by currency + merchant_category | `fact_transactions`, `fact_merchant_daily_volume` | `dim_date`, `dim_merchant`, `dim_geography` |
| Q2: Payment method adoption + success | `fact_transactions` | `dim_payment_method`, `dim_geography` |
| Q3: P2P vs Merchant ratio by tier | `fact_transactions` | `dim_user` |
| Q4: ATV per country | `fact_transactions` | `dim_geography`, `dim_date` |
| Q5: High-value from new devices | `fact_fraud_alerts` | `dim_device`, `dim_user`, `dim_account` |
| Q6: Location jumping | `fact_fraud_alerts` | `dim_user`, `dim_date` |
| Q7: KYC vs failed/reversed | `fact_transactions` | `dim_user` (kyc_status) |
| Q8: Merchant high-volume AML | `fact_merchant_daily_volume` | `dim_merchant`, `dim_date` |
| Q9: DAU/MAU | `fact_user_daily_volume` | `dim_date`, `dim_user` |
| Q10: First transaction within 7 days | `fact_transactions` | `dim_user` (registration_ts_utc) |
| Q11: Retention at 30/60/90 days | `fact_user_daily_volume` | `dim_user`, `dim_geography` |
| Q12: Tier frequency + volume | `fact_user_daily_volume` | `dim_user` (user_tier) |
| Q13: Device type distribution | `fact_transactions` | `dim_device` |
| Q14: Fraud rate by device model | `fact_fraud_alerts` | `dim_device` |
| Q15: Success rate by app version | `fact_transactions` | `dim_device` |
| Q16: Gold freshness | `gold_refresh_audit` | - |
| Q17: Quarantine rate + reasons | `dq_metrics`, `dq_quarantine` | - |
| Q18: Orphan records | `dq_quarantine` | - |
| KPI-01: TPV | `fact_transactions` | `dim_date`, `dim_geography` |
| KPI-02: Revenue | `fact_transactions` | `dim_date`, `dim_merchant` |
| KPI-03: ATV | `fact_transactions` | `dim_date`, `dim_geography` |
| KPI-04: Success Rate | `fact_transactions` | `dim_date`, `dim_payment_method` |
| KPI-05: Fraud Rate | `fact_fraud_alerts` | `dim_date` |
| KPI-06: Untrusted Device Rate | `fact_transactions` | `dim_device` |
| KPI-07: High-Risk Amount | `fact_fraud_alerts` | `dim_date` |
| KPI-08: DAU/MAU | `fact_user_daily_volume` | `dim_date` |
| KPI-09: KYC Rate | `dim_user` | `dim_geography` |
| KPI-10: Payment Method Adoption | `fact_transactions` | `dim_payment_method`, `dim_geography` |
| KPI-11: Freshness | `gold_refresh_audit` | - |
| KPI-12: Quarantine Rate | `dq_metrics` | - |
| KPI-13: Completeness | `dq_metrics` | - |

---

## 9) dbt Implementation Notes

- **Materializations:** Facts as `incremental` (append/merge); SCD2 dimensions (`dim_user`, `dim_merchant`) as dbt `snapshot` (or equivalent incremental merge); SCD1/static dimensions as `table`
- **Seeds:** `fraud_rules` reference table loaded as dbt seed (CSV -> Delta)
- **Tests:** See `docs/05-data-quality.md` Section "Minimum dbt Test Set"
- **Tags:** `tag: "fact"`, `tag: "dim"`, `tag: "audit"` for selective runs
- **Incremental strategy:** `merge` on the primary key (`transaction_id` for atomic facts; composite surrogate key for aggregated facts) with `batch_date` filter for partition pruning

