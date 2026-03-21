# Databricks notebook source
# MAGIC %md
# MAGIC # Silver Transactions
# MAGIC
# MAGIC Cleanses Bronze transactions into Silver by applying:
# MAGIC - incremental scope filtering
# MAGIC - critical-rule quarantine
# MAGIC - warning/correction logic
# MAGIC - deduplication
# MAGIC - idempotent writes to `silver.transactions` and `audit.dq_quarantine`

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1) Runtime Configuration

# COMMAND ----------

from datetime import datetime, timedelta

dbutils.widgets.text(
    "source_table",
    "hive_metastore.bronze.transactions",
    "Source Table",
)
dbutils.widgets.text(
    "target_table",
    "hive_metastore.silver.transactions",
    "Target Table",
)
dbutils.widgets.text(
    "quarantine_table",
    "hive_metastore.audit.dq_quarantine",
    "Quarantine Table",
)
dbutils.widgets.text("batch_date", "", "Batch Date (YYYY-MM-DD)")
dbutils.widgets.text("batch_cutoff_ts", "", "Batch Cutoff Timestamp")
dbutils.widgets.text("lookback_hours", "24", "Lookback Hours")
dbutils.widgets.dropdown(
    "write_strategy",
    "merge",
    ["merge", "overwrite"],
    "Write Strategy",
)

source_table = dbutils.widgets.get("source_table").strip()
target_table = dbutils.widgets.get("target_table").strip()
quarantine_table = dbutils.widgets.get("quarantine_table").strip()
batch_date = dbutils.widgets.get("batch_date").strip()
batch_cutoff_ts = dbutils.widgets.get("batch_cutoff_ts").strip()
lookback_hours_raw = dbutils.widgets.get("lookback_hours").strip()
write_strategy = dbutils.widgets.get("write_strategy").strip().lower()

if not source_table:
    raise ValueError("Widget 'source_table' cannot be empty.")
if not target_table:
    raise ValueError("Widget 'target_table' cannot be empty.")
if not quarantine_table:
    raise ValueError("Widget 'quarantine_table' cannot be empty.")
if not batch_cutoff_ts:
    raise ValueError("Widget 'batch_cutoff_ts' cannot be empty.")
if write_strategy not in {"merge", "overwrite"}:
    raise ValueError("Widget 'write_strategy' must be one of: merge, overwrite.")

try:
    lookback_hours = int(lookback_hours_raw)
except ValueError as exc:
    raise ValueError("Widget 'lookback_hours' must be an integer.") from exc

if lookback_hours < 0:
    raise ValueError("Widget 'lookback_hours' must be >= 0.")

try:
    batch_cutoff_dt = datetime.fromisoformat(batch_cutoff_ts.replace("Z", "").replace(" ", "T"))
except ValueError as exc:
    raise ValueError(
        "Widget 'batch_cutoff_ts' must be a valid ISO timestamp, e.g. 2026-03-14T08:30:00."
    ) from exc

if not batch_date:
    batch_date = batch_cutoff_dt.strftime("%Y-%m-%d")
else:
    try:
        datetime.strptime(batch_date, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("Widget 'batch_date' must be in YYYY-MM-DD format.") from exc

lookback_start_dt = batch_cutoff_dt - timedelta(hours=lookback_hours)

spark.conf.set("spark.sql.session.timeZone", "UTC")

print(f"Source table:      {source_table}")
print(f"Target table:      {target_table}")
print(f"Quarantine table:  {quarantine_table}")
print(f"Batch date:        {batch_date}")
print(f"Batch cutoff:      {batch_cutoff_dt.isoformat(sep=' ')} UTC")
print(f"Lookback hours:    {lookback_hours}")
print(f"Lookback start:    {lookback_start_dt.isoformat(sep=' ')} UTC")
print(f"Write strategy:    {write_strategy}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2) Validate Source and Reference Tables

# COMMAND ----------

table_parts = source_table.split(".")
if len(table_parts) < 2:
    raise ValueError(
        "Widget 'source_table' should be schema-qualified or catalog.schema-qualified."
    )

source_namespace = ".".join(table_parts[:-1])
audit_namespace = ".".join(quarantine_table.split(".")[:-1])

accounts_table = f"{source_namespace}.accounts"
devices_table = f"{source_namespace}.devices"
payment_methods_table = f"{source_namespace}.payment_methods"
merchants_table = f"{source_namespace}.merchants"
metrics_table = f"{audit_namespace}.dq_metrics"

required_tables = {
    "transactions": source_table,
    "accounts": accounts_table,
    "devices": devices_table,
    "payment_methods": payment_methods_table,
    "merchants": merchants_table,
}

for entity_name, table_name in required_tables.items():
    if not spark.catalog.tableExists(table_name):
        raise RuntimeError(f"Required table for '{entity_name}' does not exist: {table_name}")

print("All required Bronze tables are available.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3) Read Bronze Scope

# COMMAND ----------

from pyspark.sql import functions as F

cutoff_literal = F.lit(batch_cutoff_dt.strftime("%Y-%m-%d %H:%M:%S")).cast("timestamp")
lookback_literal = F.lit(lookback_start_dt.strftime("%Y-%m-%d %H:%M:%S")).cast("timestamp")

bronze_df = (
    spark.table(source_table)
    .withColumn("_scope_transaction_ts", F.to_timestamp("transaction_timestamp"))
    .filter(F.col("_scope_transaction_ts").isNotNull())
    .filter(F.col("_scope_transaction_ts") <= cutoff_literal)
    .filter(F.col("_scope_transaction_ts") >= lookback_literal)
    .drop("_scope_transaction_ts")
    .cache()
)

bronze_count = bronze_df.count()
if bronze_count == 0:
    print("No Bronze transactions in scope. Exiting gracefully.")
    dbutils.notebook.exit("NO_DATA")

print(f"Scoped Bronze transactions: {bronze_count:,}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4) Normalize and Cast to Silver Contract

# COMMAND ----------

string_columns = [
    "transaction_id",
    "sender_account_id",
    "receiver_id",
    "receiver_type",
    "transaction_type",
    "payment_method_id",
    "currency",
    "status",
    "device_id",
    "ip_address",
    "fraud_pattern",
]

silver_base_df = bronze_df.drop("_ingest_ts", "_source_file")

for column_name in string_columns:
    silver_base_df = silver_base_df.withColumn(
        column_name,
        F.when(
            F.trim(F.col(column_name)) == "",
            F.lit(None),
        ).otherwise(F.trim(F.col(column_name))),
    )

silver_base_df = (
    silver_base_df
    .withColumn("receiver_type", F.lower(F.col("receiver_type")))
    .withColumn("fraud_pattern", F.lower(F.col("fraud_pattern")))
    .withColumn("currency", F.upper(F.col("currency")))
    .withColumn(
        "is_flagged",
        F.when(F.lower(F.trim(F.col("is_flagged"))).isin("true", "1", "yes"), F.lit(True))
        .when(F.lower(F.trim(F.col("is_flagged"))).isin("false", "0", "no"), F.lit(False))
        .otherwise(F.lit(None).cast("boolean")),
    )
    .withColumn("amount", F.col("amount").cast("decimal(15,2)"))
    .withColumn("fee_amount", F.col("fee_amount").cast("decimal(15,2)"))
    .withColumn("latitude", F.col("latitude").cast("decimal(10,6)"))
    .withColumn("longitude", F.col("longitude").cast("decimal(10,6)"))
    .withColumn("risk_score", F.col("risk_score").cast("decimal(4,3)"))
    .withColumn("transaction_timestamp_utc", F.to_timestamp("transaction_timestamp"))
    .withColumn("completed_timestamp_utc", F.to_timestamp("completed_timestamp"))
    .withColumn("created_at", F.to_timestamp("created_at"))
    .drop("transaction_timestamp", "completed_timestamp")
)

silver_base_df = silver_base_df.select(
    "transaction_id",
    "sender_account_id",
    "receiver_id",
    "receiver_type",
    "transaction_type",
    "payment_method_id",
    "amount",
    "currency",
    "fee_amount",
    "status",
    "device_id",
    "ip_address",
    "latitude",
    "longitude",
    "transaction_timestamp_utc",
    "completed_timestamp_utc",
    "risk_score",
    "is_flagged",
    "fraud_pattern",
    "created_at",
)

silver_base_df = silver_base_df.cache()

display(silver_base_df.limit(10))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5) Build Critical Quarantine Candidates

# COMMAND ----------

bronze_accounts = spark.table(accounts_table)
bronze_devices = spark.table(devices_table)
bronze_payment_methods = spark.table(payment_methods_table)
bronze_merchants = spark.table(merchants_table)

allowed_statuses = ["Success", "Failed", "Pending", "Reversed"]
allowed_transaction_types = [
    "P2P_Transfer",
    "Merchant_Payment",
    "Deposit",
    "Withdrawal",
    "Bill_Payment",
]
allowed_currencies = ["EGP", "SAR", "AED", "KWD", "QAR"]
allowed_fraud_patterns = ["velocity", "amount", "time", "new_device", "cross_border"]
allowed_receiver_types = ["account", "merchant", "self"]

txn_001_fail = F.col("transaction_id").isNull()
txn_024_fail = F.col("sender_account_id").isNull()
txn_025_fail = F.col("device_id").isNull()
txn_026_fail = F.col("payment_method_id").isNull()
txn_004_fail = F.col("status").isNull() | (~F.col("status").isin(allowed_statuses))
txn_005_fail = F.col("transaction_type").isNull() | (~F.col("transaction_type").isin(allowed_transaction_types))
txn_006_fail = F.col("currency").isNull() | (~F.col("currency").isin(allowed_currencies))
txn_007_fail = F.col("amount").isNull() | (F.col("amount") <= F.lit(0))
txn_008_fail = F.col("fee_amount").isNull() | (F.col("fee_amount") < F.lit(0))
txn_011_fail = (F.col("is_flagged") == F.lit(True)) & F.col("fraud_pattern").isNull()
txn_012_fail = F.col("fraud_pattern").isNotNull() & (~F.col("fraud_pattern").isin(allowed_fraud_patterns))
txn_013_fail = F.col("receiver_type").isNull() | (~F.col("receiver_type").isin(allowed_receiver_types))
txn_014_fail = (F.col("receiver_type") == F.lit("self")) & F.col("receiver_id").isNotNull()
txn_015_fail = F.col("receiver_type").isin("account", "merchant") & F.col("receiver_id").isNull()
txn_016_fail = (F.col("transaction_type") == F.lit("Merchant_Payment")) & (F.col("receiver_type") != F.lit("merchant"))
txn_017_fail = (F.col("transaction_type") == F.lit("P2P_Transfer")) & (F.col("receiver_type") != F.lit("account"))
txn_027_fail = (
    F.col("transaction_type").isin("Deposit", "Withdrawal", "Bill_Payment")
    & (
        (F.col("receiver_type") != F.lit("self"))
        | F.col("receiver_id").isNotNull()
    )
)

any_business_rule_failure = (
    txn_001_fail
    | txn_024_fail
    | txn_025_fail
    | txn_026_fail
    | txn_004_fail
    | txn_005_fail
    | txn_006_fail
    | txn_007_fail
    | txn_008_fail
    | txn_011_fail
    | txn_012_fail
    | txn_013_fail
    | txn_014_fail
    | txn_015_fail
    | txn_016_fail
    | txn_017_fail
    | txn_027_fail
)

quarantine_rules_df = silver_base_df.filter(any_business_rule_failure).cache()
clean_base_df = silver_base_df.filter(~any_business_rule_failure).cache()

txn_003_orphans = (
    clean_base_df
    .filter(F.col("sender_account_id").isNotNull())
    .alias("t")
    .join(
        bronze_accounts.alias("a"),
        F.col("t.sender_account_id") == F.col("a.account_id"),
        "leftanti",
    )
)

txn_020_orphans = (
    clean_base_df
    .filter(F.col("device_id").isNotNull())
    .alias("t")
    .join(
        bronze_devices.alias("d"),
        F.col("t.device_id") == F.col("d.device_id"),
        "leftanti",
    )
)

txn_021_orphans = (
    clean_base_df
    .filter(F.col("payment_method_id").isNotNull())
    .alias("t")
    .join(
        bronze_payment_methods.alias("p"),
        F.col("t.payment_method_id") == F.col("p.payment_method_id"),
        "leftanti",
    )
)

receiver_account_orphans = (
    clean_base_df
    .filter(F.col("receiver_type") == F.lit("account"))
    .filter(F.col("receiver_id").isNotNull())
    .alias("t")
    .join(
        bronze_accounts.alias("a"),
        F.col("t.receiver_id") == F.col("a.account_id"),
        "leftanti",
    )
)

receiver_merchant_orphans = (
    clean_base_df
    .filter(F.col("receiver_type") == F.lit("merchant"))
    .filter(F.col("receiver_id").isNotNull())
    .alias("t")
    .join(
        bronze_merchants.alias("m"),
        F.col("t.receiver_id") == F.col("m.merchant_id"),
        "leftanti",
    )
)

quarantine_fk_df = (
    txn_003_orphans
    .unionByName(txn_020_orphans)
    .unionByName(txn_021_orphans)
    .unionByName(receiver_account_orphans)
    .unionByName(receiver_merchant_orphans)
    .dropDuplicates()
    .cache()
)

valid_candidate_df = clean_base_df.join(
    quarantine_fk_df.select("transaction_id").dropDuplicates(),
    on="transaction_id",
    how="leftanti",
).cache()

quarantine_candidate_df = (
    quarantine_rules_df
    .unionByName(quarantine_fk_df)
    .dropDuplicates()
    .cache()
)

critical_rule_count = quarantine_rules_df.count()
critical_fk_count = quarantine_fk_df.count()
quarantine_candidate_count = quarantine_candidate_df.count()
valid_candidate_count = valid_candidate_df.count()

print(f"Critical business-rule quarantine rows: {critical_rule_count:,}")
print(f"Critical FK-orphan quarantine rows:     {critical_fk_count:,}")
print(f"Unique quarantine candidate rows:       {quarantine_candidate_count:,}")
print(f"Valid candidates after critical checks: {valid_candidate_count:,}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6) Build Quarantine Audit Rows

# COMMAND ----------

from pyspark.sql import DataFrame


def build_quarantine_audit(
    df: DataFrame,
    dq_rule_id: str,
    dq_reason: str,
) -> DataFrame:
    df_with_audit_id = df.withColumn("_audit_row_id", F.monotonically_increasing_id())

    return df_with_audit_id.select(
        F.lit("transactions").alias("entity_name"),
        F.to_date(F.lit(batch_date)).alias("batch_date"),
        F.when(
            F.col("transaction_id").isNull(),
            F.concat(F.lit("__null_txn__:"), F.col("_audit_row_id").cast("string")),
        ).otherwise(F.col("transaction_id").cast("string")).alias("source_record_id"),
        F.lit(dq_rule_id).alias("dq_rule_id"),
        F.lit(dq_reason).alias("dq_reason"),
        F.current_timestamp().alias("quarantined_at"),
    )


critical_quarantine_specs = [
    (silver_base_df.filter(txn_001_fail), "TXN-001", "transaction_id is null"),
    (silver_base_df.filter(txn_024_fail), "TXN-024", "sender_account_id is null"),
    (silver_base_df.filter(txn_025_fail), "TXN-025", "device_id is null"),
    (silver_base_df.filter(txn_026_fail), "TXN-026", "payment_method_id is null"),
    (silver_base_df.filter(txn_004_fail), "TXN-004", "status is invalid"),
    (silver_base_df.filter(txn_005_fail), "TXN-005", "transaction_type is invalid"),
    (silver_base_df.filter(txn_006_fail), "TXN-006", "currency is invalid"),
    (silver_base_df.filter(txn_007_fail), "TXN-007", "amount must be greater than zero"),
    (silver_base_df.filter(txn_008_fail), "TXN-008", "fee_amount must be zero or positive"),
    (silver_base_df.filter(txn_011_fail), "TXN-011", "flagged transaction must have fraud_pattern"),
    (silver_base_df.filter(txn_012_fail), "TXN-012", "fraud_pattern is invalid"),
    (silver_base_df.filter(txn_013_fail), "TXN-013", "receiver_type is invalid"),
    (silver_base_df.filter(txn_014_fail), "TXN-014", "receiver_id must be null when receiver_type is self"),
    (silver_base_df.filter(txn_015_fail), "TXN-015", "receiver_id is required for account or merchant receiver_type"),
    (silver_base_df.filter(txn_016_fail), "TXN-016", "Merchant_Payment must use receiver_type merchant"),
    (silver_base_df.filter(txn_017_fail), "TXN-017", "P2P_Transfer must use receiver_type account"),
    (silver_base_df.filter(txn_027_fail), "TXN-027", "Deposit, Withdrawal, and Bill_Payment must use receiver_type self with null receiver_id"),
    (txn_003_orphans, "TXN-003", "sender_account_id not found in accounts"),
    (txn_020_orphans, "TXN-020", "device_id not found in devices"),
    (txn_021_orphans, "TXN-021", "payment_method_id not found in payment_methods"),
    (receiver_account_orphans, "TXN-022", "receiver_id not found in accounts when receiver_type is account"),
    (receiver_merchant_orphans, "TXN-023", "receiver_id not found in merchants when receiver_type is merchant"),
]

quarantine_audit_df = None
for failed_df, dq_rule_id, dq_reason in critical_quarantine_specs:
    audit_slice_df = build_quarantine_audit(failed_df, dq_rule_id, dq_reason)
    quarantine_audit_df = (
        audit_slice_df
        if quarantine_audit_df is None
        else quarantine_audit_df.unionByName(audit_slice_df)
    )

quarantine_audit_df = quarantine_audit_df.dropDuplicates(
    ["entity_name", "batch_date", "source_record_id", "dq_rule_id"]
).cache()

display(quarantine_audit_df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7) Apply Warning / Correction Logic

# COMMAND ----------

warning_corrected_df = (
    valid_candidate_df
    .withColumn(
        "_txn_009_invalid",
        F.col("completed_timestamp_utc").isNotNull()
        & (F.col("completed_timestamp_utc") < F.col("transaction_timestamp_utc")),
    )
    .withColumn(
        "completed_timestamp_utc",
        F.when(
            F.col("_txn_009_invalid"),
            F.lit(None).cast("timestamp"),
        ).otherwise(F.col("completed_timestamp_utc")),
    )
)

warning_issue_array = F.array_remove(
    F.array(
        F.when(
            F.col("_txn_009_invalid"),
            F.lit("TXN-009: completed timestamp corrected to NULL"),
        ),
        F.when(
            F.col("risk_score").isNull() | (~F.col("risk_score").between(F.lit(0.000), F.lit(1.000))),
            F.lit("TXN-010: risk_score outside expected range"),
        ),
        F.when(
            F.col("latitude").isNull() | (~F.col("latitude").between(F.lit(22.0), F.lit(32.0))),
            F.lit("TXN-018: latitude outside MENA bounds"),
        ),
        F.when(
            F.col("longitude").isNull() | (~F.col("longitude").between(F.lit(29.0), F.lit(56.0))),
            F.lit("TXN-019: longitude outside MENA bounds"),
        ),
    ),
    F.lit(None),
)

warning_corrected_df = (
    warning_corrected_df
    .withColumn("_dq_issues", F.concat_ws("|", warning_issue_array))
    .withColumn("_dq_issues",
        F.when(F.col("_dq_issues") == "", None).otherwise(F.col("_dq_issues"))
    )
    .withColumn("_dq_valid",
        F.when(F.col("_dq_issues").isNull(), True).otherwise(False)
    )
    .drop("_txn_009_invalid")
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8) Deduplicate Valid Transactions

# COMMAND ----------

from pyspark.sql.window import Window

dedup_window = Window.partitionBy("transaction_id").orderBy(
    F.col("transaction_timestamp_utc").asc(),
    F.col("created_at").asc_nulls_last(),
)

silver_final_df = (
    warning_corrected_df
    .withColumn("_row_num", F.row_number().over(dedup_window))
    .filter(F.col("_row_num") == 1)
    .drop("_row_num")
).cache()

silver_final_count = silver_final_df.count()
print(f"Silver rows after dedup: {silver_final_count:,}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9) Write Quarantine Output

# COMMAND ----------

if spark.catalog.tableExists(quarantine_table):
    spark.sql(
        f"""
        DELETE FROM {quarantine_table}
        WHERE entity_name = 'transactions'
          AND batch_date = DATE '{batch_date}'
        """
    )

quarantine_audit_df.write.format("delta").mode("append").saveAsTable(quarantine_table)

quarantine_audit_count = quarantine_audit_df.count()
print(f"Quarantine rows written: {quarantine_audit_count:,}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 10) Write DQ Metrics

# COMMAND ----------

top_failed_rules = ", ".join(
    [
        f"{row['dq_rule_id']}:{row['rule_count']}"
        for row in (
            quarantine_audit_df.groupBy("dq_rule_id")
            .count()
            .withColumnRenamed("count", "rule_count")
            .orderBy(F.col("rule_count").desc(), F.col("dq_rule_id").asc())
            .limit(5)
            .collect()
        )
    ]
)

null_rate_critical_fields = (
    silver_base_df
    .select(
        F.avg(
            F.when(
                F.col("transaction_id").isNull()
                | F.col("sender_account_id").isNull()
                | F.col("device_id").isNull()
                | F.col("payment_method_id").isNull(),
                F.lit(1.0),
            ).otherwise(F.lit(0.0))
        ).alias("null_rate")
    )
    .first()["null_rate"]
)

quarantine_row_count = quarantine_candidate_count
quarantine_rate = float(quarantine_row_count / bronze_count) if bronze_count else 0.0

dq_metrics_df = spark.createDataFrame(
    [
        (
            "transactions",
            datetime.strptime(batch_date, "%Y-%m-%d").date(),
            int(bronze_count),
            int(quarantine_row_count),
            float(quarantine_rate),
            top_failed_rules,
            float(null_rate_critical_fields or 0.0),
        )
    ],
    [
        "entity_name",
        "batch_date",
        "total_rows",
        "quarantine_count",
        "quarantine_rate",
        "top_failed_rules",
        "null_rate_critical_fields",
    ],
)

if spark.catalog.tableExists(metrics_table):
    spark.sql(
        f"""
        DELETE FROM {metrics_table}
        WHERE entity_name = 'transactions'
          AND batch_date = DATE '{batch_date}'
        """
    )

dq_metrics_df.write.format("delta").mode("append").saveAsTable(metrics_table)

display(dq_metrics_df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 11) Write Silver Output

# COMMAND ----------

from delta.tables import DeltaTable

target_exists = spark.catalog.tableExists(target_table)

if write_strategy == "overwrite" or not target_exists:
    (
        silver_final_df.write
        .format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(target_table)
    )
else:
    delta_target = DeltaTable.forName(spark, target_table)
    (
        delta_target.alias("t")
        .merge(
            silver_final_df.alias("s"),
            "t.transaction_id = s.transaction_id",
        )
        .whenMatchedUpdateAll()
        .whenNotMatchedInsertAll()
        .execute()
    )

target_row_count = spark.table(target_table).count()
print(f"Silver rows available in target: {target_row_count:,}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 12) Validation Summary

# COMMAND ----------

warning_row_count = silver_final_df.filter(
    F.col("_dq_issues").isNotNull()
).count()
distinct_transaction_id_count = silver_final_df.select("transaction_id").distinct().count()

summary_rows = [
    ("bronze_scoped_rows", bronze_count),
    ("critical_quarantine_rows", quarantine_row_count),
    ("quarantine_audit_rows", quarantine_audit_count),
    ("silver_valid_rows", silver_final_count),
    ("warning_rows", warning_row_count),
    ("distinct_transaction_ids", distinct_transaction_id_count),
]

summary_df = spark.createDataFrame(summary_rows, ["metric_name", "metric_value"])
display(summary_df)

if silver_final_count != distinct_transaction_id_count:
    raise RuntimeError("Dedup validation failed: transaction_id is not unique in Silver output.")

print("Silver transactions pipeline completed successfully.")
