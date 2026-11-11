CREATE TABLE fvi.monitor_metrics (
  metric_id   BIGSERIAL PRIMARY KEY,
  sampled_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  metric_name VARCHAR(64) NOT NULL,
  value       DOUBLE PRECISION NOT NULL,
  region_code VARCHAR(8),
  dimensions  JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX ix_monitor_metrics_name_time
  ON fvi.monitor_metrics(metric_name, sampled_at DESC);

CREATE TABLE fvi.dashboard_config (
  dashboard_key VARCHAR(64) PRIMARY KEY,
  title         VARCHAR(128) NOT NULL,
  panels        JSONB NOT NULL,
  updated_by    UUID REFERENCES fvi.users(user_id),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE VIEW fvi.v_ops_overview AS
SELECT
 (SELECT COUNT(*) FROM fvi.files WHERE created_at > now()-INTERVAL '24 hours')          AS files_24h,
 (SELECT COUNT(*) FROM fvi.files
   WHERE status='DUPLICATE_DETECTED' AND created_at > now()-INTERVAL '24 hours')        AS dups_blocked_24h,
 (SELECT COUNT(*) FROM fvi.upload_batches
   WHERE status='PARTIAL_SUCCESS'   AND created_at > now()-INTERVAL '24 hours')         AS partial_batches_24h,
 (SELECT COUNT(*) FROM fvi.reconciliation
   WHERE is_consistent=FALSE       AND reconciled_at > now()-INTERVAL '24 hours')       AS recon_inconsistent_24h,
 (SELECT percentile_cont(0.95) WITHIN GROUP (ORDER BY value)
    FROM fvi.monitor_metrics
   WHERE metric_name='api_latency_ms'
     AND sampled_at > now()-INTERVAL '1 hour')                                          AS api_p95_1h_ms;