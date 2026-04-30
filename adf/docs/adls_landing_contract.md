# ADLS Raw Landing Contract

The raw landing zone stores source extracts from PostgreSQL without business transformations.

## Folder Structure

raw/landing/<entity>/<load_type>/run_date=<yyyy-MM-dd>/run_id=<run_id>/<file_name>

## Rules

- One folder per entity.
- Full and incremental loads are stored separately.
- Each pipeline execution is isolated by `run_id`.
- Raw files should not be manually edited.
- Transformations are handled later in Bronze/Silver.
- The raw layer is treated as immutable landing evidence.