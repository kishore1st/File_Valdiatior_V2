# Low-Level Design

## 1. Component Design

### 1.1 HashService — `backend/app/services/hash_service.py`
- Input: async chunk stream (bytes) OR full bytes
- Output: 64-char lowercase hex digest of SHA-256
- Called twice per file: browser (client_hash, advisory) + API (authoritative)
- No storage of intermediate state

### 1.2 UploadService.upload_batch() — `backend/app/routers/uploads.py`
POST /v1/batches (multipart)
├─ verify Okta JWT → current_user (access_status='approved')
├─ validate payload: all files, one schema_type_key (Req 24)
├─ INSERT upload_batches (status INITIATED, total_files=N)
├─ for file in files (sequentially, Req 25):
│ ├─ compute server-side sha256
│ ├─ SELECT fvi.register_file(...) → (file_id, is_duplicate)
│ ├─ if is_duplicate → UPDATE files.status='DUPLICATE_DETECTED'; continue
│ ├─ INSERT ingestion_events (source_type='WEB_UI', file_id, status='RECEIVED')
│ └─ INSERT file_events(event_type='VALIDATION') after validation runs
└─ final UPDATE upload_batches.status (PARTIAL_SUCCESS|COMPLETED)
RETURN 202 {batch_id, correlation_id, total_files, accepted, rejected}


### 1.3 IngestionWorker — `backend/app/services/ingestion_worker.py`
- Loop every 500 ms:
  1. `SELECT ... FROM fvi.ingestion_events WHERE status='RECEIVED' FOR UPDATE SKIP LOCKED LIMIT 10`
  2. For each event: dispatch to connector by `source_type`, fetch bytes
  3. Compute hash; if event has no `file_id`, call `register_file()`
  4. Run validation, write `file_events`
  5. Update event status: `FETCHED → REGISTERED` (or `FAILED`)
- Backpressure: if `files.status='APPROVED'` count > `app_config.max_pending_transfers`, sleep 2 s

### 1.4 ValidationService — `backend/app/services/validation_service.py`
- Load `reference_data` rows where `category='schema_field' AND parent_key=schema_type_key ORDER BY position`
- Parse first 5 records (csv module / openpyxl)
- For each field: compare inferred type to `reference_data.value.data_type`
- Return:
```json
{
  "is_valid": false,
  "records_checked": 5,
  "fields": [
    {"field_id":"...", "name":"dob","pos":4,"expected":"date","actual":"string","match":false}
  ]
}

Persisted verbatim in file_events.payload with event_type='VALIDATION'

1.5 DatabricksClient — backend/app/services/databricks_client.py
put_volume_file(volume_path, filename, bytes) → PUT /api/2.1/unity-catalog/volumes/{volume_path}/files/{filename}

list_volume_files(volume_path, path) → GET (used by Volume watcher)

Auth: Authorization: Bearer ${DATABRICKS_TOKEN}

Timeout 60 s; retry handled by caller (transfers table)

1.6 Connector interface — backend/app/services/watchers/base.py
class Connector(Protocol):
    async def list_since(self, location, since, cursor) -> Iterator[DiscoveredItem]: ...
    async def fetch(self, item) -> bytes: ...

Each connector also implements subscribe() for push mode (SFTP none, Volume none, SharePoint Graph)

1.7 Watcher orchestration — watcher_tick()
See base.py — uses SELECT ... FOR UPDATE on watermarks, inserts into discovery_log with UNIQUE (location_id, source_ref, source_version), then creates ingestion_events.

2. API Specification (see docs/04-api-spec.yaml)
Method	Path	Purpose
POST	/v1/auth/callback	Okta code exchange
POST	/v1/batches		Upload N files, same schema
GET	/v1/batches/{id}	Consolidated summary
GET	/v1/files/{id}		File + events
GET	/v1/files?status=DUPLICATE_DETECTED	Duplicate report
POST	/v1/ingest/events	External push (SFTP webhook, Graph notification)
GET	/v1/watchers		List monitored locations
GET	/v1/watchers/{id}/runs	Watcher run history
POST	/v1/watchers/{id}/reset	Admin watermark reset
POST	/v1/watchers/{id}/pause	Pause tick
POST	/v1/databricks/audit	Audit sync from Databricks
GET	/v1/reconciliation	Inconsistent items
GET	/v1/dashboard/ops	v_ops_overview
GET	/healthz		Liveness

3. Database Tables & Relationships
See db/01-schema.sql, db/05-test-schema.sql, db/06-monitoring.sql, db/07-channel-schema.sql, db/08-watermark-schema.sql.
Full ER: see §5 of this document.

4. Hash Generation & Duplicate Detection
Browser computes SHA-256 (advisory)

API computes SHA-256 (authoritative)

INSERT INTO fvi.files (sha256_hash, ...) — UNIQUE index enforces at most one row

On UNIQUE violation: fetch existing row, return (existing_file_id, is_duplicate=true)

Handler sets status='DUPLICATE_DETECTED', records file_events(DUPLICATE), returns to UI

5. ER Diagram

