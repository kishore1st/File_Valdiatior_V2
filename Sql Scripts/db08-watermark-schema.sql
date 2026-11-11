CREATE TABLE fvi.watched_locations (
  location_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id       UUID NOT NULL REFERENCES fvi.ingestion_sources(source_id) ON DELETE CASCADE,
  location_key    VARCHAR(128) NOT NULL,
  location_type   VARCHAR(16) NOT NULL
                  CHECK (location_type IN ('SFTP_FOLDER','DBX_VOLUME','SP_FOLDER',
                                           'S3_PREFIX','ADLS_PATH','GCS_PREFIX')),
  region_code     VARCHAR(8),
  schema_type_key VARCHAR(64),
  discovery_mode  VARCHAR(16) NOT NULL DEFAULT 'POLL'
                  CHECK (discovery_mode IN ('PUSH','POLL','HYBRID')),
  poll_interval_sec INT NOT NULL DEFAULT 60,
  include_pattern VARCHAR(128) DEFAULT '*.csv',
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  config          JSONB NOT NULL DEFAULT '{}',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (source_id, location_key)
);
CREATE INDEX ix_watched_active ON fvi.watched_locations(source_id, location_type)
  WHERE is_active;

CREATE TABLE fvi.watermarks (
  watermark_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  location_id          UUID NOT NULL UNIQUE REFERENCES fvi.watched_locations(location_id) ON DELETE CASCADE,
  last_discovery_at    TIMESTAMPTZ NOT NULL DEFAULT '1970-01-01',
  last_discovered_item VARCHAR(512),
  last_processed_at    TIMESTAMPTZ NOT NULL DEFAULT '1970-01-01',
  last_processed_item  VARCHAR(512),
  source_cursor        TEXT,
  status               VARCHAR(16) NOT NULL DEFAULT 'IDLE'
                       CHECK (status IN ('IDLE','SCANNING','PROCESSING','ERROR','PAUSED')),
  last_error           TEXT,
  consecutive_failures INT NOT NULL DEFAULT 0,
  last_run_at          TIMESTAMPTZ,
  updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_wm_status ON fvi.watermarks(status) WHERE status <> 'IDLE';

CREATE TABLE fvi.discovery_log (
  discovery_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  location_id     UUID NOT NULL REFERENCES fvi.watched_locations(location_id) ON DELETE CASCADE,
  source_ref      VARCHAR(1024) NOT NULL,
  source_version  VARCHAR(64),
  file_name       VARCHAR(512) NOT NULL,
  file_size_bytes BIGINT,
  source_modified_at TIMESTAMPTZ,
  discovered_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  status          VARCHAR(16) NOT NULL DEFAULT 'DISCOVERED'
                  CHECK (status IN ('DISCOVERED','FETCHED','REGISTERED','DUPLICATE',
                                    'SKIPPED','FAILED')),
  ingestion_event_id UUID REFERENCES fvi.ingestion_events(event_id),
  file_id         UUID REFERENCES fvi.files(file_id),
  error_message   TEXT
);
CREATE UNIQUE INDEX ux_discovery_identity
  ON fvi.discovery_log(location_id, source_ref, COALESCE(source_version, '-'));
CREATE INDEX ix_discovery_pending
  ON fvi.discovery_log(location_id, discovered_at)
  WHERE status = 'DISCOVERED';

CREATE TABLE fvi.watcher_runs (
  run_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  location_id      UUID NOT NULL REFERENCES fvi.watched_locations(location_id) ON DELETE CASCADE,
  started_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at      TIMESTAMPTZ,
  status           VARCHAR(12) NOT NULL DEFAULT 'RUNNING'
                   CHECK (status IN ('RUNNING','SUCCESS','PARTIAL','FAILED')),
  files_discovered INT NOT NULL DEFAULT 0,
  files_fetched    INT NOT NULL DEFAULT 0,
  files_skipped    INT NOT NULL DEFAULT 0,
  bytes_scanned    BIGINT,
  duration_ms      INT,
  error_message    TEXT,
  run_by           VARCHAR(16) NOT NULL DEFAULT 'WATCHER'
                   CHECK (run_by IN ('WATCHER','MANUAL','RECOVERY'))
);
CREATE INDEX ix_watcher_runs_loc ON fvi.watcher_runs(location_id, started_at DESC);
CREATE INDEX ix_watcher_runs_fail ON fvi.watcher_runs(started_at DESC) WHERE status='FAILED';

ALTER TABLE fvi.ingestion_events ADD CONSTRAINT fk_ing_events_location
  FOREIGN KEY (location_id) REFERENCES fvi.watched_locations(location_id);
ALTER TABLE fvi.ingestion_events ADD CONSTRAINT fk_ing_events_discovery
  FOREIGN KEY (discovery_id) REFERENCES fvi.discovery_log(discovery_id);