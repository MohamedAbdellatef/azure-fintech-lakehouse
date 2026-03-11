# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze Ingestion (All Entities)
# MAGIC
# MAGIC Loads raw CSVs from landing into Bronze Delta tables with minimal transformation.
# MAGIC Bronze keeps raw fidelity and only adds technical ingestion metadata.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1) Runtime Configuration

# COMMAND ----------

dbutils.widgets.text("source_root", "/mnt/landing", "Landing Root")
dbutils.widgets.text("bronze_catalog", "hive_metastore", "Bronze Catalog")
dbutils.widgets.text("bronze_schema", "bronze", "Bronze Schema")
dbutils.widgets.dropdown("write_mode", "overwrite", ["overwrite", "append"], "Write Mode")

source_root = dbutils.widgets.get("source_root").strip().rstrip("/")
bronze_catalog = dbutils.widgets.get("bronze_catalog").strip()
bronze_schema = dbutils.widgets.get("bronze_schema").strip()
write_mode = dbutils.widgets.get("write_mode").strip().lower()

if not source_root:
    raise ValueError("Widget 'source_root' cannot be empty.")
if not bronze_schema:
    raise ValueError("Widget 'bronze_schema' cannot be empty.")
if write_mode not in {"overwrite", "append"}:
    raise ValueError("Widget 'write_mode' must be one of: overwrite, append.")

bronze_namespace = (
    f"{bronze_catalog}.{bronze_schema}" if bronze_catalog else bronze_schema
)

entities = [
    "users",
    "accounts",
    "transactions",
    "merchants",
    "devices",
    "payment_methods",
    "kyc_records",
]

print(f"Source root:  {source_root}")
print(f"Bronze NS:    {bronze_namespace}")
print(f"Write mode:   {write_mode}")
print(f"Entities:     {entities}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2) Validate Bronze Namespace

# COMMAND ----------

try:
    spark.sql(f"DESCRIBE DATABASE EXTENDED {bronze_namespace}")
except Exception as exc:
    raise RuntimeError(
        f"Bronze namespace '{bronze_namespace}' does not exist. "
        "Run 00-setup/create_schemas.py first."
    ) from exc

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3) Ingest Landing CSV -> Bronze Delta

# COMMAND ----------

from pyspark.sql import functions as F

results = []

for entity in entities:
    source_path = f"{source_root}/{entity}"
    target_table = f"{bronze_namespace}.{entity}"

    # Read all CSV files under each entity folder (supports future batch subfolders).
    df_source = (
        spark.read
        .option("header", True)
        .option("inferSchema", False)
        .option("recursiveFileLookup", "true")
        .csv(source_path)
        .withColumn("_ingest_ts", F.current_timestamp())
        .withColumn("_source_file", F.input_file_name())
    )

    source_count = df_source.count()
    if source_count == 0:
        raise RuntimeError(f"No records found for entity '{entity}' at path '{source_path}'.")

    pre_count = 0
    table_exists = spark.catalog.tableExists(target_table)
    if write_mode == "append" and table_exists:
        pre_count = spark.table(target_table).count()

    writer = df_source.write.format("delta").mode(write_mode)
    if write_mode == "overwrite":
        writer = writer.option("overwriteSchema", "true")
    writer.saveAsTable(target_table)

    target_count = spark.table(target_table).count()
    expected_count = source_count if write_mode == "overwrite" else pre_count + source_count
    is_match = expected_count == target_count

    results.append(
        (entity, source_path, target_table, source_count, expected_count, target_count, is_match)
    )
    print(
        f"[{entity}] source_count={source_count:,} expected={expected_count:,} "
        f"target_count={target_count:,} match={is_match}"
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4) Validation Summary

# COMMAND ----------

summary_df = spark.createDataFrame(
    results,
    [
        "entity",
        "source_path",
        "target_table",
        "source_count",
        "expected_target_count",
        "actual_target_count",
        "count_match",
    ],
)

display(summary_df)

mismatch_count = summary_df.filter("count_match = false").count()
if mismatch_count > 0:
    raise RuntimeError(
        f"Bronze validation failed: {mismatch_count} entities have source/target count mismatch."
    )

print("Bronze ingestion validation passed for all entities.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5) Quick Metadata Check

# COMMAND ----------

spark.sql(f"SHOW TABLES IN {bronze_namespace}").show(truncate=False)
