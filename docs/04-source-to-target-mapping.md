# Source-to-Target Mapping (STM)

| Version | Date       | Author             | Status |
| ------- | ---------- | ------------------ | ------ |
| 1.1     | 2026-03-04 | Mohamed Abdellatef | Final  |

> **Purpose:** To document the exact column-level data lineage and transformation logic from Bronze (Raw) to Silver (Cleansed) to Gold (Modeled) layers.

---

## 1) Bronze to Silver (Cleansing Rules)

The Silver layer maintains a 1:1 structural relationship with Bronze (keeping the same business columns) but applies the following record-level transformations.

| Source Entity     | Target Entity         | Transformation Logic                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| ----------------- | --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| All Bronze Tables | All Silver Tables     | 1. Cast string amounts/scores to `DECIMAL`<br>2. Cast string timestamps to UTC-normalized `TIMESTAMP` columns; where canonical normalized columns are introduced, name them with `*_utc`<br>3. Cast string flags to `BOOLEAN`<br>4. Add `_dq_valid` and `_dq_issues` flags<br>5. Apply incremental filter: entity event timestamp `> last_successful_watermark - lookback_window` and `<= current_batch_cutoff`                                                                                                                                   |
| `transactions`    | `silver_transactions` | 1. **Dedup:** Keep row with earliest `transaction_timestamp` partitioned by `transaction_id`<br>2. **Quarantine (Critical):** Move rows failing critical rules to `dq_quarantine` (negative `amount`, negative `fee_amount`, missing required FKs such as `sender_account_id` / `device_id` / `payment_method_id`, orphan FKs including conditional `receiver_id` account/merchant checks, invalid enums, receiver conditional FK/NULL logic)<br>3. **Timestamp Correction (Warning):** Persist normalized timestamps in `transaction_timestamp_utc` / `completed_timestamp_utc`; if `completed_timestamp < transaction_timestamp`, set `completed_timestamp_utc = NULL`<br>4. **Load pattern:** Upsert with `MERGE` on `transaction_id` for idempotent reruns and backfills |

---

## 1.1 Incremental Watermark Columns

| Entity | Watermark / Event Column | Rationale |
|---|---|---|
| `transactions` | `transaction_timestamp` | Event-time transaction processing |
| `users` | `updated_at` | Latest profile state changes |
| `accounts` | `updated_at` | Latest account state changes |
| `devices` | `last_seen_at` | Latest device activity |
| `payment_methods` | `updated_at` | Latest payment-method state changes |
| `kyc_records` | `updated_at` | Latest KYC review state changes |
| `merchants` | `updated_at` | Latest merchant state changes |

---

## 2) Silver to Gold (Dimensions)

### 2.1 `dim_user` (SCD Type 2)

**Source:** `silver_users`

| Gold Column           | Source Column           | Transformation / Logic                                |
| --------------------- | ----------------------- | ----------------------------------------------------- |
| `user_sk`             | `user_id`, `valid_from` | `MD5(concat(user_id, valid_from))`                    |
| `user_id`             | `user_id`               | Direct mapping                                        |
| `first_name`          | `first_name`            | Direct mapping                                        |
| `last_name`           | `last_name`             | Direct mapping                                        |
| `email`               | `email`                 | Direct mapping                                        |
| `country`             | `country`               | Direct mapping                                        |
| `city`                | `city`                  | Direct mapping                                        |
| `preferred_currency`  | `preferred_currency`    | Direct mapping                                        |
| `kyc_status`          | `kyc_status`            | Direct mapping                                        |
| `user_tier`           | `user_tier`             | Direct mapping                                        |
| `is_active`           | `is_active`             | Direct mapping                                        |
| `registration_ts_utc` | `registration_date`     | Timestamp cast/normalized to UTC TIMESTAMP            |
| `registration_date`   | `registration_date`     | Cast to UTC DATE                                      |
| `valid_from`          | -                       | dbt snapshot `dbt_valid_from` (start of validity)     |
| `valid_to`            | -                       | dbt snapshot `dbt_valid_to` (end of validity)         |
| `is_current`          | -                       | `CASE WHEN valid_to IS NULL THEN True ELSE False END` |

_(Note: `phone_number`, `date_of_birth`, `gender`, `created_at`, `updated_at` are dropped)._

### 2.2 `dim_merchant` (SCD Type 2)

**Source:** `silver_merchants`

| Gold Column         | Source Column               | Transformation / Logic                                |
| ------------------- | --------------------------- | ----------------------------------------------------- |
| `merchant_sk`       | `merchant_id`, `valid_from` | `MD5(concat(merchant_id, valid_from))`                |
| `merchant_id`       | `merchant_id`               | Direct mapping                                        |
| `merchant_name`     | `merchant_name`             | Direct mapping                                        |
| `merchant_category` | `merchant_category`         | Direct mapping                                        |
| `business_type`     | `business_type`             | Direct mapping                                        |
| `country`           | `country`                   | Direct mapping                                        |
| `city`              | `city`                      | Direct mapping                                        |
| `risk_score`        | `risk_score`                | Direct mapping                                        |
| `fee_percentage`    | `fee_percentage`            | Direct mapping                                        |
| `monthly_limit`     | `monthly_limit`             | Direct mapping                                        |
| `is_verified`       | `is_verified`               | Direct mapping                                        |
| `is_active`         | `is_active`                 | Direct mapping                                        |
| `registration_date` | `registration_date`         | Direct mapping                                        |
| `valid_from`        | -                           | dbt snapshot `dbt_valid_from`                         |
| `valid_to`          | -                           | dbt snapshot `dbt_valid_to`                           |
| `is_current`        | -                           | `CASE WHEN valid_to IS NULL THEN True ELSE False END` |

### 2.3 `dim_account` (SCD Type 1)

**Source:** `silver_accounts`

| Gold Column     | Source Column   | Transformation / Logic |
| --------------- | --------------- | ---------------------- |
| `account_sk`    | `account_id`    | `MD5(account_id)`      |
| `account_id`    | `account_id`    | Direct mapping         |
| `user_id`       | `user_id`       | Direct mapping         |
| `account_type`  | `account_type`  | Direct mapping         |
| `currency`      | `currency`      | Direct mapping         |
| `balance`       | `balance`       | Direct mapping         |
| `daily_limit`   | `daily_limit`   | Direct mapping         |
| `monthly_limit` | `monthly_limit` | Direct mapping         |
| `status`        | `status`        | Direct mapping         |
| `created_at`    | `created_at`    | Direct mapping         |

### 2.4 `dim_device` (SCD Type 1)

**Source:** `silver_devices`

| Gold Column          | Source Column        | Transformation / Logic |
| -------------------- | -------------------- | ---------------------- |
| `device_sk`          | `device_id`          | `MD5(device_id)`       |
| `device_id`          | `device_id`          | Direct mapping         |
| `user_id`            | `user_id`            | Direct mapping         |
| `device_type`        | `device_type`        | Direct mapping         |
| `device_model`       | `device_model`       | Direct mapping         |
| `os_version`         | `os_version`         | Direct mapping         |
| `app_version`        | `app_version`        | Direct mapping         |
| `device_fingerprint` | `device_fingerprint` | Direct mapping         |
| `is_trusted`         | `is_trusted`         | Direct mapping         |
| `first_seen_at`      | `first_seen_at`      | Direct mapping         |
| `last_seen_at`       | `last_seen_at`       | Direct mapping         |

### 2.5 `dim_payment_method` (SCD Type 1)

**Source:** `silver_payment_methods`

| Gold Column         | Source Column       | Transformation / Logic   |
| ------------------- | ------------------- | ------------------------ |
| `payment_method_sk` | `payment_method_id` | `MD5(payment_method_id)` |
| `payment_method_id` | `payment_method_id` | Direct mapping           |
| `user_id`           | `user_id`           | Direct mapping           |
| `method_type`       | `method_type`       | Direct mapping           |
| `provider`          | `provider`          | Direct mapping           |
| `last_four_digits`  | `last_four_digits`  | Direct mapping           |
| `expiry_date`       | `expiry_date`       | Direct mapping           |
| `is_default`        | `is_default`        | Direct mapping           |
| `is_verified`       | `is_verified`       | Direct mapping           |
| `is_active`         | `is_active`         | Direct mapping           |
| `added_at`          | `added_at`          | Direct mapping           |

### 2.6 `dim_date` (Static)

**Source:** `dbt seed` (Calendar Generation)

| Gold Column    | Source Column | Transformation / Logic                           |
| -------------- | ------------- | ------------------------------------------------ |
| `date_sk`      | `full_date`   | `MD5(full_date)`                                 |
| `full_date`    | `date`        | Direct mapping                                   |
| `day_of_month` | `date`        | `DAY(date)`                                      |
| `day_of_week`  | `date`        | `((DAYOFWEEK(date) + 5) % 7) + 1` (1=Mon, 7=Sun) |
| `day_name`     | `date`        | `DATE_FORMAT(date, 'EEEE')`                      |
| `is_weekend`   | `date`        | `DAYOFWEEK(date) IN (1, 7)`                      |
| `week_of_year` | `date`        | `WEEKOFYEAR(date)`                               |
| `month_num`    | `date`        | `MONTH(date)`                                    |
| `month_name`   | `date`        | `DATE_FORMAT(date, 'MMMM')`                      |
| `quarter`      | `date`        | `QUARTER(date)`                                  |
| `year`         | `date`        | `YEAR(date)`                                     |
| `year_month`   | `date`        | `DATE_FORMAT(date, 'yyyy-MM')`                   |

### 2.7 `dim_geography` (Static)

**Source:** `dbt seed` (MENA Reference Data)

| Gold Column    | Source Column     | Transformation / Logic              |
| -------------- | ----------------- | ----------------------------------- |
| `geography_sk` | `country`, `city` | `MD5(concat(country, city))`        |
| `country`      | `country_code`    | Direct mapping (EG, SA, AE, KW, QA) |
| `country_name` | `country_name`    | Direct mapping                      |
| `city`         | `city_name`       | Direct mapping                      |
| `currency`     | `currency`        | Direct mapping                      |
| `timezone`     | `timezone`        | Direct mapping                      |

---

## 3) Silver to Gold (Facts)

### 3.1 `fact_transactions`

**Source:** `silver_transactions` (`TXN`) joins to Dimensions

| Gold Column                 | Source Column                                                                         | Transformation / Logic                                                                                                                                                                             |
| --------------------------- | ------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `transaction_id`            | `TXN.transaction_id`                                                                  | Direct mapping                                                                                                                                                                                     |
| `date_sk`                   | `TXN.transaction_timestamp_utc`                                                       | `MD5(full_date)` where `full_date = CAST(transaction_timestamp_utc AS DATE)`                                                                                                                       |
| `user_sk`                   | `TXN.sender_account_id`                                                               | Derive `user_id` via `silver_accounts` (`sender_account_id -> user_id`), then as-of join to `dim_user` where `TXN.transaction_timestamp_utc >= valid_from` and `< COALESCE(valid_to,'9999-12-31')` |
| `account_sk`                | `TXN.sender_account_id`                                                               | `MD5(sender_account_id)`                                                                                                                                                                           |
| `merchant_sk`               | `TXN.receiver_id`                                                                     | As-of join to `dim_merchant` on `merchant_id = receiver_id` using `TXN.transaction_timestamp_utc`; store resolved `dim_merchant.merchant_sk` when `receiver_type = 'merchant'`, else NULL          |
| `device_sk`                 | `TXN.device_id`                                                                       | `MD5(device_id)`                                                                                                                                                                                   |
| `payment_method_sk`         | `TXN.payment_method_id`                                                               | `MD5(payment_method_id)`                                                                                                                                                                           |
| `geography_sk`              | `TXN.sender_account_id -> silver_accounts.user_id -> dim_user.country, dim_user.city` | `MD5(concat(country, city))` from the same as-of resolved sender user dimension row                                                                                                                |
| `transaction_type`          | `TXN.transaction_type`                                                                | Direct mapping                                                                                                                                                                                     |
| `receiver_type`             | `TXN.receiver_type`                                                                   | Direct mapping                                                                                                                                                                                     |
| `status`                    | `TXN.status`                                                                          | Direct mapping                                                                                                                                                                                     |
| `amount`                    | `TXN.amount`                                                                          | Direct mapping                                                                                                                                                                                     |
| `fee_amount`                | `TXN.fee_amount`                                                                      | Direct mapping                                                                                                                                                                                     |
| `total_charged`             | `TXN.amount`, `TXN.fee_amount`                                                        | `amount + fee_amount`                                                                                                                                                                              |
| `currency`                  | `TXN.currency`                                                                        | Direct mapping                                                                                                                                                                                     |
| `is_flagged`                | `TXN.is_flagged`                                                                      | Direct mapping                                                                                                                                                                                     |
| `fraud_pattern`             | `TXN.fraud_pattern`                                                                   | Direct mapping                                                                                                                                                                                     |
| `risk_score`                | `TXN.risk_score`                                                                      | Direct mapping                                                                                                                                                                                     |
| `is_trusted_device`         | `dim_device.is_trusted`                                                           | Read from `dim_device` join                                                                                                                                                                        |
| `transaction_timestamp_utc` | `TXN.transaction_timestamp_utc`                                                       | Direct mapping                                                                                                                                                                                     |
| `completed_timestamp_utc`   | `TXN.completed_timestamp_utc`                                                         | Direct mapping                                                                                                                                                                                     |
| `transaction_date`          | `TXN.transaction_timestamp_utc`                                                       | `CAST(transaction_timestamp_utc AS DATE)`                                                                                                                                                          |
| `transaction_hour`          | `TXN.transaction_timestamp_utc`                                                       | `HOUR(transaction_timestamp_utc)`                                                                                                                                                                  |
| `ip_address`                | `TXN.ip_address`                                                                      | Direct mapping                                                                                                                                                                                     |
| `latitude`                  | `TXN.latitude`                                                                        | Direct mapping                                                                                                                                                                                     |
| `longitude`                 | `TXN.longitude`                                                                       | Direct mapping                                                                                                                                                                                     |

### 3.2 `fact_user_daily_volume`

**Source:** `silver_transactions` aggregated by user, date, currency

| Gold Column        | Source Column                                                                     | Transformation / Logic                                                                                                 |
| ------------------ | --------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| `user_daily_sk`    | `user_id`, `date`, `currency`                                                     | `MD5(concat(user_id, transaction_date, currency))`                                                                     |
| `user_sk`          | `sender_account_id`                                                               | Derive `user_id` via `silver_accounts`, then end-of-day as-of join to `dim_user` using `transaction_date 23:59:59 UTC` |
| `date_sk`          | `transaction_date`                                                                | `MD5(full_date)` where `full_date = transaction_date`                                                                  |
| `geography_sk`     | `sender_account_id -> silver_accounts.user_id -> dim_user.country, dim_user.city` | `MD5(concat(country, city))` from sender user at end-of-day snapshot                                                   |
| `transaction_date` | `transaction_timestamp_utc`                                                       | `CAST(transaction_timestamp_utc AS DATE)`                                                                              |
| `txn_count`        | `transaction_id`                                                                  | `COUNT(*)`                                                                                                             |
| `success_count`    | `status`                                                                          | `COUNT(*) WHERE status = 'Success'`                                                                                    |
| `failed_count`     | `status`                                                                          | `COUNT(*) WHERE status = 'Failed'`                                                                                     |
| `total_amount`     | `amount`                                                                          | `SUM(amount) WHERE status = 'Success'`                                                                                 |
| `total_fees`       | `fee_amount`                                                                      | `SUM(fee_amount) WHERE status = 'Success'`                                                                             |
| `avg_amount`       | `total_amount`, `success_count`                                                   | `total_amount / NULLIF(success_count, 0)`                                                                              |
| `flagged_count`    | `is_flagged`                                                                      | `COUNT(*) WHERE is_flagged = True`                                                                                     |
| `currency`         | `currency`                                                                        | Group by key                                                                                                           |

### 3.3 `fact_merchant_daily_volume`

**Source:** `silver_transactions` WHERE `receiver_type = 'merchant'`

| Gold Column              | Source Column                                            | Transformation / Logic                                                                                                                     |
| ------------------------ | -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `merchant_daily_sk`      | `receiver_id`, `date`, `currency`                        | `MD5(concat(receiver_id, transaction_date, currency))`                                                                                     |
| `merchant_sk`            | `receiver_id`                                            | End-of-day as-of join to `dim_merchant` on `merchant_id = receiver_id` using `transaction_date 23:59:59 UTC`; store resolved `merchant_sk` |
| `date_sk`                | `transaction_date`                                       | `MD5(full_date)` where `full_date = transaction_date`                                                                                      |
| `geography_sk`           | `receiver_id -> dim_merchant.country, dim_merchant.city` | `MD5(concat(country, city))` from merchant at end-of-day snapshot                                                                          |
| `transaction_date`       | `transaction_timestamp_utc`                              | `CAST(transaction_timestamp_utc AS DATE)`                                                                                                  |
| `txn_count`              | `transaction_id`                                         | `COUNT(*)`                                                                                                                                 |
| `success_count`          | `status`                                                 | `COUNT(*) WHERE status = 'Success'`                                                                                                        |
| `total_amount`           | `amount`                                                 | `SUM(amount) WHERE status = 'Success'`                                                                                                     |
| `total_fees`             | `fee_amount`                                             | `SUM(fee_amount) WHERE status = 'Success'`                                                                                                 |
| `distinct_senders`       | `sender_account_id`                                      | `COUNT(DISTINCT sender_account_id)`                                                                                                        |
| `newly_funded_txn_count` | `sender_account_id`                                      | `COUNT(*)` WHERE sender had Deposit in last 24h                                                                                            |
| `currency`               | `currency`                                               | Group by key                                                                                                                               |

### 3.4 `fact_fraud_alerts`

**Source:** `silver_transactions` WHERE `is_flagged = True`

| Gold Column                 | Source Column                                                                     | Transformation / Logic                                                                                                                 |
| --------------------------- | --------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `transaction_id`            | `transaction_id`                                                                  | Direct mapping                                                                                                                         |
| `user_sk`                   | `sender_account_id`                                                               | Derive `user_id` via `silver_accounts`, then as-of join to `dim_user` using `transaction_timestamp_utc`                                |
| `account_sk`                | `sender_account_id`                                                               | `MD5(sender_account_id)`                                                                                                               |
| `device_sk`                 | `device_id`                                                                       | `MD5(device_id)`                                                                                                                       |
| `merchant_sk`               | `receiver_id`                                                                     | As-of join to `dim_merchant` on `merchant_id = receiver_id`; store resolved `merchant_sk` when `receiver_type = 'merchant'`, else NULL |
| `date_sk`                   | `transaction_timestamp_utc`                                                       | `MD5(full_date)` where `full_date = CAST(transaction_timestamp_utc AS DATE)`                                                           |
| `geography_sk`              | `sender_account_id -> silver_accounts.user_id -> dim_user.country, dim_user.city` | `MD5(concat(country, city))` from the same as-of resolved sender user dimension row                                                    |
| `fraud_pattern`             | `fraud_pattern`                                                                   | Direct mapping                                                                                                                         |
| `amount`                    | `amount`                                                                          | Direct mapping                                                                                                                         |
| `currency`                  | `currency`                                                                        | Direct mapping                                                                                                                         |
| `risk_score`                | `risk_score`                                                                      | Direct mapping                                                                                                                         |
| `is_trusted_device`         | `is_trusted`                                                                      | Read from `dim_device`                                                                                                                 |
| `user_kyc_status`           | `kyc_status`                                                                      | Read from resolved `dim_user` row                                                                                                      |
| `user_tier`                 | `user_tier`                                                                       | Read from resolved `dim_user` row                                                                                                      |
| `transaction_timestamp_utc` | `transaction_timestamp_utc`                                                       | Direct mapping                                                                                                                         |
| `transaction_date`          | `transaction_timestamp_utc`                                                       | `CAST(transaction_timestamp_utc AS DATE)`                                                                                              |
| `latitude`                  | `latitude`                                                                        | Direct mapping                                                                                                                         |
| `longitude`                 | `longitude`                                                                       | Direct mapping                                                                                                                         |
