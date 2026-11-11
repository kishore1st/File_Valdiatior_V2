-- Compatibility views matching the 7 names from Req 32
CREATE VIEW fvi.channel_master AS
SELECT category_code AS channel_code, description AS channel_name, is_active
FROM   fvi.channel_category;

CREATE VIEW fvi.channel_source_config AS
SELECT source_id, source_type, category_code, subcategory_code, source_key,
       display_name, region_code, config, is_active, created_at, updated_at
FROM   fvi.ingestion_sources;

CREATE VIEW fvi.channel_folder_config AS
SELECT location_id, source_id, location_key, location_type, region_code,
       schema_type_key, discovery_mode, poll_interval_sec, include_pattern,
       is_active, config
FROM   fvi.watched_locations;

CREATE VIEW fvi.channel_watermark AS
SELECT wm.watermark_id, wl.location_id, wl.source_id, wl.location_key,
       wl.location_type, wl.region_code,
       wm.last_discovery_at, wm.last_discovered_item,
       wm.last_processed_at, wm.last_processed_item,
       wm.source_cursor, wm.status, wm.last_error,
       wm.consecutive_failures, wm.last_run_at, wm.updated_at
FROM   fvi.watermarks wm
JOIN   fvi.watched_locations wl USING (location_id);

CREATE VIEW fvi.channel_event_log AS
SELECT event_id, source_id, location_id, discovery_id, correlation_id,
       raw_payload, file_name, source_ref, status, received_at, processed_at,
       file_id, error_message
FROM   fvi.ingestion_events;

CREATE VIEW fvi.channel_discovery_log AS
SELECT discovery_id, location_id, source_ref, source_version, file_name,
       file_size_bytes, source_modified_at, discovered_at, status,
       ingestion_event_id, file_id, error_message
FROM   fvi.discovery_log;

CREATE VIEW fvi.channel_watcher_audit AS
SELECT run_id, location_id, started_at, finished_at, status,
       files_discovered, files_fetched, files_skipped,
       bytes_scanned, duration_ms, error_message, run_by
FROM   fvi.watcher_runs;