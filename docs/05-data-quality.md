# Data Quality Framework

| Version | Date       | Author             | Status |
| ------- | ---------- | ------------------ | ------ |
| 1.0     | 2026-03-04 | Mohamed Abdellatef | Final  |

> DQ rules, quarantine logic, Silver cleansing actions, and dbt test specifications for Bronze, Silver, and Gold layers.

---

## 1) DQ Principles

| Dimension | Definition | How We Check |
|---|---|---|
| **Completeness** | Required fields are present | `NOT NULL` checks on mandatory columns |
| **Validity** | Values conform to domain rules | Accepted values, regex, range checks |
| **Consistency** | Cross-table and conditional logic holds | FK existence, conditional field checks |
| **Uniqueness** | Keys are not duplicated | PK uniqueness after Silver dedup |
| **Timeliness** | Data arrives within SLA | Freshness check: hours since last Gold refresh (KPI-11) |
| **Accuracy** | Values are within plausible ranges | Range bounds on scores, amounts, coordinates |

---

## 2) Layer Expectations

| Area | Bronze (Raw) | Silver (Cleansed) | Action |
|---|---|---|---|
| Duplicate PKs | ~1% (10,000 dups) | 0% - unique | Dedup: keep row with earliest `transaction_timestamp` |
| Negative amounts | ~2% (20,115 rows) | 0% - all positive | Quarantine to `dq_quarantine` |
| Invalid timestamp order | ~1% (11,044 rows) | Corrected | Set `completed_timestamp_utc = NULL` after UTC normalization (row otherwise valid) |
| NULL emails | ~5% (2,535 rows) | Pass through | Nullable field - no action needed |
| NULL phone numbers | ~3% (1,533 rows) | Pass through | Nullable field - no action needed |
| NULL doc hash | ~2% (1,039 rows) | Pass through | Nullable field - no action needed |
| Enum conformance | Raw generator values | Strict enforcement | Quarantine if value not in accepted set |
| Timestamps | Naive (no timezone) | UTC normalized | Cast + apply BRD Section 5.4 rules |
| Fraud labels | ~3% flagged | Preserved | Validated: `is_flagged = True` must have `fraud_pattern` |

---

## 3) DQ Rules by Entity

### 3.1 `transactions` (27 rules)

| Rule ID | Severity | Column(s) | Logic | Bronze | Silver | Silver Action |
|---|---|---|---|---|---|---|
| TXN-001 | Critical | `transaction_id` | NOT NULL | 100% | 100% | - |
| TXN-002 | Critical | `transaction_id` | Unique (after dedup) | ~99% | 100% | Dedup: keep earliest `transaction_timestamp` |
| TXN-003 | Critical | `sender_account_id` | FK exists in `accounts` | 100% | 100% | Quarantine orphans |
| TXN-004 | Critical | `status` | IN (`Success`, `Failed`, `Pending`, `Reversed`) | 100% | 100% | - |
| TXN-005 | Critical | `transaction_type` | IN (`P2P_Transfer`, `Merchant_Payment`, `Deposit`, `Withdrawal`, `Bill_Payment`) | 100% | 100% | - |
| TXN-006 | Critical | `currency` | IN (`EGP`, `SAR`, `AED`, `KWD`, `QAR`) | 100% | 100% | - |
| TXN-007 | Critical | `amount` | `> 0` | ~98% | 100% | Quarantine negatives to `dq_quarantine` |
| TXN-008 | Critical | `fee_amount` | `>= 0` | 100% | 100% | Quarantine negatives to `dq_quarantine` |
| TXN-009 | Warning | `completed_timestamp` | `>= transaction_timestamp` when not NULL | ~99% | 100% | Set `completed_timestamp_utc = NULL` if invalid |
| TXN-010 | Warning | `risk_score` | Between 0.000 and 1.000 | 100% | 100% | - |
| TXN-011 | Critical | `is_flagged`, `fraud_pattern` | If `is_flagged = True` then `fraud_pattern` NOT NULL | 100% | 100% | - |
| TXN-012 | Critical | `fraud_pattern` | When not NULL: IN (`velocity`, `amount`, `time`, `new_device`, `cross_border`) | 100% | 100% | - |
| TXN-013 | Critical | `receiver_type` | IN (`account`, `merchant`, `self`) | 100% | 100% | - |
| TXN-014 | Critical | `receiver_type`, `receiver_id` | `receiver_type = 'self'` => `receiver_id IS NULL` | 100% | 100% | - |
| TXN-015 | Critical | `receiver_type`, `receiver_id` | `receiver_type IN ('account','merchant')` => `receiver_id IS NOT NULL` | 100% | 100% | - |
| TXN-016 | Critical | `transaction_type`, `receiver_type` | `Merchant_Payment` => `receiver_type = 'merchant'` | 100% | 100% | - |
| TXN-017 | Critical | `transaction_type`, `receiver_type` | `P2P_Transfer` => `receiver_type = 'account'` | 100% | 100% | - |
| TXN-018 | Warning | `latitude` | Between 22.0 and 32.0 (MENA bounds) | 100% | 100% | - |
| TXN-019 | Warning | `longitude` | Between 29.0 and 56.0 (MENA bounds) | 100% | 100% | - |
| TXN-020 | Critical | `device_id` | FK exists in `devices` | 100% | 100% | Quarantine orphans |
| TXN-021 | Critical | `payment_method_id` | FK exists in `payment_methods` | 100% | 100% | Quarantine orphans |
| TXN-022 | Critical | `receiver_id` | If `receiver_type = 'account'`, `receiver_id` exists in `accounts` | 100% | 100% | Quarantine orphans |
| TXN-023 | Critical | `receiver_id` | If `receiver_type = 'merchant'`, `receiver_id` exists in `merchants` | 100% | 100% | Quarantine orphans |
| TXN-024 | Critical | `sender_account_id` | NOT NULL | 100% | 100% | - |
| TXN-025 | Critical | `device_id` | NOT NULL | 100% | 100% | - |
| TXN-026 | Critical | `payment_method_id` | NOT NULL | 100% | 100% | - |
| TXN-027 | Critical | `transaction_type`, `receiver_type`, `receiver_id` | `Deposit`, `Withdrawal`, `Bill_Payment` => `receiver_type = 'self'` and `receiver_id IS NULL` | 100% | 100% | - |

### 3.2 `users` (7 rules)

| Rule ID | Severity | Column(s) | Logic | Bronze | Silver |
|---|---|---|---|---|---|
| USR-001 | Critical | `user_id` | Unique + NOT NULL | 100% | 100% |
| USR-002 | Warning | `email` | Valid email regex when not NULL | >= 95% | 100% |
| USR-003 | Warning | `email` | NOT NULL | ~95% | >= 95% (pass through) |
| USR-004 | Warning | `phone_number` | NOT NULL | ~97% | >= 97% (pass through) |
| USR-005 | Critical | `country` | IN (`EG`, `SA`, `AE`, `KW`, `QA`) | 100% | 100% |
| USR-006 | Critical | `kyc_status` | IN (`verified`, `pending`, `rejected`) | 100% | 100% |
| USR-007 | Critical | `user_tier` | IN (`basic`, `silver`, `gold`, `platinum`) | 100% | 100% |

### 3.3 `accounts` (6 rules)

| Rule ID | Severity | Column(s) | Logic | Bronze | Silver |
|---|---|---|---|---|---|
| ACC-001 | Critical | `account_id` | Unique + NOT NULL | ~98.5% | 100% |
| ACC-002 | Critical | `user_id` | FK exists in `users` | ~99% | 100% |
| ACC-003 | Warning | `balance` | `>= 0` | ~98% | 100% |
| ACC-004 | Critical | `currency` | IN (`EGP`, `SAR`, `AED`, `KWD`, `QAR`) | ~99% | 100% |
| ACC-005 | Critical | `status` | IN (`active`, `frozen`) | ~99% | 100% |
| ACC-006 | Critical | `account_type` | IN (`Wallet`, `Savings`) | ~99.5% | 100% |

### 3.4 `merchants` (7 rules)

| Rule ID | Severity | Column(s) | Logic | Bronze | Silver |
|---|---|---|---|---|---|
| MER-001 | Critical | `merchant_id` | Unique + NOT NULL | ~99.7% | 100% |
| MER-002 | Critical | `merchant_category` | IN (8 categories: `Retail`, `Food & Beverage`, `Utilities`, `Travel`, `E-commerce`, `Gaming`, `Healthcare`, `Education`) | ~99% | 100% |
| MER-003 | Critical | `business_type` | IN (`individual`, `company`, `enterprise`) | ~99% | 100% |
| MER-004 | Critical | `country` | IN (`EG`, `SA`, `AE`, `KW`, `QA`) | ~99% | 100% |
| MER-005 | Warning | `risk_score` | Between 0.000 and 1.000 | 100% | 100% |
| MER-006 | Warning | `fee_percentage` | Between 1.50 and 3.50 | 100% | 100% |
| MER-007 | Warning | `monthly_limit` | `> 0` | 100% | 100% |

### 3.5 `devices` (4 rules)

| Rule ID | Severity | Column(s) | Logic | Bronze | Silver |
|---|---|---|---|---|---|
| DEV-001 | Critical | `device_id` | Unique + NOT NULL | ~99.7% | 100% |
| DEV-002 | Critical | `user_id` | FK exists in `users` | ~99% | 100% |
| DEV-003 | Critical | `device_type` | IN (`ios`, `android`, `web`) | ~99% | 100% |
| DEV-004 | Warning | `first_seen_at`, `last_seen_at` | `first_seen_at <= last_seen_at` | ~99% | 100% |

### 3.6 `payment_methods` (6 rules)

| Rule ID | Severity | Column(s) | Logic | Bronze | Silver |
|---|---|---|---|---|---|
| PAY-001 | Critical | `payment_method_id` | Unique + NOT NULL | ~99.7% | 100% |
| PAY-002 | Critical | `user_id` | FK exists in `users` | ~99% | 100% |
| PAY-003 | Critical | `method_type` | IN (`debit_card`, `credit_card`, `bank_account`, `wallet_balance`) | ~99% | 100% |
| PAY-004 | Warning | `last_four_digits` | 4 digits required for `debit_card`, `credit_card`, `bank_account`; NULL allowed only for `wallet_balance` | ~99% | 100% |
| PAY-005 | Warning | `expiry_date` | NULL or future date; NULL allowed for `bank_account` and `wallet_balance` | ~99% | 100% |
| PAY-006 | Warning | `is_default` | At most one default method per `user_id` | ~99% | 100% |

### 3.7 `kyc_records` (7 rules)

| Rule ID | Severity | Column(s) | Logic | Bronze | Silver |
|---|---|---|---|---|---|
| KYC-001 | Critical | `kyc_id` | Unique + NOT NULL | 100% | 100% |
| KYC-002 | Critical | `user_id` | FK exists in `users` + one record per user | 100% | 100% |
| KYC-003 | Critical | `verification_status` | IN (`verified`, `pending`, `rejected`) | 100% | 100% |
| KYC-004 | Critical | `document_type` | IN (`national_id`, `passport`, `iqama`, `emirates_id`, `civil_id`, `qatar_id`, `visa`) | 100% | 100% |
| KYC-005 | Warning | `rejection_reason` | NOT NULL when `verification_status = 'rejected'` | 100% | 100% |
| KYC-006 | Warning | `verified_at` | NOT NULL when `verification_status = 'verified'` | 100% | 100% |
| KYC-007 | Warning | `document_country` | Must equal `users.country` for same `user_id` | 100% | 100% |

---

## 4) Quarantine Policy

### 4.1 What Gets Quarantined

Rows failing any **Critical** rule where the row cannot be corrected are moved to `dq_quarantine`:

| Condition | Example | Action |
|---|---|---|
| Negative amount | `amount = -500.00` | Quarantine - cannot infer correct value |
| Orphan FK | `sender_account_id` not in `accounts` | Quarantine - broken lineage |
| Invalid enum | `status = 'Unknown'` | Quarantine - not an accepted value |

### 4.2 What Gets Corrected (Not Quarantined)

Rows failing these checks are corrected and retained in Silver.

| Condition | Example | Action |
|---|---|---|
| Duplicate transaction ID | Two rows with same `transaction_id` | Keep row with earliest `transaction_timestamp`, discard duplicate |
| Invalid timestamp order | `completed_timestamp < transaction_timestamp` | Set `completed_timestamp_utc = NULL` after UTC normalization; row is otherwise valid |

### 4.3 What Passes Through (Warning Only)

Rows failing only **Warning** rules remain in Silver with DQ flags:

| Column | Type | Description |
|---|---|---|
| `_dq_valid` | BOOLEAN | `True` if all Warning rules pass; `False` if any fail |
| `_dq_issues` | STRING | Pipe-separated list of failed rule IDs (e.g., `TXN-009\|TXN-018`) |

### 4.4 Quarantine Table Schema

> Matches `dq_quarantine` in `docs/06-data-model.md` Section 5.2

| Column | Type | Description |
|---|---|---|
| `entity_name` | STRING | Source table (e.g., `transactions`) |
| `batch_date` | DATE | Processing date |
| `source_record_id` | STRING | Source PK value (e.g., `transaction_id`) |
| `dq_rule_id` | STRING | Failed rule (e.g., `TXN-007`) |
| `dq_reason` | STRING | Human-readable reason (e.g., "Negative amount: -500.00") |
| `quarantined_at` | TIMESTAMP | Quarantine timestamp (UTC) |

---

## 5) Monitoring & Metrics

### 5.1 `dq_metrics` (per entity per batch)

> Matches `dq_metrics` in `docs/06-data-model.md` Section 5.3

| Column | Type | Description |
|---|---|---|
| `entity_name` | STRING | Table name |
| `batch_date` | DATE | Processing date |
| `total_rows` | INTEGER | Total rows processed |
| `quarantine_count` | INTEGER | Rows quarantined |
| `quarantine_rate` | FLOAT | `quarantine_count / total_rows` |
| `top_failed_rules` | STRING | Most common failure rule IDs |
| `null_rate_critical_fields` | FLOAT | % NULLs in mandatory fields |

### 5.2 Freshness SLA

| Metric | Target | BRD Reference |
|---|---|---|
| Hours since last Gold refresh | < 24 hours | KPI-11 |
| Alert threshold | > 24 hours triggers alert | BRD Section 8.2 |
| Tracked in | `gold_refresh_audit.finished_ts` | Data Model Section 5.1 |

### 5.3 Expected Quarantine Rates

| Entity | Expected Quarantine Rate | Primary Cause |
|---|---|---|
| `transactions` | ~2% (~20,000 rows) | Negative amounts (~20K); duplicates are corrected, not quarantined |
| `users` | ~0% | No critical noise injected |
| `accounts` | ~4% | Null/duplicate PKs, orphan `user_id`, invalid enums; negative balance remains warning-only |
| `merchants` | ~3% | Null PK plus invalid category/business type/country |
| `devices` | ~2% | Null PK, orphan `user_id`, invalid `device_type`; invalid time order remains warning-only |
| `payment_methods` | ~2% | Null PK, orphan `user_id`, invalid `method_type`; digit/expiry/default issues remain warning-only |
| `kyc_records` | ~0% | No critical noise (NULL doc_hash is Warning, not Critical) |

---

## 6) dbt Test Specifications (Silver + Gold)

### 6.1 Generic Tests (All Models)

```yaml
# Applied to every Silver and Gold table
tests:
  - unique         # on all PKs
  - not_null        # on all PKs and mandatory FKs
  - relationships   # on all FK columns -> parent table PK
  - accepted_values # on all enum columns
```

### 6.2 Silver-Specific Tests

| Test | Table | Logic | dbt Implementation |
|---|---|---|---|
| No duplicates | `silver_transactions` | `transaction_id` unique | `unique` test |
| No negative amounts | `silver_transactions` | `amount > 0` | Custom `dbt_utils.expression_is_true` |
| Valid timestamps | `silver_transactions` | `completed_timestamp >= transaction_timestamp` OR NULL | Custom test |
| FK: sender -> accounts | `silver_transactions` | `sender_account_id` exists in `silver_accounts` | `relationships` test |
| FK: device -> devices | `silver_transactions` | `device_id` exists in `silver_devices` | `relationships` test |
| FK: payment_method -> methods | `silver_transactions` | `payment_method_id` exists in `silver_payment_methods` | `relationships` test |
| Receiver self logic | `silver_transactions` | `self` => `receiver_id IS NULL` | Custom test |
| Receiver account logic | `silver_transactions` | `account` => `receiver_id` NOT NULL | Custom test |
| Receiver merchant logic | `silver_transactions` | `merchant` => `receiver_id` NOT NULL | Custom test |
| Receiver FK -> accounts | `silver_transactions` | If `receiver_type = 'account'`, `receiver_id` exists in `silver_accounts` | Custom test |
| Receiver FK -> merchants | `silver_transactions` | If `receiver_type = 'merchant'`, `receiver_id` exists in `silver_merchants` | Custom test |
| Txn type logic | `silver_transactions` | `Merchant_Payment` => `receiver_type = 'merchant'`; `P2P_Transfer` => `receiver_type = 'account'` | Custom test |
| UTC timestamps | All Silver tables | All canonical `*_utc` columns are valid timestamps | `not_null` + type check |

### 6.3 Gold-Specific Tests

| Test | Table | Logic | dbt Implementation |
|---|---|---|---|
| SK unique | `dim_user` | `user_sk` unique | `unique` test |
| SK unique | `dim_merchant` | `merchant_sk` unique | `unique` test |
| SK unique | `dim_date` | `date_sk` unique | `unique` test |
| FK: fact -> dim | `fact_transactions` | All `*_sk` exist in parent dims | `relationships` test per FK |
| Grain unique | `fact_user_daily_volume` | `user_daily_sk` unique | `unique` test |
| Grain unique | `fact_merchant_daily_volume` | `merchant_daily_sk` unique | `unique` test |
| No cross-currency mixing | `fact_user_daily_volume` | Each row is aggregated at `user_id + transaction_date + currency`; `currency` must be NOT NULL | `unique` on `user_daily_sk` + `not_null` on `currency` |
| SCD2 no overlap | `dim_user` | No overlapping `valid_from`/`valid_to` per `user_id` | Custom test |
| SCD2 one current | `dim_user` | Exactly one `is_current = True` per `user_id` | Custom test |
| TPV reconciliation | `fact_transactions` vs `fact_merchant_daily_volume` | `SUM(amount)` where `status = 'Success' AND receiver_type = 'merchant'` matches merchant daily totals | Custom reconciliation test |
| Row count reconciliation | `silver_transactions` vs `fact_transactions` | Row counts match (1:1 after dedup) | Custom test |
| Fraud subset | `fact_fraud_alerts` vs `fact_transactions` | All fraud alert `transaction_id` exist in `fact_transactions` | `relationships` test |

---

## 7) BRD Traceability

| BRD Requirement | DQ Rules That Support It |
|---|---|
| KPI-01 (TPV): `SUM(amount) WHERE status='Success'` | TXN-004 (valid status), TXN-007 (positive amounts), TXN-006 (valid currency) |
| KPI-05 (Fraud Rate): flagged / total | TXN-011 (flagged => pattern exists), TXN-012 (valid patterns) |
| KPI-08 (DAU/MAU): COUNT(DISTINCT user_id) | USR-001 (unique user_id), TXN-002 (unique txn_id for accurate counts) |
| KPI-09 (KYC Rate): verified / total | USR-006 (valid kyc_status), KYC-003 (consistent status) |
| KPI-11 (Freshness) | Freshness SLA monitoring (Section 5.2) |
| KPI-12 (Quarantine Rate) | `dq_metrics.quarantine_rate` (Section 5.1) |
| Q5 (New device + high value) | DEV-002 (device -> user FK), TXN-020 (txn -> device FK) |
| Q7 (KYC vs failed txns) | USR-006 (valid KYC), KYC-003 (consistent), TXN-004 (valid status) |
| Q8 (Merchant AML) | MER-001 (unique merchant), TXN-016 (Merchant_Payment => merchant) |

---

## 8) Alignment with Data Dictionary

> All noise rates, column names, and enum values in this document use exact values from `docs/03-data-dictionary.md` Section 4 (Intentional Data Noise) and Section 3 (Bronze Column Contracts).

| Cross-Reference | This Doc | Data Dictionary |
|---|---|---|
| Dup PK count | 10,000 | 10,000 (Section 4) |
| Negative amount count | 20,115 | 20,115 (Section 4) |
| Bad timestamp count | 11,044 | 11,044 (Section 4) |
| Dedup strategy | Keep earliest `transaction_timestamp` | Keep earliest `transaction_timestamp` (Section 5) |
| Invalid timestamp action | Set `completed_timestamp_utc = NULL` | Set `completed_timestamp_utc = NULL` (Section 5) |
| Quarantine table schema | Section 4.4 | Matches `dq_quarantine` in Data Model Section 5.2 |
