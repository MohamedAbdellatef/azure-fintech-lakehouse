# Databricks notebook source
# MAGIC %md
# MAGIC # Silver Users
# MAGIC
# MAGIC Cleanses Bronze users into Silver by applying:
# MAGIC - incremental scope filtering
# MAGIC - critical-rule quarantine
# MAGIC - warning logic
# MAGIC - idempotent writes to `silver.users` and `audit.dq_quarantine`

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1) Runtime Configuration

# COMMAND ----------

from datetime import datetime, timedelta

dbutils.widgets.text(
    "source_table",
    "hive_metastore.bronze.users",
    "Source Table",
)
dbutils.widgets.text(
    "target_table",
    "hive_metastore.silver.users",
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
        "Widget 'batch_cutoff_ts' must be a valid ISO timestamp, e.g. 2026-03-17T08:30:00."
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
# MAGIC ## 2) Validate Source and Audit Tables

# COMMAND ----------

table_parts = source_table.split(".")
if len(table_parts) < 2:
    raise ValueError(
        "Widget 'source_table' should be schema-qualified or catalog.schema-qualified."
    )

audit_namespace = ".".join(quarantine_table.split(".")[:-1])
metrics_table = f"{audit_namespace}.dq_metrics"

required_tables = {
    "users": source_table,
}

for entity_name, table_name in required_tables.items():
    if not spark.catalog.tableExists(table_name):
        raise RuntimeError(f"Required table for '{entity_name}' does not exist: {table_name}")

print("Required Bronze source table is available.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3) Read Bronze Scope

# COMMAND ----------

from pyspark.sql import functions as F

cutoff_literal = F.lit(batch_cutoff_dt.strftime("%Y-%m-%d %H:%M:%S")).cast("timestamp")
lookback_literal = F.lit(lookback_start_dt.strftime("%Y-%m-%d %H:%M:%S")).cast("timestamp")

bronze_df = (
    spark.table(source_table)
    .withColumn("_scope_updated_at", F.to_timestamp("updated_at"))
    .filter(F.col("_scope_updated_at").isNotNull())
    .filter(F.col("_scope_updated_at") <= cutoff_literal)
    .filter(F.col("_scope_updated_at") >= lookback_literal)
    .drop("_scope_updated_at")
    .cache()
)

bronze_count = bronze_df.count()
if bronze_count == 0:
    print("No Bronze users in scope. Exiting gracefully.")
    dbutils.notebook.exit("NO_DATA")

print(f"Scoped Bronze users: {bronze_count:,}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4) Normalize and Cast to Silver Contract

# COMMAND ----------

string_columns = [
    "user_id",
    "first_name",
    "last_name",
    "email",
    "phone_number",
    "gender",
    "country",
    "city",
    "preferred_currency",
    "kyc_status",
    "user_tier",
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
    .withColumn("kyc_status", F.lower(F.col("kyc_status")))
    .withColumn("user_tier", F.lower(F.col("user_tier")))
    .withColumn("country", F.upper(F.col("country")))
    .withColumn("gender", F.upper(F.col("gender")))
    .withColumn("preferred_currency", F.upper(F.col("preferred_currency")))
    .withColumn(
        "is_active",
        F.when(F.lower(F.trim(F.col("is_active"))).isin("true", "1", "yes"), F.lit(True))
        .when(F.lower(F.trim(F.col("is_active"))).isin("false", "0", "no"), F.lit(False))
        .otherwise(F.lit(None).cast("boolean")),
    )
    .withColumn("date_of_birth", F.to_date("date_of_birth"))
    .withColumn("registration_date", F.to_timestamp("registration_date"))
    .withColumn("created_at", F.to_timestamp("created_at"))
    .withColumn("updated_at", F.to_timestamp("updated_at"))
)

silver_base_df = silver_base_df.select(
    "user_id",
    "first_name",
    "last_name",
    "email",
    "phone_number",
    "date_of_birth",
    "gender",
    "country",
    "city",
    "preferred_currency",
    "kyc_status",
    "user_tier",
    "is_active",
    "registration_date",
    "created_at",
    "updated_at",
)

silver_base_df = silver_base_df.cache()

display(silver_base_df.limit(10))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5) Build Critical Quarantine Candidates

# COMMAND ----------

from pyspark.sql.window import Window

allowed_countries = ["EG", "SA", "AE", "KW", "QA"]
allowed_status = ["verified", "pending", "rejected"]
allowed_tiers = ["basic", "silver", "gold", "platinum"]

user_window = Window.partitionBy("user_id")
silver_base_with_counts_df = silver_base_df.withColumn(
    "_user_id_count",
    F.count("user_id").over(user_window),
)

usr_001_null_fail = F.col("user_id").isNull()
usr_001_duplicate_fail = F.col("user_id").isNotNull() & (F.col("_user_id_count") > 1)
usr_005_fail = F.col("country").isNull() | (~F.col("country").isin(allowed_countries))
usr_006_fail = F.col("kyc_status").isNull() | (~F.col("kyc_status").isin(allowed_status))
usr_007_fail = F.col("user_tier").isNull() | (~F.col("user_tier").isin(allowed_tiers))

any_critical_failure = (
    usr_001_null_fail
    | usr_001_duplicate_fail
    | usr_005_fail
    | usr_006_fail
    | usr_007_fail
)

quarantine_rules_df = (
    silver_base_with_counts_df
    .filter(any_critical_failure)
    .drop("_user_id_count")
    .dropDuplicates()
    .cache()
)

clean_base_df = (
    silver_base_with_counts_df
    .filter(~any_critical_failure)
    .drop("_user_id_count")
    .cache()
)

critical_rule_count = quarantine_rules_df.count()
valid_candidate_count = clean_base_df.count()

print(f"Critical business-rule quarantine rows: {critical_rule_count:,}")
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
        F.lit("users").alias("entity_name"),
        F.to_date(F.lit(batch_date)).alias("batch_date"),
        F.when(
            F.col("user_id").isNull(),
            F.concat(F.lit("__null_user__:"), F.col("_audit_row_id").cast("string")),
        ).otherwise(F.col("user_id").cast("string")).alias("source_record_id"),
        F.lit(dq_rule_id).alias("dq_rule_id"),
        F.lit(dq_reason).alias("dq_reason"),
        F.current_timestamp().alias("quarantined_at"),
    )


critical_quarantine_specs = [
    (
        silver_base_with_counts_df.filter(usr_001_null_fail).drop("_user_id_count"),
        "USR-001",
        "user_id is null",
    ),
    (
        silver_base_with_counts_df.filter(usr_001_duplicate_fail).drop("_user_id_count"),
        "USR-001",
        "user_id is duplicated",
    ),
    (
        silver_base_with_counts_df.filter(usr_005_fail).drop("_user_id_count"),
        "USR-005",
        "country is invalid",
    ),
    (
        silver_base_with_counts_df.filter(usr_006_fail).drop("_user_id_count"),
        "USR-006",
        "kyc_status is invalid",
    ),
    (
        silver_base_with_counts_df.filter(usr_007_fail).drop("_user_id_count"),
        "USR-007",
        "user_tier is invalid",
    ),
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
# MAGIC ## 7) Apply Warning Logic

# COMMAND ----------

email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"

warning_corrected_df = (
    clean_base_df
    .withColumn(
        "_usr_002_warn",
        F.col("email").isNotNull() & (~F.col("email").rlike(email_regex)),
    )
    .withColumn(
        "_usr_003_warn",
        F.col("email").isNull(),
    )
    .withColumn(
        "_usr_004_warn",
        F.col("phone_number").isNull(),
    )
)

warning_issue_array = F.array_remove(
    F.array(
        F.when(F.col("_usr_002_warn"), F.lit("USR-002: invalid email format")),
        F.when(F.col("_usr_003_warn"), F.lit("USR-003: email is null")),
        F.when(F.col("_usr_004_warn"), F.lit("USR-004: phone_number is null")),
    ),
    F.lit(None),
)

warning_corrected_df = (
    warning_corrected_df
    .withColumn("_dq_issues", F.concat_ws("|", warning_issue_array))
    .withColumn(
        "_dq_issues",
        F.when(F.col("_dq_issues") == "", None).otherwise(F.col("_dq_issues")),
    )
    .withColumn(
        "_dq_valid",
        F.when(F.col("_dq_issues").isNull(), True).otherwise(False),
    )
    .drop("_usr_002_warn", "_usr_003_warn", "_usr_004_warn")
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8) Finalize Silver Users

# COMMAND ----------

silver_final_df = warning_corrected_df.select(
    "user_id",
    "first_name",
    "last_name",
    "email",
    "phone_number",
    "date_of_birth",
    "gender",
    "country",
    "city",
    "preferred_currency",
    "kyc_status",
    "user_tier",
    "is_active",
    "registration_date",
    "created_at",
    "updated_at",
    "_dq_valid",
    "_dq_issues",
).cache()

silver_final_count = silver_final_df.count()
print(f"Silver rows ready to write: {silver_final_count:,}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9) Write Quarantine Output

# COMMAND ----------

if spark.catalog.tableExists(quarantine_table):
    spark.sql(
        f"""
        DELETE FROM {quarantine_table}
        WHERE entity_name = 'users'
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
                F.col("user_id").isNull()
                | F.col("country").isNull()
                | F.col("kyc_status").isNull()
                | F.col("user_tier").isNull(),
                F.lit(1.0),
            ).otherwise(F.lit(0.0))
        ).alias("null_rate")
    )
    .first()["null_rate"]
)

quarantine_row_count = critical_rule_count
quarantine_rate = float(quarantine_row_count / bronze_count) if bronze_count else 0.0

dq_metrics_df = spark.createDataFrame(
    [
        (
            "users",
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
        WHERE entity_name = 'users'
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
            "t.user_id = s.user_id",
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
distinct_user_id_count = silver_final_df.select("user_id").distinct().count()

summary_rows = [
    ("bronze_scoped_rows", bronze_count),
    ("critical_quarantine_rows", quarantine_row_count),
    ("quarantine_audit_rows", quarantine_audit_count),
    ("silver_valid_rows", silver_final_count),
    ("warning_rows", warning_row_count),
    ("distinct_user_ids", distinct_user_id_count),
]

summary_df = spark.createDataFrame(summary_rows, ["metric_name", "metric_value"])
display(summary_df)

if silver_final_count != distinct_user_id_count:
    raise RuntimeError("Validation failed: user_id is not unique in Silver output.")

print("Silver users pipeline completed successfully.")
