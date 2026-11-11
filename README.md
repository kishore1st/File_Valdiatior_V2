# File Validator V2 (FVI) — File Validation & Ingestion Framework

Centralized, channel-independent framework that **validates, deduplicates, transfers, and reconciles** CSV/XLSX files delivered by regional business teams — via the React upload portal, SFTP drops, SharePoint document libraries, and Databricks staging Volumes — into Databricks Bronze.

Replaces the manual handoff that caused duplicate ingestion, no audit trail, and no SLA visibility.

## Pipeline

1. Files arrive through a channel (portal upload, SFTP, SharePoint, Databricks Volume — watched with watermarks)
2. SHA-256 hash computed client-side (portal) or server-side; **atomic dedupe** via `UNIQUE(files.sha256_hash)` + `fvi.register_file()` stored procedure
3. Validation: allowed type/size, first-N-record schema type check → results in `file_events` (append-only audit)
4. Approved files routed to the correct regional Unity Catalog Volume (`reference_data` → `volume_mapping`)
5. Databricks Auto Loader ingests Intake → Bronze; nightly `files ↔ reconciliation` sync; Databricks audit pushed back to `/v1/databricks/audit`

## Technology Stack

| Layer | Technology |
| --- | --- |
| UI portal | React 18 + Vite + TypeScript, Okta Auth JS (OIDC/PKCE), Web Crypto SHA-256 |
| API | FastAPI (async) + asyncpg + Pydantic v2 |
| Database | PostgreSQL 16 — schemas `fvi` (prod) / `fvi_test` (test) |
| Ingestion | asyncio workers, `SELECT … FOR UPDATE SKIP LOCKED`, asyncssh, msgraph-sdk, httpx |
| Databricks | Unity Catalog Volumes (Files API PUT), Auto Loader, REST 2.1 |
| Auth | Okta OIDC + JWKS verification; ServiceNow request captured at provisioning |
| Observability | Prometheus metrics → `monitor_metrics` |
| Testing | pytest, Playwright (e2e), k6 (perf) |
| Packaging | Docker Compose |

## Repository Layout

| Path | Contents |
| --- | --- |
| `backend/` | FastAPI app — `routers/` (auth, uploads, batches, files, databricks, watchers, health), `services/` (validation, hash, ingestion worker, Okta, Databricks client, `watchers/` for SFTP/Volume/SharePoint/scheduler) |
| `frontend/` | React portal — uploader, batch summary, status tables, Okta provider, client API |
| `Sql Scripts/` | Postgres DDL `db01`–`db09`: schema, seeds, views, functions, test schema, monitoring, channel schema, watermark schema, channel views |
| `databricks/` | Auto Loader bronze notebook, audit-sync notebook, `autoloader_job.json` |
| `Design Docs/` | Solution design, HLD, LLD, ER diagram |
| `Docs/` | API spec (`04-api-spec.yaml`), requirement spec, test cases/plans, runbook, monitoring, multichannel & watermark notes |
| `Mockup Screens/` | HTML UI mockups (admin, manager, upload, lifecycle) |
| `sample-data/` | Regional customer files (US/GB/EU/IN/AE) |
| `tests/` | e2e (SFTP/volume watermark, UI flow) + perf (`k6_upload.js`) |

## Build Order (safe stop/restart)

1. **Database first** — apply `Sql Scripts/db01…db09`; schema must exist before anything runs
2. **Backend** — API + workers
3. **Frontend** — UI
4. **Databricks** — notebooks/jobs
5. **Tests** — E2E + perf
6. **Docs** — can be written last

## Running Locally

```bash
cp .env.example .env            # fill Okta + Databricks credentials
docker compose up --build      # Postgres 16 + FastAPI (:8000) + Vite UI (:5173)
```

The UI dev server proxies `/v1/*` to the API on port 8000.

> On first start, Postgres automatically applies the DDL from `Sql Scripts/` (`db01`–`db09`, executed in name order) through the `docker-entrypoint-initdb.d` mount. The mount is read-only; schema changes must be made in the scripts and re-applied or run against the running database.

## Key Design Decisions

* Atomic dedupe via `UNIQUE(sha256_hash)` + `register_file()` — never read-then-write
* One `reference_data` JSONB table for regions, schema types, schema fields, volume mappings, validation rules
* All state transitions recorded in `file_events`; `files.status` is a denormalized cache
* Channel-independent ingestion via `ingestion_events`; every channel is a connector
* Watcher idempotency via `UNIQUE(location_id, source_ref, source_version)` on `discovery_log`
* Test artifacts isolated in `fvi_test` schema; production tables untouched

## Implementation Phases

1. DB schema, FastAPI core, React upload, hash dedupe, batch semantics
2. Databricks transfer + Auto Loader + reconciliation
3. Multi-channel connectors (SFTP, Volume, SharePoint)
4. Watchers + watermarks + monitoring dashboards
5. E2E, performance, SSO test execution + sign-off

See `Design Docs/docs.01-solution-design.md` for the full requirement-to-design mapping, HLD/LLD, and the runbook in `Docs/06-runbook.md`.