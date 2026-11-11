# High-Level Design – File Validation & Ingestion Framework

## 1. Context Diagram

┌──────────────┐
External SFTP ───▶│ │
SharePoint ────▶ │ Ingest Bus │ ◀── Browser (React + Okta)
DBX Staging ────▶ │ │
└──────┬───────┘
│ ingestion_events
▼
┌────────────────────┐
│ FastAPI Backend │
│ ┌──────────────┐ │
│ │ Watchers │ │── watermarks / discovery_log
│ │ Workers │ │── register_file() (SQL proc)
│ │ Validators │ │── file_events
│ │ Transfer │ │── transfers
│ └──────────────┘ │
└────────┬───────────┘
│
▼
┌────────────────────┐ ┌──────────────┐
│ PostgreSQL 16 │◀──────▶│ Databricks │
│ 20 tables │ │ Unity Cat. │
└────────────────────┘ │ Bronze + │
│ Auto Loader │
└──────────────┘


## 2. React Portal Architecture
- Vite SPA, single page per major flow: `/upload`, `/batches`, `/files`, `/watchers` (admin)
- Okta Auth JS holds tokens in memory (no localStorage); API client attaches `Authorization`
- Hash computed client-side via Web Crypto (Req 3)
- Batch UI: multi-select file picker + schema-type selector; per-file status table; consolidated summary

## 3. FastAPI Backend Architecture
Layers:
1. **Routers** — HTTP only (`/v1/*`)
2. **Services** — hash, validation, databricks, okta, ingestion_worker, watchers
3. **Data** — asyncpg pool (SQL only, no ORM for MVP)
4. **Background** — `ingestion_worker` (drains `ingestion_events`), `watcher_scheduler` (ticks each `watched_locations`)

Concurrency model:
- Uvicorn 4 workers × asyncpg pool 20 → 80 max DB connections
- `SELECT ... FOR UPDATE SKIP LOCKED` on `ingestion_events` and `watermarks` for safe multi-worker dequeuing

## 4. Relational Database Architecture
- Schema: `fvi` (production) + `fvi_test` (test management)
- 20 tables, 4 views (production) + 7 compatibility views for Req 32 naming
- Partitioning planned for `file_events` and `monitor_metrics` at >10M rows
- Recovery: streaming replica + WAL archive; RPO 15 min

## 5. Databricks Integration Architecture
- **Transfer**: FastAPI → Unity Catalog Files API `PUT /api/2.1/unity-catalog/volumes/.../files/{name}`
- **Ingestion**: Auto Loader per region/schema, `cloudFiles.format=csv`, schemaLocation per target
- **Audit sync**: Databricks job queries `system.access.audit` and POSTs to `/v1/databricks/audit`
- **Reconciliation**: nightly join of `files` ↔ `reconciliation`

## 6. Authentication & Authorization (Okta)
- OIDC authorization-code + PKCE; token verification via JWKS
- Roles → `users.roles`; access gated on `users.access_status='approved'`
- ServiceNow request ID captured on provisioning (`users.snow_request_id`)
- Session records in `sso_sessions` for expiry / revocation validation (Req 28C)

## 7. File Ingestion & Validation Workflow
[Channel connector or UI] → ingestion_events(RECEIVED)
→ ingestion_worker picks event (SKIP LOCKED)
→ connector.fetch() → bytes
→ hash_service.sha256()
→ fvi.register_file() → files row OR DUPLICATE_DETECTED
→ validation_service: first 5 rows vs reference_data schema_field rows
→ status APPROVED → outbox → transfer worker
→ databricks_client.put_volume_file()
→ transfers(SUCCESS) + file_events(TRANSFER_ACK)
→ status TRANSFERRED_TO_DATABRICKS


## 8. Audit / Governance / Security / Reconciliation
- Every state transition and validation run → `file_events`
- Reconciliation job writes `reconciliation.is_consistent`
- Governance: `reference_data(category='validation_rule')` and per-region `app_config`
- Security: secrets referenced (not inlined) in `ingestion_sources.config.secret_ref`

## 9. Performance & Concurrency
- Batch worker concurrency from `app_config.batch_queue_workers`
- Backpressure via `files.status='QUEUED'` cap + `SKIP LOCKED` dequeuing
- Retry with exponential backoff from `app_config.retry_backoff_ms`
- p95 goals: 500 ms register; 5 s/10 MB upload; 30 s transfer

## 10. Error Handling & Recovery
- Every connector has idempotent fetch (hash check happens after fetch)
- Transfer retries via `transfers.attempt_number` + `next_retry_at`
- Watchers auto-recover from `watermarks.last_discovery_at`
- Circuit breaker: `watermarks.consecutive_failures` > `watcher_max_consecutive_failures` → `PAUSED`