# Project Overview

| Version | Date       | Author             | Status |
| ------- | ---------- | ------------------ | ------ |
| 1.0     | 2026-03-04 | Mohamed Abdellatef | Final  |

> End-to-end Azure Lakehouse portfolio project for FinTech payments analytics and fraud investigation.

---

## 1) Scope

- **Domain:** Digital wallet and payment transactions.
- **Target market:** MENA focus (Egypt, Saudi Arabia, UAE) with regional coverage including Kuwait and Qatar in source data.
- **Primary goals:**
  - Build a realistic Bronze -> Silver -> Gold data pipeline.
  - Support fraud, finance, and product analytics use cases from BRD.
  - Demonstrate production-style data quality, auditability, and dimensional modeling.

---

## 2) End-to-End Flow

`Python Generator (CSV raw data)` -> `ADF` -> `ADLS Bronze` -> `Databricks PySpark (Bronze/Silver + DQ)` -> `dbt on Databricks (Gold facts/dims + tests)` -> `Power BI`.

---

## 3) Source Dataset (Generator)

- Entities: `users`, `accounts`, `merchants`, `transactions`, `devices`, `payment_methods`, `kyc_records`.
- Baseline full volume:
  - `users`: 50,000
  - `accounts`: ~62,000
  - `merchants`: 2,000
  - `devices`: ~82,000
  - `payment_methods`: ~85,000
  - `kyc_records`: 50,000
  - `transactions`: 1,010,000 (includes intentional duplicates/noise)
- Intentional data quality issues are injected to create real Silver cleansing work (duplicates, negative amounts, invalid timestamp order, nullable non-critical fields).

---

## 4) Architecture Components

| Component | Role |
|---|---|
| `data-generator/` | Produces raw CSV source data with controlled noise and fraud labels |
| Azure Data Factory (ADF) | Orchestrates ingestion and pipeline execution |
| ADLS Gen2 | Stores Bronze, Silver, and Gold layer data |
| Databricks (PySpark + Delta) | Bronze/Silver processing, cleansing, dedup, quarantine, DQ metrics |
| dbt Core on Databricks | Gold dimensional models, tests, and documentation |
| Power BI | KPI dashboards and stakeholder reporting |

---

## 5) Medallion Layer Contracts

| Layer | Contract |
|---|---|
| **Bronze** | Raw source fidelity, CSV landing, minimal transformation, known noise retained |
| **Silver** | Type casting, UTC normalization, dedup, critical-rule quarantine, validated conformed datasets |
| **Gold** | Star schema optimized for analytics and BI, conformed dimensions and business facts |

---

## 6) Gold Model Summary

- **Facts (4):**
  - `fact_transactions`
  - `fact_user_daily_volume`
  - `fact_merchant_daily_volume`
  - `fact_fraud_alerts`
- **Dimensions (7):**
  - `dim_user` (SCD2)
  - `dim_merchant` (SCD2)
  - `dim_account` (SCD1)
  - `dim_device` (SCD1)
  - `dim_payment_method` (SCD1)
  - `dim_date` (static)
  - `dim_geography` (static)

---

## 7) Data Quality and Monitoring

- Core outputs:
  - `dq_quarantine`
  - `dq_metrics`
  - `gold_refresh_audit`
- Key controls:
  - Dedup by `transaction_id` in Silver.
  - Quarantine critical failures (negative amount, FK orphans, invalid enums, invalid conditional receiver logic).
  - Correct non-critical timestamp ordering issue by setting invalid `completed_timestamp` to NULL.

---

## 8) Design Status

- BRD, data model, data dictionary, DQ framework, and STM are finalized and aligned with generator logic.
- Next phase is implementation of ADF, Databricks, dbt, and BI assets.

---

## 9) Related Documents

- `docs/01-business-requirements.md`
- `docs/03-data-dictionary.md`
- `docs/04-source-to-target-mapping.md`
- `docs/05-data-quality.md`
- `docs/06-data-model.md`

---

## 10) Diagrams

- Source ERD: [Source ERD](./diagrams/source-erd.png)
- Architecture: [Architecture Diagram](./diagrams/architecture-diagram.png)
- Gold Star Schema (Overview): [Gold Star Schema](./diagrams/gold-star-schema.png)
- Gold Star Schema (Detailed): [Gold Star Schema - Detailed](./diagrams/gold-star-schema-detailed.png)

### 10.1 Architecture Preview
![Architecture Diagram](./diagrams/architecture-diagram.png)

### 10.2 Gold Star Schema Preview
![Gold Star Schema](./diagrams/gold-star-schema.png)
