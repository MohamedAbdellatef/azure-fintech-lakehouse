# FinTech Fraud Detection Data Pipeline 🛡️💸

## 📋 Project Overview
This project simulates an end-to-end data engineering solution for a digital wallet company (similar to STC Pay, Fawry, or Revolut). The goal is to build a modern **Lakehouse Architecture** on **Azure** using **Databricks** and **dbt** to process millions of transactions, ensure data quality, and establish a foundation for real-time fraud detection analytics.

The pipeline handles raw, noisy data, processes it through a Medallion Architecture (Bronze -> Silver -> Gold), and models it for BI consumption.

## 🎯 Business Problem Statement
In the rapidly growing digital payments sector, processing high volumes of transactions while instantly detecting fraudulent activities is critical. The current legacy systems struggle with:
* **Data Silos:** User data, transaction logs, and device info reside in disconnected systems.
* **Poor Data Quality:** Inconsistent formatting and duplicates hinder accurate reporting.
* **Slow Fraud Detection:** Inability to correlate device geo-location with transaction velocity in near real-time.

## 👥 Key Stakeholders
* **Fraud Analysts Team:** Needs clean, linked data between users, devices, and transactions to investigate suspicious patterns.
* **Finance Department:** Requires accurate daily aggregation of deposits, withdrawals, and merchant payments for reconciliation.
* **Product Managers:** Needs insights into user demographics and popular payment methods to drive new feature development.

## 💡 Use Cases & Business Questions
The final Gold layer (Star Schema) is designed to answer questions like:
1.  **Fraud Detection:** Which users have performed transactions from two different countries within a 1-hour window (Location Jumping)?
2.  **Fraud Detection:** Identify devices associated with more than 5 distinct user accounts performing high-value transfers.
3.  **Business Performance:** What is the total transaction volume (TPV) per currency and merchant category daily?
4.  **User Behavior:** What are the top 3 payment methods used by "Gold Tier" users versus "Basic Tier" users?

## 🛠️ Tech Stack & Architecture
* **Cloud Provider:** Microsoft Azure
* **Data Ingestion:** Azure Data Factory (ADF)
* **Storage (Data Lake):** Azure Data Lake Storage (ADLS) Gen2
* **Data Processing & Lakehouse:** Databricks (PySpark, Delta Lake)
* **Transformation & Modeling:** dbt (data build tool)
* **Orchestration:** Apache Airflow (Managed or on VM)
* **BI & Visualization:** Power BI / Tableau

---