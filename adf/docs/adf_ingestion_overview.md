# ADF Ingestion Overview

This stage ingests data from Azure Database for PostgreSQL Flexible Server into ADLS Gen2 raw landing using Azure Data Factory.

## Implemented Pipeline

- Pipeline: `PL_Load_All_Entities_Full`
- Source dataset: `DS_PG_Source_Table`
- Sink dataset: `DS_ADLS_Raw_CSV`

## Source Entities

- users
- merchants
- accounts
- devices
- payment_methods
- kyc_records
- transactions

## Landing Path Pattern

raw/landing/<entity>/full/run_date=<yyyy-MM-dd>/run_id=<pipeline_run_id>/<entity>.csv

## Design Notes

- Source and sink datasets are parameterized.
- The pipeline uses a ForEach activity to loop over multiple entities.
- Each pipeline run is isolated using `run_id`.
- Raw landing stores source extracts without business transformations.

## Control Tables
The ingestion_control table is actively used by the incremental pipeline to store the latest successful watermark.

The ingestion_audit table is currently used as a lightweight/manual run-history evidence table in Stage 2. Full automated audit logging from ADF is intentionally deferred to avoid over-engineering this phase.