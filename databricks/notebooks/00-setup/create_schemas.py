# Databricks notebook source
# MAGIC %md
# MAGIC # Create Medallion Databases/Schemas
# MAGIC
# MAGIC Run this notebook after `mount_adls.py`.
# MAGIC It creates Bronze, Silver, Gold, and Audit databases with explicit locations.
# MAGIC Each schema is pinned to its container root: `/mnt/<layer>/`.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1) Configuration

# COMMAND ----------

dbutils.widgets.text("catalog", "hive_metastore", "Catalog")
dbutils.widgets.dropdown("show_tables", "true", ["true", "false"], "Show Tables Per DB")

catalog = dbutils.widgets.get("catalog").strip()
show_tables = dbutils.widgets.get("show_tables").strip().lower() == "true"

if not catalog:
    raise ValueError("Widget 'catalog' cannot be empty.")

databases = ["bronze", "silver", "gold", "audit"]

print(f"Catalog:   {catalog}")
print(f"Databases: {databases}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2) Validate Required Mounts

# COMMAND ----------

for db_name in databases:
    mount_path = f"/mnt/{db_name}/"
    try:
        dbutils.fs.ls(mount_path)
        print(f"Mount available: {mount_path}")
    except Exception as exc:
        raise RuntimeError(
            f"Cannot access required mount '{mount_path}'. Run mount_adls.py first."
        ) from exc

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3) Create Databases

# COMMAND ----------

use_catalog_qualified = False
try:
    spark.sql(f"USE CATALOG {catalog}")
    use_catalog_qualified = True
except Exception:
    if catalog.lower() != "hive_metastore":
        raise
    print("Catalog-qualified names are not available; using unqualified names.")


def db_ref(name: str) -> str:
    return f"{catalog}.{name}" if use_catalog_qualified else name


for db_name in databases:
    location = f"/mnt/{db_name}/"
    target_db = db_ref(db_name)
    spark.sql(f"CREATE DATABASE IF NOT EXISTS {target_db} LOCATION '{location}'")
    print(f"Database ready: {target_db} (location: {location})")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4) Verification

# COMMAND ----------

for db_name in databases:
    target_db = db_ref(db_name)
    details_df = spark.sql(f"DESCRIBE DATABASE EXTENDED {target_db}")
    location_row = (
        details_df
        .filter("database_description_item = 'Location'")
        .select("database_description_value")
        .first()
    )
    actual_location = location_row["database_description_value"] if location_row else "UNKNOWN"
    print(f"{target_db}: location={actual_location}")

    if show_tables:
        spark.sql(f"SHOW TABLES IN {target_db}").show(truncate=False)
