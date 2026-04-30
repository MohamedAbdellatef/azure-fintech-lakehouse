# Databricks notebook source
# MAGIC %md
# MAGIC # Mount ADLS Gen2 Containers
# MAGIC
# MAGIC Run once per environment. This notebook mounts Medallion containers and
# MAGIC validates that landing data can be read.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1) Configuration

# COMMAND ----------

dbutils.widgets.text("storage_account", "stfintechlakehousedev", "ADLS Storage Account")
dbutils.widgets.text("secret_scope", "fintech-scope", "Databricks Secret Scope")
dbutils.widgets.text("client_id_secret_key", "sp-client-id", "Client ID Secret Key")
dbutils.widgets.text("client_secret_secret_key", "sp-client-secret", "Client Secret Key")
dbutils.widgets.text("tenant_secret_key", "tenant-id", "Tenant Secret Key")
dbutils.widgets.dropdown("force_remount", "false", ["false", "true"], "Force Remount")

storage_account = dbutils.widgets.get("storage_account").strip()
secret_scope = dbutils.widgets.get("secret_scope").strip()
client_id_secret_key = dbutils.widgets.get("client_id_secret_key").strip()
client_secret_secret_key = dbutils.widgets.get("client_secret_secret_key").strip()
tenant_secret_key = dbutils.widgets.get("tenant_secret_key").strip()
force_remount = dbutils.widgets.get("force_remount").strip().lower() == "true"

if not storage_account:
    raise ValueError("Widget 'storage_account' cannot be empty.")
if not secret_scope:
    raise ValueError("Widget 'secret_scope' cannot be empty.")
if not client_id_secret_key:
    raise ValueError("Widget 'client_id_secret_key' cannot be empty.")
if not client_secret_secret_key:
    raise ValueError("Widget 'client_secret_secret_key' cannot be empty.")
if not tenant_secret_key:
    raise ValueError("Widget 'tenant_secret_key' cannot be empty.")

containers = ["landing", "bronze", "silver", "gold", "audit"]


def read_secret(key: str) -> str:
    try:
        return dbutils.secrets.get(scope=secret_scope, key=key)
    except Exception as exc:
        raise RuntimeError(f"Missing secret '{key}' in scope '{secret_scope}'.") from exc


client_id = read_secret(client_id_secret_key)
client_secret = read_secret(client_secret_secret_key)
tenant_id = read_secret(tenant_secret_key)

oauth_configs = {
    "fs.azure.account.auth.type": "OAuth",
    "fs.azure.account.oauth.provider.type": "org.apache.hadoop.fs.azurebfs.oauth2.ClientCredsTokenProvider",
    "fs.azure.account.oauth2.client.id": client_id,
    "fs.azure.account.oauth2.client.secret": client_secret,
    "fs.azure.account.oauth2.client.endpoint": f"https://login.microsoftonline.com/{tenant_id}/oauth2/token",
}

print(f"Storage account: {storage_account}")
print(f"Secret scope:    {secret_scope}")
print(f"Containers:      {containers}")
print(f"Force remount:   {force_remount}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2) Mount Containers

# COMMAND ----------

existing_mounts = {m.mountPoint for m in dbutils.fs.mounts()}

for container in containers:
    mount_point = f"/mnt/{container}"
    source_uri = f"abfss://{container}@{storage_account}.dfs.core.windows.net/"

    if mount_point in existing_mounts and not force_remount:
        print(f"Already mounted: {mount_point}")
        continue

    if mount_point in existing_mounts and force_remount:
        print(f"Unmounting: {mount_point}")
        dbutils.fs.unmount(mount_point)

    print(f"Mounting {source_uri} -> {mount_point}")
    try:
        dbutils.fs.mount(
            source=source_uri,
            mount_point=mount_point,
            extra_configs=oauth_configs,
        )
    except Exception as exc:
        raise RuntimeError(
            f"Failed to mount container '{container}' at '{mount_point}'. "
            "Earlier mounts in this run may already be in place."
        ) from exc

dbutils.fs.refreshMounts()
print("Mount operation completed.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3) Verify Mounts

# COMMAND ----------

for container in containers:
    mount_path = f"/mnt/{container}/"
    print(f"\n{mount_path}")
    items = dbutils.fs.ls(mount_path)
    if not items:
        print("  (empty)")
        continue
    for item in items[:10]:
        print(f"  {item.name} ({item.size} bytes)")
    if len(items) > 10:
        print(f"  ... and {len(items) - 10} more items")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4) Smoke Test (Landing Read)

# COMMAND ----------

landing_dirs = [x.path for x in dbutils.fs.ls("/mnt/landing/") if x.isDir()]

if not landing_dirs:
    print("Landing is empty. Upload CSV files first, then rerun this cell.")
else:
    test_path = landing_dirs[0]
    print(f"Testing CSV read from: {test_path}")
    df_test = spark.read.option("header", True).csv(test_path)
    print(f"Columns: {len(df_test.columns)}")
    df_test.printSchema()
    display(df_test.limit(5))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Utility: Unmount All (Manual)

# COMMAND ----------

# Uncomment to reset mounts:
# for container in containers:
#     path = f"/mnt/{container}"
#     if any(m.mountPoint == path for m in dbutils.fs.mounts()):
#         dbutils.fs.unmount(path)
#         print(f"Unmounted {path}")
