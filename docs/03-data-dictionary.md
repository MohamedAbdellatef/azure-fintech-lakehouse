# Data Dictionary

| Version | Date       | Author             | Status |
| ------- | ---------- | ------------------ | ------ |
| 1.0     | 2026-03-03 | Mohamed Abdellatef | Final  |

> Column-level contract for every data asset across Bronze, Silver, and Gold layers.
> Note: Bronze types in this document describe source/business semantics. Physical Bronze Delta tables may still preserve raw CSV values as `STRING` for minimal-transformation landing, with strict type enforcement happening in Silver.

---

## 1) Scope & Cross-References

| Layer | What This File Documents | Detailed Design In |
|---|---|---|
| **Bronze** | Full column-level contract for all 7 raw source tables | Generator code (`data-generator/`) |
| **Silver** | Transformation guarantees (dedup, UTC, DQ) - not column-level | `docs/05-data-quality.md` |
| **Gold** | Full column-level contract for 4 facts + 7 dimensions | `docs/06-data-model.md` |

---

## 2) Source Table Summary (Bronze)

| Table | Primary Key / ID | Row Count | Columns | Intentional Noise | BRD Usage |
|---|---|---:|---:|---|---|
| `users` | `user_id` | 50,000 | 16 | email NULL ~5%, phone NULL ~3% | Q3, Q9-Q12, KPI-08, KPI-09 |
| `merchants` | `merchant_id` | 2,000 | 14 | None | Q1, Q8, KPI-01, KPI-02 |
| `accounts` | `account_id` | 62,416 | 10 | None | Q5, Q8 (newly funded wallets) |
| `devices` | `device_id` | 82,630 | 11 | None | Q5, Q13-Q15, KPI-06 |
| `payment_methods` | `payment_method_id` | 85,185 | 12 | last_four_digits NULL ~15%, expiry NULL ~40% | Q2, KPI-04, KPI-10 |
| `kyc_records` | `kyc_id` | 50,000 | 14 | document_number_hash NULL ~2%, many conditional NULLs | Q7, KPI-09 |
| `transactions` | `transaction_id` (not unique in Bronze) | 1,010,000 | 20 | Duplicate IDs ~1%, negative amounts ~2%, bad timestamps ~1% | All KPIs, Q1-Q15 |

---

## 3) Bronze Column Contracts

### 3.1 `users`

| Column | Type | Nullable | Description | Allowed Values / Notes |
|---|---|---|---|---|
| `user_id` | STRING (UUID) | No | Primary key | Unique UUID |
| `first_name` | STRING | No | First name | MENA demographic mix |
| `last_name` | STRING | No | Last name | MENA demographic mix |
| `email` | STRING | **Yes** | Email address | **NULL ~5%** (intentional noise for DQ) |
| `phone_number` | STRING | **Yes** | Phone number | **NULL ~3%**, mixed formats |
| `date_of_birth` | DATE | No | Date of birth | 18-65 years old at generation |
| `gender` | STRING | No | Gender | `M`, `F` |
| `country` | STRING | No | Country code | `EG`, `SA`, `AE`, `KW`, `QA` |
| `city` | STRING | No | City | Country-specific list (Cairo, Riyadh, Dubai, etc.) |
| `preferred_currency` | STRING | No | Preferred currency | `EGP`, `SAR`, `AED`, `KWD`, `QAR` |
| `kyc_status` | STRING | No | KYC verification state | `verified`, `pending`, `rejected` |
| `user_tier` | STRING | No | Loyalty tier | `basic`, `silver`, `gold`, `platinum` |
| `is_active` | BOOLEAN | No | Active flag | `True`, `False` |
| `registration_date` | TIMESTAMP | No | Registration timestamp | Historical date (stored as timestamp string) |
| `created_at` | TIMESTAMP | No | Record creation | Equals `registration_date` |
| `updated_at` | TIMESTAMP | No | Last update | SCD2 trigger: changes when `kyc_status`, `user_tier`, or `is_active` change |

**FK relationships:** None (root entity)
**Gold target:** `dim_user` (SCD Type 2 - tracks `kyc_status`, `user_tier`, `is_active`)
**Dropped in Gold:** `phone_number`, `date_of_birth`, `gender` (PII / no BRD use), `created_at`, `updated_at` (audit only)

---

### 3.2 `merchants`

| Column | Type | Nullable | Description | Allowed Values / Notes |
|---|---|---|---|---|
| `merchant_id` | STRING (UUID) | No | Primary key | Unique UUID |
| `merchant_name` | STRING | No | Display name | Arabic/MENA style names |
| `merchant_category` | STRING | No | Business category | `Retail`, `Food & Beverage`, `Utilities`, `Travel`, `E-commerce`, `Gaming`, `Healthcare`, `Education` |
| `business_type` | STRING | No | Entity type | `individual`, `company`, `enterprise` |
| `country` | STRING | No | Country code | `EG`, `SA`, `AE`, `KW`, `QA` |
| `city` | STRING | No | City | Country-specific list |
| `registration_date` | DATE | No | Registration date | Historical date |
| `is_verified` | BOOLEAN | No | Verification status | `True`, `False` |
| `is_active` | BOOLEAN | No | Active status | `True`, `False` |
| `risk_score` | DECIMAL(4,3) | No | Risk score | 0.000 to 1.000 |
| `monthly_limit` | INTEGER | No | Monthly transaction cap | Configured buckets |
| `fee_percentage` | DECIMAL(4,2) | No | Fee percentage | 1.50 to 3.50 |
| `created_at` | TIMESTAMP | No | Created timestamp | Historical |
| `updated_at` | TIMESTAMP | No | Last update | SCD2 trigger: changes when `risk_score`, `is_active`, or `is_verified` change |

**FK relationships:** None (root entity)
**Gold target:** `dim_merchant` (SCD Type 2 - tracks `risk_score`, `is_active`, `is_verified`)
**Dropped in Gold:** `created_at`, `updated_at` (audit only)

---

### 3.3 `accounts`

| Column | Type | Nullable | Description | Allowed Values / Notes |
|---|---|---|---|---|
| `account_id` | STRING (UUID) | No | Primary key | Unique UUID |
| `user_id` | STRING (UUID) | No | Owner user | FK -> `users.user_id` |
| `account_type` | STRING | No | Account type | `Wallet`, `Savings` |
| `currency` | STRING | No | Account currency | `EGP`, `SAR`, `AED`, `KWD`, `QAR` |
| `balance` | DECIMAL(15,2) | No | Current balance | Non-negative at generation |
| `daily_limit` | INTEGER | No | Daily transaction limit | Configured buckets |
| `monthly_limit` | INTEGER | No | Monthly transaction limit | Configured buckets |
| `status` | STRING | No | Account status | `active`, `frozen` |
| `created_at` | TIMESTAMP | No | Account creation time | Based on user's `registration_date` |
| `updated_at` | TIMESTAMP | No | Last update | Generation runtime |

**FK relationships:** `user_id` -> `users.user_id` (many-to-one)
**Cardinality:** ~1.2 accounts per user (some users have Wallet + Savings)
**Gold target:** `dim_account` (SCD Type 1)
**Dropped in Gold:** `updated_at` (audit only)

---

### 3.4 `devices`

| Column | Type | Nullable | Description | Allowed Values / Notes |
|---|---|---|---|---|
| `device_id` | STRING (UUID) | No | Primary key | Unique UUID |
| `user_id` | STRING (UUID) | No | Owner user | FK -> `users.user_id` |
| `device_type` | STRING | No | Device platform | `ios`, `android`, `web` |
| `device_model` | STRING | No | Model/browser label | Depends on `device_type` (e.g., iPhone 14, Samsung Galaxy S21, Chrome 120) |
| `os_version` | STRING | No | OS/browser version | Depends on `device_type` (e.g., iOS 17, Android 13) |
| `app_version` | STRING | No | App version | Semantic versioning (e.g., 3.0.2) |
| `device_fingerprint` | STRING | No | Fingerprint hash | 24-character hex hash |
| `is_trusted` | BOOLEAN | No | Trust signal | `True`, `False` |
| `first_seen_at` | TIMESTAMP | No | First seen | After user's `registration_date` |
| `last_seen_at` | TIMESTAMP | No | Last seen | >= `first_seen_at` |
| `created_at` | TIMESTAMP | No | Created timestamp | Equals `first_seen_at` |

**FK relationships:** `user_id` -> `users.user_id` (many-to-one)
**Cardinality:** ~1.7 devices per user
**Gold target:** `dim_device` (SCD Type 1)
**Dropped in Gold:** `created_at` (audit only)

---

### 3.5 `payment_methods`

| Column | Type | Nullable | Description | Allowed Values / Notes |
|---|---|---|---|---|
| `payment_method_id` | STRING (UUID) | No | Primary key | Unique UUID |
| `user_id` | STRING (UUID) | No | Owner user | FK -> `users.user_id` |
| `method_type` | STRING | No | Method type | `debit_card`, `credit_card`, `bank_account`, `wallet_balance` |
| `provider` | STRING | No | Provider/network | `visa`, `mastercard`, `amex`, `mada`, `meeza`, `knet`, `internal_wallet`, `Bank_<country>_<n>` |
| `last_four_digits` | STRING | **Yes** | Last 4 digits of card/account | NULL for `wallet_balance`; required 4 digits for `debit_card`, `credit_card`, and `bank_account` |
| `expiry_date` | DATE | **Yes** | Card expiration | **NULL ~40%** (NULL for `bank_account` and `wallet_balance`) |
| `is_default` | BOOLEAN | No | Default method flag | First method per user = True |
| `is_verified` | BOOLEAN | No | Verification status | `True`, `False` |
| `is_active` | BOOLEAN | No | Active status | `True`, `False` |
| `added_at` | TIMESTAMP | No | Method added timestamp | Historical |
| `created_at` | TIMESTAMP | No | Created timestamp | Equals `added_at` |
| `updated_at` | TIMESTAMP | No | Last update | Generation runtime |

**FK relationships:** `user_id` -> `users.user_id` (many-to-one)
**Cardinality:** ~1.7 methods per user
**Gold target:** `dim_payment_method` (SCD Type 1)
**Dropped in Gold:** `created_at`, `updated_at` (audit only)

---

### 3.6 `kyc_records`

| Column | Type | Nullable | Description | Allowed Values / Notes |
|---|---|---|---|---|
| `kyc_id` | STRING (UUID) | No | Primary key | Unique UUID |
| `user_id` | STRING (UUID) | No | User reference | FK -> `users.user_id` |
| `document_type` | STRING | No | Document type | Country-specific: `national_id`, `passport`, `iqama` (SA), `emirates_id` (AE), `civil_id` (KW), `qatar_id` (QA), `visa` (AE) |
| `document_number_hash` | STRING | **Yes** | SHA-256 hashed doc number | **NULL ~2%** (intentional noise) |
| `document_country` | STRING | No | Issuing country | Matches `users.country` |
| `verification_status` | STRING | No | Verification result | `verified`, `pending`, `rejected` (mirrors `users.kyc_status`) |
| `rejection_reason` | STRING | **Yes** | Rejection reason | **NULL ~95%** - only populated when `rejected`: `document_expired`, `document_unclear`, `face_mismatch`, `information_mismatch`, `suspected_fraud`, `incomplete_documents` |
| `verification_attempts` | INTEGER | No | Number of attempts | 1-4 (higher for rejected) |
| `submitted_at` | TIMESTAMP | No | Submission time | After user's `registration_date` |
| `verified_at` | TIMESTAMP | **Yes** | Completion time | **NULL ~15%** (NULL when `pending`) |
| `verified_by` | STRING | **Yes** | Verifier type | **NULL ~15%** (NULL when `pending`); otherwise `system_auto` (75%) or `manual_review` (25%) |
| `risk_flags` | STRING | **Yes** | Risk flag label | **NULL ~92%**; otherwise `high_risk_country`, `pep_match`, `sanctions_check` |
| `created_at` | TIMESTAMP | No | Created timestamp | Equals `submitted_at` |
| `updated_at` | TIMESTAMP | No | Last update | `verified_at` or `submitted_at` |

**FK relationships:** `user_id` -> `users.user_id` (one-to-one; 1 KYC record per user)
**Gold target:** Not promoted to Gold - KYC status is tracked via `dim_user.kyc_status`. Document-level detail stays in Bronze/Silver for audit.

---

### 3.7 `transactions`

| Column | Type | Nullable | Description | Allowed Values / Notes |
|---|---|---|---|---|
| `transaction_id` | STRING (UUID) | No | Business transaction identifier | **Duplicate IDs ~1%** (10,000 dups - intentional noise for Silver dedup; uniqueness enforced in Silver) |
| `sender_account_id` | STRING (UUID) | No | Sender account | FK -> `accounts.account_id` |
| `receiver_id` | STRING (UUID) | **Yes** | Receiver account or merchant | **NULL when `receiver_type = 'self'` for `Deposit`, `Withdrawal`, and `Bill_Payment`** |
| `receiver_type` | STRING | No | Receiver entity type | `self` (40%), `merchant` (35%), `account` (25%) |
| `transaction_type` | STRING | No | Transaction type | `P2P_Transfer`, `Merchant_Payment`, `Deposit`, `Withdrawal`, `Bill_Payment` |
| `payment_method_id` | STRING (UUID) | No | Payment method used | FK -> `payment_methods.payment_method_id` |
| `amount` | DECIMAL(15,2) | No | Principal amount | **Negative values ~2%** (20,115 rows - intentional noise for DQ quarantine) |
| `currency` | STRING | No | Transaction currency | Normally from sender account: `EGP`, `SAR`, `AED`, `KWD`, `QAR`; may be intentionally mismatched for `cross_border` fraud injection |
| `fee_amount` | DECIMAL(15,2) | No | Fee charged | Non-negative |
| `status` | STRING | No | Transaction outcome | `Success` (85%), `Failed` (8%), `Pending` (5%), `Reversed` (2%) |
| `device_id` | STRING (UUID) | No | Device used | FK -> `devices.device_id` |
| `ip_address` | STRING | No | Client IP address | IPv4 format |
| `latitude` | DECIMAL(10,6) | No | Transaction latitude | MENA bounds (22.0-32.0) |
| `longitude` | DECIMAL(10,6) | No | Transaction longitude | MENA bounds (29.0-56.0) |
| `transaction_timestamp` | TIMESTAMP | No | Initiated timestamp | Last ~1 year of historical data |
| `completed_timestamp` | TIMESTAMP | No | Completed timestamp | **Invalid ordering ~1%** (11,044 rows where completed < initiated - intentional noise) |
| `risk_score` | DECIMAL(4,3) | No | Risk score | 0.000 to 1.000 |
| `is_flagged` | BOOLEAN | No | Fraud flag | ~3% flagged |
| `fraud_pattern` | STRING | **Yes** | Detected fraud pattern | **NULL ~97%** - only populated when `is_flagged = True`: `velocity`, `amount`, `time`, `new_device`, `cross_border` |
| `created_at` | TIMESTAMP | No | Record creation | Equals `transaction_timestamp` |

**FK relationships:**
- `sender_account_id` -> `accounts.account_id` (many-to-one)
- `receiver_id` -> `accounts.account_id` (when `receiver_type = 'account'`) OR `merchants.merchant_id` (when `receiver_type = 'merchant'`)
- `payment_method_id` -> `payment_methods.payment_method_id` (many-to-one)
- `device_id` -> `devices.device_id` (many-to-one)

**Gold target:** `fact_transactions` (1:1 after dedup), `fact_fraud_alerts` (filtered where `is_flagged = True`), `fact_user_daily_volume` (aggregated), `fact_merchant_daily_volume` (aggregated where `receiver_type = 'merchant'`)
**Dropped in Gold:** `created_at` (audit only)

---

## 4) Intentional Data Noise (for DQ Testing)

> The generator injects realistic data quality issues so Bronze -> Silver cleansing has real work to do.

| Noise Type | Table | Column(s) | Rate | Silver Action |
|---|---|---|---|---|
| Duplicate transaction IDs | `transactions` | `transaction_id` | ~1% (10,000 rows) | Dedup - keep row with earliest `transaction_timestamp` |
| Negative amounts | `transactions` | `amount` | ~2% (20,115 rows) | Quarantine to `dq_quarantine` |
| Invalid timestamp order | `transactions` | `completed < transaction` | ~1% (11,044 rows) | Set `completed_timestamp` to NULL (row is otherwise valid) |
| NULL emails | `users` | `email` | ~5% (2,535 rows) | Pass through (nullable field) |
| NULL phone numbers | `users` | `phone_number` | ~3% (1,533 rows) | Pass through (nullable field) |
| NULL doc hash | `kyc_records` | `document_number_hash` | ~2% (1,039 rows) | Pass through (nullable field) |

---

## 5) Silver Layer Guarantees

> Silver keeps the same business meaning as Bronze, but normalized timestamp outputs may be stored in canonical UTC columns (for example, `transaction_timestamp_utc`, `completed_timestamp_utc`). Silver also adds technical columns such as `_dq_valid` and `_dq_issues` and enforces quality by quarantine.

| Guarantee | Details |
|---|---|
| **Deduplication** | `transaction_id` is unique after dedup (1,010,000 -> ~1,000,000 rows); keep row with earliest `transaction_timestamp` |
| **UTC standardization** | All timestamps normalized to UTC (see BRD Section 5.4); canonical Silver timestamp columns use `*_utc` naming where applicable |
| **Negative amount removal** | `amount < 0` rows quarantined to `dq_quarantine` |
| **Negative fee removal** | `fee_amount < 0` rows quarantined to `dq_quarantine` |
| **Invalid timestamp handling** | Where `completed_timestamp < transaction_timestamp`, set `completed_timestamp_utc = NULL` after UTC normalization (row is otherwise valid) |
| **Orphan FK check** | Critical transaction FKs such as `sender_account_id`, `device_id`, and `payment_method_id` must exist in parent tables; orphans are quarantined |
| **Type casting** | All columns cast to correct Databricks types (STRING, DECIMAL, TIMESTAMP, BOOLEAN, etc.) |
| **DQ flags** | Each Silver table adds `_dq_valid` (BOOLEAN) and `_dq_issues` (STRING) columns |

---

## 6) Gold Layer Contracts

> Full column-level design is in `docs/06-data-model.md`. Below is a summary of each Gold table's contract.

### 6.1 Fact Tables

| Table | PK | Grain | Source | Est. Rows |
|---|---|---|---|---|
| `fact_transactions` | `transaction_id` (natural) | 1 row per deduplicated transaction attempt | `silver_transactions` (1:1) | ~1,000,000 |
| `fact_user_daily_volume` | `user_daily_sk` (composite hash) | 1 row per user/day/currency | `silver_transactions` aggregated | ~970,000 |
| `fact_merchant_daily_volume` | `merchant_daily_sk` (composite hash) | 1 row per merchant/day/currency | `silver_transactions` WHERE `receiver_type = 'merchant'` | ~350,000 |
| `fact_fraud_alerts` | `transaction_id` (natural) | 1 row per flagged transaction | `silver_transactions` WHERE `is_flagged = True` | ~30,000 |

### 6.2 Dimension Tables

| Table | PK | SCD Type | Source | Tracked Changes |
|---|---|---|---|---|
| `dim_user` | `user_sk` = `MD5(concat(user_id, valid_from))` | Type 2 | `silver_users` | `kyc_status`, `user_tier`, `is_active` |
| `dim_merchant` | `merchant_sk` = `MD5(concat(merchant_id, valid_from))` | Type 2 | `silver_merchants` | `risk_score`, `is_active`, `is_verified` |
| `dim_account` | `account_sk` = `MD5(account_id)` | Type 1 | `silver_accounts` | Overwrites (no history) |
| `dim_device` | `device_sk` = `MD5(device_id)` | Type 1 | `silver_devices` | Overwrites (no history) |
| `dim_payment_method` | `payment_method_sk` = `MD5(payment_method_id)` | Type 1 | `silver_payment_methods` | Overwrites (no history) |
| `dim_date` | `date_sk` = `MD5(full_date)` | Static | dbt seed | N/A (seeded once) |
| `dim_geography` | `geography_sk` = `MD5(concat(country, city))` | Static | dbt seed | N/A (seeded once) |

### 6.3 Monitoring Tables

| Table | Purpose | BRD Support |
|---|---|---|
| `gold_refresh_audit` | Pipeline run tracking (model, batch_date, status, rows, duration) | KPI-11 (Freshness) |
| `dq_quarantine` | Failed records with rule ID + reason | KPI-12, Q17, Q18 |
| `dq_metrics` | Aggregated DQ stats per entity per batch | KPI-12, KPI-13 |

---

## 7) FK Relationship Map

```text
users (50K)
  |- accounts (62K)         user_id -> users.user_id      [1:N]
  |- devices (83K)          user_id -> users.user_id      [1:N]
  |- payment_methods (85K)  user_id -> users.user_id      [1:N]
  `- kyc_records (50K)      user_id -> users.user_id      [1:1]

transactions (1M)
  |- sender_account_id -> accounts.account_id                [N:1]
  |- receiver_id -> accounts.account_id (when account)       [N:1]
  |- receiver_id -> merchants.merchant_id (when merchant)    [N:1]
  |- payment_method_id -> payment_methods.payment_method_id  [N:1]
  `- device_id -> devices.device_id                          [N:1]

merchants (2K) - standalone entity, referenced by transactions
```

---

## 8) Naming Conventions

| Pattern | Meaning | Examples |
|---|---|---|
| `*_id` | Natural/business identifier (UUID) | `user_id`, `transaction_id` |
| `*_sk` | Surrogate key (MD5 hash) - Gold only | `user_sk`, `date_sk` |
| `*_at` | Timestamp column | `created_at`, `first_seen_at` |
| `*_date` | Date-only column | `registration_date`, `transaction_date` |
| `is_*` | Boolean flag | `is_active`, `is_flagged`, `is_current` |
| `*_score` | Bounded numeric score (0.0-1.0) | `risk_score` |
| `*_count` | Integer count (Gold aggregated facts) | `txn_count`, `success_count` |
| `*_amount` | Monetary value in original currency | `amount`, `total_amount` |

---

## 9) Notes

1. **Bronze** stores raw generator output as-is - timestamps are naive (no timezone), some business IDs (notably `transactions.transaction_id`) may contain duplicates, and amounts may be negative.
2. **Silver** normalizes all timestamps to UTC, persists canonical UTC timestamp columns where defined, deduplicates, quarantines invalid records and applies safe corrections where defined (e.g., invalid completed timestamp), and casts types.
3. **Gold** adds surrogate keys, resolves SCD2 dimensions via point-in-time (as-of) joins, computes aggregations, and drops PII/audit columns.
4. `kyc_records` flows through Bronze and Silver but is **not promoted to Gold** - KYC status is tracked via `dim_user.kyc_status` (SCD2).
5. All monetary values remain in original transaction currency throughout all layers (no conversion).
