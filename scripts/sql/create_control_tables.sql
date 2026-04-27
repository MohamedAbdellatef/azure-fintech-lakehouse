-- ============================================================
-- DDL: fintech_oltp.control
-- Ingestion metadata and audit tables
-- ============================================================

CREATE SCHEMA IF NOT EXISTS control;

-- 1) Drop existing tables
DROP TABLE IF EXISTS control.ingestion_audit;
DROP TABLE IF EXISTS control.ingestion_control;

-- ============================================================
-- Current ingestion state per entity
-- ============================================================

CREATE TABLE control.ingestion_control (
    entity_name        VARCHAR(50) PRIMARY KEY,
    source_schema      VARCHAR(50)  NOT NULL,
    source_table       VARCHAR(100) NOT NULL,

    load_strategy      VARCHAR(30)  NOT NULL DEFAULT 'full_then_incremental',
    watermark_col      VARCHAR(50),

    last_watermark     TIMESTAMP    NOT NULL DEFAULT '1900-01-01 00:00:00',
    is_active          BOOLEAN      NOT NULL DEFAULT TRUE,

    last_run_id        VARCHAR(100),
    last_run_status    VARCHAR(30),
    last_run_ts        TIMESTAMP,
    rows_ingested      BIGINT       DEFAULT 0,

    created_at         TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at         TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_ingestion_control_load_strategy
        CHECK (load_strategy IN ('full_only', 'incremental_only', 'full_then_incremental')),

    CONSTRAINT chk_ingestion_control_watermark_required
        CHECK (
            load_strategy = 'full_only'
            OR watermark_col IS NOT NULL
        ),

    CONSTRAINT chk_ingestion_control_last_run_status
        CHECK (
            last_run_status IS NULL
            OR last_run_status IN ('success', 'failed', 'running', 'skipped')
        ),

    CONSTRAINT chk_ingestion_control_rows_ingested
        CHECK (rows_ingested >= 0)
);

-- ============================================================
-- Ingestion run-level audit history
-- ============================================================

CREATE TABLE control.ingestion_audit (
    audit_id          BIGSERIAL PRIMARY KEY,

    pipeline_run_id  VARCHAR(100) NOT NULL,
    entity_name      VARCHAR(50)  NOT NULL,

    load_type        VARCHAR(20)  NOT NULL,
    source_schema    VARCHAR(50),
    source_table     VARCHAR(100),

    watermark_col    VARCHAR(50),
    old_watermark    TIMESTAMP,
    new_watermark    TIMESTAMP,

    source_count     BIGINT,
    rows_read        BIGINT,
    rows_copied      BIGINT,

    landing_path     TEXT,

    status           VARCHAR(30)  NOT NULL,
    error_message    TEXT,

    started_at       TIMESTAMP,
    ended_at         TIMESTAMP,
    created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_ingestion_audit_load_type
        CHECK (load_type IN ('full', 'incremental')),

    CONSTRAINT chk_ingestion_audit_status
        CHECK (status IN ('success', 'failed', 'running', 'skipped')),

    CONSTRAINT chk_ingestion_audit_source_count
        CHECK (source_count IS NULL OR source_count >= 0),

    CONSTRAINT chk_ingestion_audit_rows_read
        CHECK (rows_read IS NULL OR rows_read >= 0),

    CONSTRAINT chk_ingestion_audit_rows_copied
        CHECK (rows_copied IS NULL OR rows_copied >= 0),

    CONSTRAINT fk_ingestion_audit_entity
        FOREIGN KEY (entity_name)
        REFERENCES control.ingestion_control(entity_name)
);

-- ============================================================
-- Seed ingestion metadata
-- ============================================================

INSERT INTO control.ingestion_control
(
    entity_name,
    source_schema,
    source_table,
    load_strategy,
    watermark_col
)
VALUES
    ('users',           'source', 'users',           'full_then_incremental', 'updated_at'),
    ('merchants',       'source', 'merchants',       'full_then_incremental', 'updated_at'),
    ('accounts',        'source', 'accounts',        'full_then_incremental', 'updated_at'),
    ('devices',         'source', 'devices',         'full_then_incremental', 'last_seen_at'),
    ('payment_methods', 'source', 'payment_methods', 'full_then_incremental', 'updated_at'),
    ('kyc_records',     'source', 'kyc_records',     'full_then_incremental', 'updated_at'),
    ('transactions',    'source', 'transactions',    'full_then_incremental', 'transaction_timestamp')
ON CONFLICT (entity_name) DO NOTHING;

-- ============================================================
-- Verification
-- ============================================================

SELECT table_schema, table_name
FROM   information_schema.tables
WHERE  table_schema = 'control'
ORDER  BY table_schema, table_name;

SELECT *
FROM control.ingestion_control
ORDER BY entity_name;