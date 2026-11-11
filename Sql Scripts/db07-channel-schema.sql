-- ============================================================
-- Multi-channel ingestion (Req 30) - category + subcategory added
-- ============================================================
CREATE TABLE fvi.channel_category (
  category_code VARCHAR(32) PRIMARY KEY,
  description   TEXT NOT NULL,
  is_active     BOOLEAN NOT NULL DEFAULT TRUE
);
INSERT INTO fvi.channel_category VALUES
 ('FILE_SYSTEM','SFTP, network shares, and enterprise filesystems'),
 ('CLOUD_STORAGE','S3, ADLS, GCS, Azure Blob'),
 ('DOCUMENT_MANAGEMENT','SharePoint, Box, Confluence'),
 ('DATA_PLATFORM','Databricks Volumes, Snowflake stages'),
 ('WEB_UPLOAD','Browser upload via UI portal'),
 ('API_PUSH','REST or webhook-driven ingest');

CREATE TABLE fvi.channel_subcategory (
  subcategory_code VARCHAR(32) PRIMARY KEY,
  category_code    VARCHAR(32) NOT NULL REFERENCES fvi.channel_category(category_code),
  description      TEXT NOT NULL,
  is_active        BOOLEAN NOT NULL DEFAULT TRUE
);
INSERT INTO fvi.channel_subcategory VALUES
 ('SFTP','FILE_SYSTEM','Secure FTP push'),
 ('INTERNAL_FS','FILE_SYSTEM','Internal network share'),
 ('S3','CLOUD_STORAGE','AWS S3 prefix'),
 ('ADLS','CLOUD_STORAGE','Azure Data Lake Storage'),
 ('GCS','CLOUD_STORAGE','Google Cloud Storage'),
 ('BLOB','CLOUD_STORAGE','Azure Blob Storage'),
 ('SHAREPOINT','DOCUMENT_MANAGEMENT','SharePoint Document Library'),
 ('DBX_VOLUME','DATA_PLATFORM','Databricks Unity Catalog Volume'),
 ('REACT_UI','WEB_UPLOAD','React portal upload'),
 ('REST_PUSH','API_PUSH','External system POSTs to /v1/ingest/events');

CREATE TABLE fvi.ingestion_sources (
  source_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_type        VARCHAR(32) NOT NULL,          -- e.g. 'SFTP','SHAREPOINT','DBX_VOLUME','WEB_UI'
  category_code      VARCHAR(32) NOT NULL REFERENCES fvi.channel_category(category_code),
  subcategory_code   VARCHAR(32) NOT NULL REFERENCES fvi.channel_subcategory(subcategory_code),
  source_key         VARCHAR(64)  NOT NULL,          -- 'ext-sftp-eu','sp-finance'
  display_name       VARCHAR(128) NOT NULL,
  region_code        VARCHAR(8),
  config             JSONB NOT NULL DEFAULT '{}',
  is_active          BOOLEAN NOT NULL DEFAULT TRUE,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (source_type, source_key)
);
CREATE INDEX ix_ing_sources_cat ON fvi.ingestion_sources(category_code, subcategory_code)
  WHERE is_active;

CREATE TABLE fvi.ingestion_events (
  event_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id       UUID NOT NULL REFERENCES fvi.ingestion_sources(source_id),
  location_id     UUID,                              -- FK added in 08-watermark-schema.sql
  discovery_id    UUID,                              -- FK added in 08-watermark-schema.sql
  correlation_id  UUID NOT NULL UNIQUE,
  raw_payload     JSONB NOT NULL DEFAULT '{}',
  file_name       VARCHAR(512) NOT NULL,
  file_size_bytes BIGINT,
  declared_ext    VARCHAR(8),
  source_ref      VARCHAR(1024),
  status          VARCHAR(16) NOT NULL DEFAULT 'RECEIVED'
                  CHECK (status IN ('RECEIVED','FETCHING','FETCHED',
                                    'REGISTERED','FAILED','IGNORED')),
  file_id         UUID REFERENCES fvi.files(file_id),
  error_message   TEXT,
  received_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  processed_at    TIMESTAMPTZ
);
CREATE INDEX ix_ing_events_status
  ON fvi.ingestion_events(status, received_at)
  WHERE status IN ('RECEIVED','FETCHING');
CREATE INDEX ix_ing_events_source
  ON fvi.ingestion_events(source_id, received_at DESC);

ALTER TABLE fvi.files ADD CONSTRAINT fk_files_source
  FOREIGN KEY (source_id) REFERENCES fvi.ingestion_sources(source_id);

ALTER TABLE fvi.file_events DROP CONSTRAINT IF EXISTS file_events_event_type_check;
ALTER TABLE fvi.file_events ADD CONSTRAINT file_events_event_type_check
  CHECK (event_type IN (
    'BATCH_START','BATCH_ITEM_QUEUED','HASH_CHECK','DUPLICATE','VALIDATION',
    'TRANSFER_ATTEMPT','TRANSFER_ACK','DBX_INGEST','STATUS_CHANGE','AUDIT','AUTH',
    'E2E_TEST','PERF_TEST','LOGIN','LOGOUT','TOKEN_REFRESH','ACCESS_CHANGE','TOKEN_REVOKED',
    'INGEST_RECEIVED','INGEST_FETCHED','INGEST_FAILED','SOURCE_HEALTH_CHECK',
    'WATCHER_TICK','WATCHER_FAILED','WATERMARK_ADVANCED','WATERMARK_RESET',
    'DISCOVERY_SKIPPED','DISCOVERY_DUPLICATE'
  ));