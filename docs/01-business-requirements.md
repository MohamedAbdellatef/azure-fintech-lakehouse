# Business Requirements Document (BRD) - FinTech Lakehouse 🏦

| Version | Date       | Author             | Status |
| ------- | ---------- | ------------------ | ------ |
| 1.0     | 2026-02-21 | Mohamed Abdellatef | Final  |

> **Purpose:** To build a scalable, end-to-end Medallion data architecture that processes high-volume digital wallet transactions, enabling rapid fraud detection, user behavior analysis, and automated financial reconciliation.
> **Dataset:** Synthetic FinTech Payment Data (1M+ records, 8 core entities).

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
| **Consolidate Data Sources**                | 100% of the 8 raw entities are ingested, cleansed, and modeled into a Star Schema daily.                                           |
| **Enable Multi-dimensional Fraud Analysis** | Reduce the data preparation time for Risk Analysts from days to hours by linking transactions to devices and KYC statuses.         |
| **Automate Financial Reconciliation**       | Deliver automated Total Payment Volume (TPV) and revenue aggregations with zero discrepancies handling multi-currency conversions. |

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
2. Which payment methods (e.g., Visa, Mada, Meeza, Wallet Balance) have the highest success rates and adoption across different user geographic locations?
3. What is the ratio of P2P transfers versus Merchant Payments, and how does this distribution vary between Basic and Platinum users?
4. What is the average transaction value (ATV) per country?

**Fraud & Risk:**

5. How many high-value transactions were initiated from newly registered, untrusted devices within 24 hours of account creation?
6. Which users exhibit "location jumping" patterns (e.g., transacting from two geographically distant locations within an impossible timeframe)?
7. What is the correlation between rejected/pending KYC statuses and reversed or failed transactions?
8. Which active merchant accounts are receiving an unusually high volume of transactions from newly funded wallets (potential money laundering indicator)?

**User Behavior & Retention:**

9. How many daily/monthly active users (DAU/MAU) do we have, and what is the trend over time?
10. What percentage of users complete their first transaction within 7 days of registration?
11. What is the user retention rate at 30/60/90 days by country and user tier?
12. Which user tiers (Basic, Silver, Gold, Platinum) have the highest transaction frequency and volume?

**Device & Channel:**

13. What is the distribution of transactions by device type (iOS vs Android vs Web)?
14. Which device models have the highest fraud flag rates?
15. How does transaction success rate vary across different app versions?

**Operational & Data Quality:**

16. What is the current data freshness (hours since last Gold layer refresh)?
17. What percentage of records are quarantined due to data quality issues, and what are the top failure reasons?
18. Are there any orphan records (e.g., transactions referencing non-existent accounts or users)?

---

## 4) KPI Definitions (Catalog)

> **Rule:** For ratio KPIs, compute as ratio of sums (not AVG of per-row ratios).

### 4.1 Financial KPIs

**KPI-01 Total Payment Volume (TPV)**

- Definition: Sum of all successful transaction amounts
- Formula: `SUM(amount) WHERE status = 'Success'`
- Grain: day/week/month; currency; country; merchant_category
- Filters: `status = 'Success'`

**KPI-02 Transaction Revenue (Fees)**

- Definition: Sum of all fee amounts collected
- Formula: `SUM(fee_amount) WHERE status = 'Success'`
- Grain: day/week/month; merchant_category
- Filters: `status = 'Success'`

**KPI-03 Average Transaction Value (ATV)**

- Definition: Average value per successful transaction
- Formula: `TPV / COUNT(DISTINCT transaction_id)`
- Grain: day/week/month; country; transaction_type
- Filters: `status = 'Success'`

**KPI-04 Transaction Success Rate**

- Definition: Percentage of transactions that completed successfully
- Formula: `COUNT(status='Success') / COUNT(*) * 100`
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
- Formula: `COUNT(device.is_trusted=False) / COUNT(*) * 100`
- Grain: day; country
- Filters: None

**KPI-07 High-Risk Transaction Amount**

- Definition: Sum of amounts from flagged transactions
- Formula: `SUM(amount) WHERE is_flagged = True`
- Grain: day/week
- Filters: `is_flagged = True`

### 4.3 User & Adoption KPIs

**KPI-08 Active Users (Daily/Monthly)**

- Definition: Distinct users with ≥1 successful transaction
- Formula: `COUNT(DISTINCT user_id) WHERE status = 'Success'`
- Grain: day (DAU) / month (MAU)
- Filters: `status = 'Success'`

**KPI-09 KYC Verification Rate**

- Definition: % of users with verified KYC status
- Formula: `COUNT(kyc_status='verified') / COUNT(*) * 100`
- Grain: month; country
- Filters: `is_active = True`

**KPI-10 Payment Method Adoption**

- Definition: Distribution of transactions by payment method provider
- Formula: `COUNT(*) GROUP BY provider / COUNT(*) * 100`
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

### 5.1 Qualifying Transaction Status (Locked)

- **Included in KPIs:** `Success`
- **Excluded:** `Failed`, `Pending`, `Reversed`
- **Rationale:** Only completed transactions represent actual money movement. Failed/Pending/Reversed inflate volume metrics without real value.

### 5.2 Fraud Flag Definition (Locked)

- **is_flagged = True** when ANY of these patterns detected:
  - `velocity`: >5 transactions in 10 minutes
  - `amount`: Single transaction >50,000 (local currency)
  - `time`: Transaction between 02:00-05:00 local time
  - `new_device`: First transaction from new device >10,000
- **Rationale:** Aligns with industry-standard fraud detection heuristics.

### 5.3 Currency Policy (Locked)

- **All monetary values stored in:** Original transaction currency (EGP, SAR, AED, KWD, QAR)
- **No currency conversion applied** in Bronze/Silver layers
- **Gold layer:** May include USD-equivalent column for cross-country comparison (using daily exchange rate snapshot)
- **Rationale:** Preserving original currency prevents rounding errors and audit issues.

### 5.4 Timezone Policy (Locked)

- **All timestamps stored as:** UTC
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

**Source Tables:**

- `transactions`
- `accounts`
- `devices`
- `kyc_records`
- `payment_methods`
- `users`
- `merchants`

**Reference/Lookup:**

- `fraud_rules`

---

## 7) Data Quality & Controls

### 7.1 Critical Record Rules (Quarantine)

Quarantine rows that violate:

- **Missing PKs:** `transaction_id`, `user_id`, `account_id`, `merchant_id` is NULL
- **Negative amounts:** `amount < 0` or `fee_amount < 0`
- **Invalid timestamps:** `completed_timestamp < transaction_timestamp`
- **Invalid status:** `status NOT IN ('Success', 'Failed', 'Pending', 'Reversed')`
- **Invalid KYC status:** `kyc_status NOT IN ('verified', 'pending', 'rejected')`
- **Orphan records:** `user_id` not found in `users` table

**Quarantine table must store:**

- `entity_name`, `batch_date`, `dq_rule_name`
- `dq_reason`, `source_record_id`, `created_at`

### 7.2 Tests (Minimum)

**Uniqueness + Not Null:**

- `transactions.transaction_id` — unique, not null
- `users.user_id` — unique, not null
- `accounts.account_id` — unique, not null
- `merchants.merchant_id` — unique, not null

**Referential Integrity:**

- `transactions.sender_account_id` → `accounts.account_id`
- `transactions.device_id` → `devices.device_id`
- `transactions.receiver_id` → `merchants.merchant_id` (when `receiver_type = 'merchant'`)
- `accounts.user_id` → `users.user_id`
- `devices.user_id` → `users.user_id`
- `kyc_records.user_id` → `users.user_id`
- `payment_methods.user_id` → `users.user_id`

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
- **Backfill:** Supported via `batch_date` parameter in ADF/Airflow
- **Idempotency:** Re-running same `batch_date` performs MERGE (upsert) — safe to retry

### 8.2 Audit Tables

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

### 8.3 BI Health Page Requirements

Dashboard must display:

- Last successful refresh timestamp
- Freshness in hours (with alert if > 24h)
- Row counts per layer (Bronze → Silver → Gold)
- Quarantine % with drill-down to top failure reasons
- Pipeline run history (last 7 days)

---

## 9) Analytics Data Model Summary

> Detailed design in [`06-data-model.md`](./06-data-model.md)

### 9.1 Grain Decisions (Locked)

| Fact Table          | Grain                         | Rationale                                |
| ------------------- | ----------------------------- | ---------------------------------------- |
| `fact_transactions` | 1 row per transaction         | Atomic level for detailed fraud analysis |
| `fact_daily_volume` | 1 row per user/merchant/day   | Pre-aggregated for dashboard performance |
| `fact_fraud_alerts` | 1 row per flagged transaction | Filtered fact for risk team              |

### 9.2 Conceptual Facts & Dimensions

**Fact Tables:**

- `fact_transactions` — Core transaction metrics (amount, fee, status, fraud flags)
- `fact_daily_volume` — Aggregated TPV, transaction count per day
- `fact_fraud_alerts` — Subset of flagged transactions with pattern details

**Dimension Tables:**

- `dim_user` — User demographics, KYC status, tier, country
- `dim_merchant` — Merchant details, category, risk score
- `dim_account` — Account type, currency, limits
- `dim_device` — Device type, model, trust status
- `dim_payment_method` — Card/bank details, provider
- `dim_date` — Calendar dimension (date, week, month, quarter, year, weekday)
- `dim_geography` — Country, city (derived from user/merchant)

### 9.3 Slowly Changing Dimensions

| Dimension      | SCD Type | Rationale                                   |
| -------------- | -------- | ------------------------------------------- |
| `dim_user`     | Type 2   | Track KYC status changes over time          |
| `dim_merchant` | Type 2   | Track risk score changes                    |
| `dim_device`   | Type 1   | Device trust status overwrites (no history) |
| `dim_account`  | Type 1   | Balance/limit updates overwrite             |

---
