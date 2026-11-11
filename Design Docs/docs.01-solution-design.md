# Solution Design – File Validation & Ingestion Framework (MVP)

Version: 1.0 · Owner: Data Platform Team · Status: Approved for MVP build

## 1. Business Context
Regional business teams deliver CSV/XLSX files from web portals, SFTP drops,
Databricks staging Volumes, and SharePoint document libraries. The current
manual handoff results in duplicate ingestion, no audit trail, and no SLA
visibility. This solution centralizes validation, deduplication, transfer to
Databricks Bronze, and reconciliation under one channel-independent framework.

## 2. Scope (MVP)
In scope:
- React UI portal (Req 1–3) with Okta SSO (Req 2)
- PostgreSQL relational store (Req 18) with 20 tables
- FastAPI backend (Req 8–11)
- Databricks Volume transfer + Auto Loader (Req 10–14)
- Batched multi-file upload with per-file outcome (Req 24–26)
- E2E, performance, SSO, monitoring test artefacts (Req 27–29)
- Multi-channel ingestion: SFTP, Databricks Volume, SharePoint (Req 30)
- Event watchers + watermarks (Req 31–32)

Out of scope (future): S3/ADLS/GCS/BLOB channels, policy engine,
ML-based anomaly detection.

## 3. Functional Requirements → Design
| Req | Requirement | Design location |
|-----|-------------|-----------------|
| 1   | CSV/XLSX upload UI | `frontend/src/components/FileUploader.tsx` |
| 2   | Okta SSO + SNOW approval | `backend/app/services/okta.py`, `users.access_status` |
| 3   | Client SHA-256 + dup detection | `frontend/src/utils/sha256.ts`; `files.sha256_hash` UNIQUE |
| 4   | Registry/Audit/Governance/Security/Recon | `db/01-schema.sql`, `db/05-test-schema.sql` |
| 5   | Upload context capture | `files.machine_host/ip_address/user_agent`; `file_events.payload` |
| 6   | First-5-record type check | `validation_service.py` → `file_events(event_type='VALIDATION')` |
| 7   | Full activity audit | `file_events` (append-only) |
| 8   | All comms via APIs | FastAPI routers (`/v1/*`) |
| 9   | Backend hash + registry update | `fvi.register_file()` stored proc, `ingestion_worker.py` |
| 10  | Route to correct Volume | `reference_data(category='volume_mapping')` |
| 11  | Capture ack + status update | `transfers` table + `file_events(TRANSFER_ACK)` |
| 12  | Auto Loader detection | `databricks/notebooks/01_autoloader_bronze.py` |
| 13  | system tables → MongoDB (→ PG) | `databricks/notebooks/02_sync_audit_to_api.py`, `reconciliation` |
| 14  | REST APIs to pull audit | `databricks_client.py` |
| 15–21 | Performance, concurrency, batch, dedup | `app_config`, `SKIP LOCKED`, UNIQUE index on `sha256_hash` |
| 22  | SQL scripts | `db/*.sql` |
| 23  | Sample data | `db/sample-data/*.csv` |
| 24–26 | Multi-file batch, sequential, per-file reject | `upload_batches`, `files.status`, `v_batch_summary` |
| 27  | E2E / smoke | `docs/05-test-cases.md`, `tests/e2e/` |
| 28  | Perf + SSO tests | `docs/08-perf-test-plan.md`, `docs/09-sso-test-plan.md`, `sso_sessions` |
| 29  | Monitoring dashboards | `monitor_metrics`, `dashboard_config`, `v_ops_overview` |
| 30  | Multi-channel ingestion | `ingestion_sources` (with category/subcategory), `ingestion_events`, connectors |
| 31  | Event watchers + watermarks | `watched_locations`, `watermarks`, `discovery_log`, `watcher_runs` |
| 32  | Watermark tables + views | `db/08-watermark-schema.sql`, `db/09-channel-views.sql` |

## 4. Non-Functional Requirements
- Concurrency: 50 parallel uploads; p95 register ≤ 500 ms; p95 file upload ≤ 5 s per 10 MB
- Availability 99.5% / RPO 15 min (audit) / RTO 1 h
- Security: Okta OIDC; TLS 1.2+; no PII in logs; secrets via env/secret manager
- Retention: audit 24 months, files 12 months, reconciliation 24 months

## 5. Architecture Decisions (ADRs)
- **ADR-01** Atomic dedupe via `UNIQUE(sha256_hash)` + `register_file()`; never read-then-write.
- **ADR-02** One `reference_data` JSONB table (config) instead of 6 micro-tables.
- **ADR-03** All state transitions in `file_events`; `files.status` is denormalized cache.
- **ADR-04** Ingestion is channel-independent via `ingestion_events`; every channel is a connector.
- **ADR-05** Watcher idempotency via `UNIQUE(location_id, source_ref, source_version)` on `discovery_log`.
- **ADR-06** Test artifacts live in `fvi_test` schema; production tables untouched.
- **ADR-07** PostgreSQL chosen over SQL Server (Req 18) for JSONB, `SKIP LOCKED`, `ON CONFLICT`, cost.

## 6. Technology Stack
| Layer | Technology |
|---|---|
| UI | React 18 + Vite + Okta Auth JS |
| API | FastAPI (async) + asyncpg + Pydantic v2 |
| DB | PostgreSQL 16 |
| Ingestion | asyncio workers; asyncssh; msgraph-sdk; httpx |
| Databricks | Unity Catalog Volumes + Auto Loader + REST 2.1 |
| Auth | Okta OIDC (PKCE) |
| Observability | Prometheus metrics → `monitor_metrics` |
| Testing | pytest + Playwright + k6 |
| Packaging | Docker Compose |

## 7. Implementation Phases
- **Phase 1 (2 weeks)** — DB schema, FastAPI core, React upload, hash dedupe, batch semantics
- **Phase 2 (2 weeks)** — Databricks transfer + Auto Loader + reconciliation
- **Phase 3 (1 week)** — Multi-channel connectors (SFTP, Volume, SharePoint)
- **Phase 4 (1 week)** — Watchers + watermarks + monitoring dashboards
- **Phase 5 (1 week)** — E2E, performance, SSO test execution + sign-off

## 8. Assumptions & Risks
- Okta tenant and ServiceNow workflow available before Phase 1 end
- Databricks workspace has Unity Catalog enabled
- SharePoint Graph app registration approved (may slip Phase 3 — Volume + SFTP still deliverable)
- Network egress allowed from FastAPI to Databricks, SFTP, Graph