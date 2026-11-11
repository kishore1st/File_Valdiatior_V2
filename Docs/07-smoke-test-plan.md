# Smoke & End-to-End Test Plan (Req 27)

Version: 1.0 · Owner: QA + Data Platform · Sign-off gate for MVP

## 1. Objective
Prove that the complete framework — authentication, upload, validation,
deduplication, batch semantics, Databricks transfer, Auto Loader ingestion,
and reconciliation — works as one system before MVP sign-off.

A **smoke run** must complete in ≤ 30 minutes with **all P0 cases PASS**.
An **E2E run** covers the smoke set plus the extended scenarios in
`docs/05-test-cases.md` (TC-01 … TC-28).

## 2. Scope
In scope:
- Okta SSO authentication and role authorization (TC-10, TC-11, TC-12)
- Single-file and multi-file upload (TC-01, TC-05)
- CSV and XLSX validation (TC-06)
- SHA-256 duplicate detection (TC-02, TC-03)
- Batch semantics with per-file outcome (TC-04, TC-05)
- Databricks Volume transfer (TC-07, TC-08)
- Auto Loader ingestion + audit sync (TC-09)
- Reconciliation (TC-09)
- Multi-channel ingest (TC-13 … TC-19)
- Watcher watermark correctness (TC-20 … TC-28)

Out of scope for smoke (covered in performance plan):
- Sustained 50-VU load, stress, memory profiling

## 3. Pre-requisites
| Item | Required |
|---|---|
| PostgreSQL 16 running with `db/01..09*.sql` applied | ✓ |
| FastAPI backend running at `FVI_API` | ✓ |
| React UI running at `UI_URL` | ✓ |
| Okta test tenant with 3 users (uploader / approver / auditor) | ✓ |
| Databricks workspace with `main.bronze` schema and 5 region Volumes | ✓ |
| Databricks job `fvi-autoloader-bronze` deployed | ✓ |
| Sample files from `db/sample-data/*.csv` present | ✓ |
| `FVI_TOKEN`, `DATABRICKS_TOKEN`, `OKTA_JWKS_URL` env vars set | ✓ |

## 4. Smoke suite (must-run, ≤ 30 min)

Run order matters — later tests depend on state created by earlier ones.

| Step | TC     | Action                                                                 | Expected                                                                                      | Time |
|------|--------|------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------|------|
| S-01 | TC-10  | Call `GET /v1/files` with no token                                     | HTTP 401                                                                                      | 10s  |
| S-02 | TC-10  | Call `GET /v1/files` with an auditor-only token                        | HTTP 403                                                                                      | 10s  |
| S-03 | TC-01  | Login via Okta as uploader; `GET /v1/auth/me`                          | 200, roles include `uploader`                                                                 | 30s  |
| S-04 | TC-01  | Upload `IN_customer.csv`                                               | 202; `batch_id`; `accepted=1`; file `status` reaches `TRANSFERRED_TO_DATABRICKS` within 60 s | 90s  |
| S-05 | TC-02  | Re-upload same file as a second user                                   | 202; `rejected=1`; file `status='DUPLICATE_DETECTED'`                                         | 30s  |
| S-06 | TC-03  | Fire 10 parallel identical uploads (same file)                         | Exactly one `files` row for that hash; 9 `DUPLICATE_DETECTED` events                          | 60s  |
| S-07 | TC-05  | Upload 5-file batch: 4 new + 1 duplicate                               | `status='PARTIAL_SUCCESS'`, `accepted=4`, `rejected=1`                                        | 60s  |
| S-08 | TC-06  | Upload `IN_customer_bad_type.csv` (string in date field)               | `status='VALIDATION_FAILED'`; `file_events.payload.mismatches` non-empty                      | 30s  |
| S-09 | TC-07  | Inspect Databricks Volume `/Volumes/main/bronze/incoming/IN/customer/` | Contains accepted filenames; `transfers.status='SUCCESS'`                                     | 30s  |
| S-10 | TC-09  | Wait for next Auto Loader run + audit sync job                         | `main.bronze.customer_in` row count increased; `reconciliation.is_consistent=TRUE` for accepted files | 5m   |
| S-11 | TC-09  | Call `GET /v1/databricks/reconciliation`                               | 0 items returned                                                                              | 10s  |
| S-12 | —      | Check `v_ops_overview`                                                 | `files_24h` ≥ 5, `dups_blocked_24h` ≥ 10                                                      | 10s  |

**Total smoke time:** ≈ 9 minutes plus Auto Loader wait.

## 5. Extended E2E (all TCs 01–28)

Run after smoke passes. Each TC loaded into `fvi_test.test_cases` and executed
by `pytest tests/e2e/` — results written to `fvi_test.test_runs` and
`fvi_test.test_results`. Full list in `docs/05-test-cases.md`.

Execution:
```bash
# Load TC definitions
psql $PG_DSN -f db/02-seed.sql    # includes initial TC rows
# Run suite, capture results
pytest tests/e2e/ -v --junitxml=reports/e2e.xml