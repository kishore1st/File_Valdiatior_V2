# Operational Runbook

## Startup
1. `docker compose up -d db`
2. Wait for Postgres to apply `db/01..09*.sql`
3. `docker compose up -d api ui`
4. Verify: `curl http://localhost:8000/healthz` → `{"ok":true}`

## Common checks
- Pending events: `SELECT COUNT(*) FROM fvi.ingestion_events WHERE status='RECEIVED'`
- Stuck files:   `SELECT status, COUNT(*) FROM fvi.files GROUP BY status`
- Watcher state: `SELECT * FROM fvi.v_channel_health` (if created) or `SELECT * FROM fvi.watermarks`
- Recent failures: `SELECT * FROM fvi.watcher_runs WHERE status='FAILED' ORDER BY started_at DESC LIMIT 20`

## Recovery
- **Watcher paused** → `POST /v1/watchers/{location_id}/reset` (admin) then wait for next tick
- **Transfer stuck** → `UPDATE fvi.transfers SET next_retry_at=now() WHERE status='RETRY'`
- **Duplicate storm** → inspect `v_duplicate_attempts`; if a partner is re-sending, ask them to stop; the UNIQUE index prevents any ingestion

## Deploy
- Backend: `docker build -t fvi-backend ./backend && docker push ...`
- Databricks: import `databricks/notebooks/*` and `databricks/jobs/*` into workspace; set `CLUSTER_ID` on the job