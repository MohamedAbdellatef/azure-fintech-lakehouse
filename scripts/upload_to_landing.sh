#!/bin/bash
# scripts/upload_to_landing.sh
# Usage: ./scripts/upload_to_landing.sh <storage_account_name> [source_dir]

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <storage_account_name> [source_dir]"
  echo "Example: $0 stfintechlakehousedev data-generator/raw_data"
  exit 1
fi

if ! command -v az >/dev/null 2>&1; then
  echo "Azure CLI (az) is not installed or not in PATH."
  exit 1
fi

if ! az account show >/dev/null 2>&1; then
  echo "Azure CLI is not logged in. Run: az login"
  exit 1
fi

STORAGE_ACCOUNT="$1"
SOURCE_DIR="${2:-data-generator/raw_data}"

ENTITIES=("users" "accounts" "transactions" "merchants" "devices" "payment_methods" "kyc_records")

for entity in "${ENTITIES[@]}"; do
  src_file="${SOURCE_DIR}/${entity}.csv"
  if [[ ! -f "$src_file" ]]; then
    echo "Missing source file: $src_file"
    exit 1
  fi

  echo "Uploading ${src_file} -> landing/${entity}/${entity}.csv"
  az storage blob upload \
    --auth-mode login \
    --account-name "$STORAGE_ACCOUNT" \
    --container-name "landing" \
    --name "${entity}/${entity}.csv" \
    --file "$src_file" \
    --overwrite
done

echo "Upload completed."
