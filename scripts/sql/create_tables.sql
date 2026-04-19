-- ============================================================
-- DDL: fintech_oltp.source (PostgreSQL 17)
-- ============================================================

-- 1) Database
-- (Run this manually if needed: CREATE DATABASE fintech_oltp;)

-- 2) Schema
CREATE SCHEMA IF NOT EXISTS source;

-- 3) Drop existing tables (idempotent re-run)
DROP TABLE IF EXISTS source.ingestion_control   CASCADE;
DROP TABLE IF EXISTS source.transactions        CASCADE;
DROP TABLE IF EXISTS source.kyc_records         CASCADE;
DROP TABLE IF EXISTS source.payment_methods     CASCADE;
DROP TABLE IF EXISTS source.devices             CASCADE;
DROP TABLE IF EXISTS source.accounts            CASCADE;
DROP TABLE IF EXISTS source.merchants           CASCADE;
DROP TABLE IF EXISTS source.users               CASCADE;

-- ============================================================
-- ROOT ENTITIES (no FKs)
-- ============================================================

CREATE TABLE source.users (
    user_id            VARCHAR(36)   NOT NULL,
    first_name         VARCHAR(100)  NOT NULL,
    last_name          VARCHAR(100)  NOT NULL,
    email              VARCHAR(255),
    phone_number       VARCHAR(30),
    date_of_birth      DATE          NOT NULL,
    gender             VARCHAR(2)    NOT NULL,
    country            VARCHAR(5)    NOT NULL,
    city               VARCHAR(100)  NOT NULL,
    preferred_currency VARCHAR(5)    NOT NULL,
    kyc_status         VARCHAR(20)   NOT NULL,
    user_tier          VARCHAR(20)   NOT NULL,
    is_active          BOOLEAN       NOT NULL,
    registration_date  TIMESTAMP     NOT NULL,
    created_at         TIMESTAMP     NOT NULL,
    updated_at         TIMESTAMP     NOT NULL
);

CREATE TABLE source.merchants (
    merchant_id        VARCHAR(36),
    merchant_name      VARCHAR(200)  NOT NULL,
    merchant_category  VARCHAR(50)   NOT NULL,
    business_type      VARCHAR(30)   NOT NULL,
    country            VARCHAR(5)    NOT NULL,
    city               VARCHAR(100)  NOT NULL,
    registration_date  DATE          NOT NULL,
    is_verified        BOOLEAN       NOT NULL,
    is_active          BOOLEAN       NOT NULL,
    risk_score         DECIMAL(4,3)  NOT NULL,
    monthly_limit      INTEGER       NOT NULL,
    fee_percentage     DECIMAL(4,2)  NOT NULL,
    created_at         TIMESTAMP     NOT NULL,
    updated_at         TIMESTAMP     NOT NULL
);

-- ============================================================
-- CHILD ENTITIES (FK references — NOT ENFORCED)
-- ============================================================

CREATE TABLE source.accounts (
    account_id    VARCHAR(36),
    user_id       VARCHAR(36)    NOT NULL,
    account_type  VARCHAR(20)    NOT NULL,
    currency      VARCHAR(5)     NOT NULL,
    balance       DECIMAL(15,2)  NOT NULL,
    daily_limit   INTEGER        NOT NULL,
    monthly_limit INTEGER        NOT NULL,
    status        VARCHAR(20)    NOT NULL,
    created_at    TIMESTAMP      NOT NULL,
    updated_at    TIMESTAMP      NOT NULL
);

CREATE TABLE source.devices (
    device_id          VARCHAR(36),
    user_id            VARCHAR(36)   NOT NULL,
    device_type        VARCHAR(20)   NOT NULL,
    device_model       VARCHAR(100)  NOT NULL,
    os_version         VARCHAR(50)   NOT NULL,
    app_version        VARCHAR(20)   NOT NULL,
    device_fingerprint VARCHAR(64)   NOT NULL,
    is_trusted         BOOLEAN       NOT NULL,
    first_seen_at      TIMESTAMP     NOT NULL,
    last_seen_at       TIMESTAMP     NOT NULL,
    created_at         TIMESTAMP     NOT NULL
);

CREATE TABLE source.payment_methods (
    payment_method_id VARCHAR(36),
    user_id           VARCHAR(36)   NOT NULL,
    method_type       VARCHAR(30)   NOT NULL,
    provider          VARCHAR(50)   NOT NULL,
    last_four_digits  VARCHAR(10),
    expiry_date       DATE,
    is_default        BOOLEAN       NOT NULL,
    is_verified       BOOLEAN       NOT NULL,
    is_active         BOOLEAN       NOT NULL,
    added_at          TIMESTAMP     NOT NULL,
    created_at        TIMESTAMP     NOT NULL,
    updated_at        TIMESTAMP     NOT NULL
);

CREATE TABLE source.kyc_records (
    kyc_id                VARCHAR(36)   NOT NULL,
    user_id               VARCHAR(36)   NOT NULL,
    document_type         VARCHAR(30)   NOT NULL,
    document_number_hash  VARCHAR(64),
    document_country      VARCHAR(5)    NOT NULL,
    verification_status   VARCHAR(20)   NOT NULL,
    rejection_reason      TEXT,
    verification_attempts INTEGER       NOT NULL,
    submitted_at          TIMESTAMP     NOT NULL,
    verified_at           TIMESTAMP,
    verified_by           VARCHAR(30),
    risk_flags            TEXT,
    created_at            TIMESTAMP     NOT NULL,
    updated_at            TIMESTAMP     NOT NULL
);

CREATE TABLE source.transactions (
    transaction_id        VARCHAR(36)    NOT NULL,
    sender_account_id     VARCHAR(36)    NOT NULL,
    receiver_id           VARCHAR(36),
    receiver_type         VARCHAR(20)    NOT NULL,
    transaction_type      VARCHAR(30)    NOT NULL,
    payment_method_id     VARCHAR(36)    NOT NULL,
    amount                DECIMAL(15,2)  NOT NULL,
    currency              VARCHAR(5)     NOT NULL,
    fee_amount            DECIMAL(10,2)  NOT NULL,
    status                VARCHAR(20)    NOT NULL,
    device_id             VARCHAR(36)    NOT NULL,
    ip_address            VARCHAR(45),
    latitude              DECIMAL(10,7),
    longitude             DECIMAL(10,7),
    transaction_timestamp TIMESTAMP      NOT NULL,
    completed_timestamp   TIMESTAMP,
    risk_score            DECIMAL(4,3),
    is_flagged            BOOLEAN        NOT NULL,
    fraud_pattern         VARCHAR(50),
    created_at            TIMESTAMP      NOT NULL
);

-- ============================================================
-- WATERMARK CONTROL TABLE (for ADF incremental ingestion)
-- ============================================================

CREATE TABLE source.ingestion_control (
    entity_name    VARCHAR(50)   PRIMARY KEY,
    source_table   VARCHAR(100)  NOT NULL,
    watermark_col  VARCHAR(50)   NOT NULL,
    last_watermark TIMESTAMP     NOT NULL DEFAULT '1900-01-01 00:00:00',
    last_run_ts    TIMESTAMP,
    rows_ingested  INTEGER       DEFAULT 0
);

INSERT INTO source.ingestion_control (entity_name, source_table, watermark_col) VALUES
    ('users',           'source.users',           'updated_at'),
    ('merchants',       'source.merchants',       'updated_at'),
    ('accounts',        'source.accounts',        'updated_at'),
    ('devices',         'source.devices',         'last_seen_at'),
    ('payment_methods', 'source.payment_methods', 'updated_at'),
    ('kyc_records',     'source.kyc_records',     'updated_at'),
    ('transactions',    'source.transactions',    'transaction_timestamp')
ON CONFLICT (entity_name) DO NOTHING;

-- ============================================================
-- Verification
-- ============================================================
SELECT table_name
FROM   information_schema.tables
WHERE  table_schema = 'source'
ORDER  BY table_name;
