import csv
import os
import sys
from pathlib import Path

import psycopg
from psycopg import sql

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
RAW_DATA_DIR = REPO_ROOT / "data-generator" / "raw_data"
ENV_FILE = REPO_ROOT / ".env"

REQUIRED_ENV_VARS = [
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_DATABASE",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
]

ENTITIES = {
    "users": ("source", "users"),
    "merchants": ("source", "merchants"),
    "accounts": ("source", "accounts"),
    "devices": ("source", "devices"),
    "payment_methods": ("source", "payment_methods"),
    "kyc_records": ("source", "kyc_records"),
    "transactions": ("source", "transactions"),
}


def load_env_file(env_file: Path) -> None:
    if not env_file.exists():
        return

    with open(env_file, "r", encoding="utf-8") as file_obj:
        for raw_line in file_obj:
            line = raw_line.strip()

            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            if key and key not in os.environ:
                os.environ[key] = value


def count_csv_rows(file_path: Path) -> int:
    with open(file_path, "r", encoding="utf-8", newline="") as file_obj:
        reader = csv.reader(file_obj)
        next(reader, None)
        return sum(1 for _ in reader)


def get_required_env_vars() -> dict[str, str]:
    config = {name: os.getenv(name) for name in REQUIRED_ENV_VARS}
    missing = [name for name, value in config.items() if not value]

    if missing:
        missing_list = ", ".join(missing)
        raise ValueError(f"Missing required environment variables: {missing_list}")

    return config


def get_connection() -> psycopg.Connection:
    config = get_required_env_vars()
    return psycopg.connect(
        host=config["POSTGRES_HOST"],
        port=config["POSTGRES_PORT"],
        dbname=config["POSTGRES_DATABASE"],
        user=config["POSTGRES_USER"],
        password=config["POSTGRES_PASSWORD"],
    )


def load_table(cursor: psycopg.Cursor, schema_name: str, table_name: str, file_path: Path) -> None:
    if not file_path.exists():
        raise FileNotFoundError(f"CSV file not found: {file_path}")

    truncate_stmt = sql.SQL("TRUNCATE {}.{}").format(
        sql.Identifier(schema_name),
        sql.Identifier(table_name),
    )
    cursor.execute(truncate_stmt)

    copy_stmt = sql.SQL(
        """
        COPY {}.{}
        FROM STDIN
        WITH (FORMAT CSV, HEADER TRUE)
        """
    ).format(
        sql.Identifier(schema_name),
        sql.Identifier(table_name),
    )

    with open(file_path, "r", encoding="utf-8") as file_obj:
        with cursor.copy(copy_stmt) as copy:
            while data := file_obj.read(8192):
                copy.write(data)

    count_stmt = sql.SQL("SELECT COUNT(*) FROM {}.{}").format(
        sql.Identifier(schema_name),
        sql.Identifier(table_name),
    )
    cursor.execute(count_stmt)
    db_count = cursor.fetchone()[0]
    csv_count = count_csv_rows(file_path)

    if db_count != csv_count:
        raise ValueError(
            f"Row count mismatch for {schema_name}.{table_name}: "
            f"expected {csv_count:,} but got {db_count:,}"
        )

    print(f"  OK {schema_name}.{table_name}: {db_count:,} rows loaded")


if __name__ == "__main__":
    print("==================================================")
    print("        PostgreSQL Bulk Loader (FinTech)          ")
    print("==================================================")

    conn = None
    failed: list[str] = []

    try:
        load_env_file(ENV_FILE)
        conn = get_connection()
        print("[+] Successfully connected to PostgreSQL.\n")

        for entity_name, (schema_name, table_name) in ENTITIES.items():
            file_path = RAW_DATA_DIR / f"{entity_name}.csv"

            try:
                with conn.cursor() as cursor:
                    load_table(cursor, schema_name, table_name, file_path)
                conn.commit()
            except Exception as exc:
                conn.rollback()
                failed.append(entity_name)
                print(f"  FAIL {schema_name}.{table_name}: {exc}")

    finally:
        if conn is not None:
            conn.close()

    print("\n==================================================")
    print(f"  Result: {len(ENTITIES) - len(failed)}/{len(ENTITIES)} tables loaded")
    if failed:
        print(f"  Failed: {failed}")
    print("==================================================")

    if failed:
        sys.exit(1)
