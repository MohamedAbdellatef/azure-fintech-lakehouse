# ADF Ingestion Layer

This folder contains the Azure Data Factory assets used for this project:

`Azure Database for PostgreSQL -> ADF -> ADLS Gen2 raw landing`

## Scope of ingestion

Ingestion covers: 

- extract source data from Azure Database for PostgreSQL
- land raw files in ADLS Gen2
- validate source-to-landing row counts
- prove one small watermark-based incremental pattern

This stage does not include Bronze, Silver, dbt, or business transformations.

## What Is Inside

- `linked_services/`: ADF linked service exports for PostgreSQL and ADLS
- `datasets/`: parameterized source and sink datasets
- `pipelines/`: reusable full-load and incremental pipeline exports
- `docs/`: landing contract, ingestion overview, and failure handling notes
- `evidence/`: validation files and screenshots for this stage

## Pipelines

- `pl_load_all_entities_full.json`: reusable baseline full-load pipeline using `ForEach` across all source entities
- `pl_load_entity_incremental.json`: reusable watermark-based incremental pipeline for one entity at a time

## Full vs Incremental

- Full load establishes the raw landing baseline for all source tables
- Incremental load copies only rows newer than the last successful watermark
- Ingestion uses full load for all entities and one small incremental pilot to prove the watermark logic

## Evidence Location

- `evidence/source_to_landing_counts.md`: full-load source-to-landing count validation
- `evidence/incremental_validation.md`: incremental pilot validation, including no-new-rows behavior
- `evidence/screenshots/`: ADF and ADLS screenshots captured for ingestion proof

## Status

Ingestion implementation completed.