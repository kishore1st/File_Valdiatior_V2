# Test Cases (Req 27 + 30 + 31 + 32)

| TC     | Req    | Priority | Scenario                                         | Expected                                                       |
|--------|--------|----------|--------------------------------------------------|----------------------------------------------------------------|
| TC-01  | Req-3  | P0       | Upload valid CSV                                 | 202, batch created, file QUEUED → APPROVED → TRANSFERRED       |
| TC-02  | Req-16 | P0       | Same file from two users concurrently            | 1 success, 1 DUPLICATE_DETECTED                                |
| TC-03  | Req-19 | P0       | 10 concurrent identical uploads                  | Exactly 1 `files` row                                          |
| TC-04  | Req-24 | P0       | Batch with 2 schema types                        | 422, batch not created                                         |
| TC-05  | Req-26 | P0       | 5-file batch, 1 duplicate                        | 4 complete, 1 duplicate, batch PARTIAL_SUCCESS                 |
| TC-06  | Req-6  | P1       | CSV with wrong-type value                        | VALIDATION_FAILED + mismatch in `file_events.payload`          |
| TC-07  | Req-10 | P0       | Approved file transferred                        | `transfers.SUCCESS`, `destination_path` populated              |
| TC-08  | Req-21 | P1       | Databricks 503 ×3 then 200                       | 3 transfer rows, last SUCCESS                                  |
| TC-09  | Req-13 | P0       | Auto Loader ingest + audit sync                  | `reconciliation.is_consistent = true`                          |
| TC-10  | Req-2  | P0       | Token without uploader role                      | 403                                                            |
| TC-11  | Req-28C| P1       | Expired token                                    | 401                                                            |
| TC-12  | Req-28C| P1       | Logout revokes session                           | `sso_sessions.revoked_at` set; subsequent 401                  |
| TC-13  | Req-30A| P0       | File dropped to internal SFTP                    | Event REGISTERED, file TRANSFERRED                             |
| TC-14  | Req-30A| P0       | Same file dropped to SFTP again                  | discovery UNIQUE → SKIPPED; `file_events` DUPLICATE            |
| TC-15  | Req-30B| P0       | File appears in staging Volume                   | Event processed, transferred                                   |
| TC-16  | Req-30C| P0       | Graph change notification arrives                | Fetched via Graph, registered, transferred                     |
| TC-17  | Req-30 | P0       | Same file via UI AND SFTP within 5s              | Exactly 1 `files` row                                          |
| TC-18  | Req-30 | P1       | Connector fetch fails twice then succeeds        | INGEST_FAILED → INGEST_FETCHED, then transferred               |
| TC-19  | Req-30 | P1       | Source paused mid-flight                         | New events IGNORED with reason                                 |
| TC-20  | Req-31A| P0       | SFTP folder 5 new + 100 historical               | Only 5 events; watermark advanced                              |
| TC-21  | Req-31A| P0       | File re-uploaded to SFTP (new mtime)             | New discovery row; `files` UNIQUE → DUPLICATE                  |
| TC-22  | Req-31B| P0       | 3 new Volume files                               | 3 events; existing files not rescanned                         |
| TC-23  | Req-31C| P0       | SharePoint file modified (new eTag)              | New discovery row; prior version untouched                     |
| TC-24  | Req-31C| P0       | Graph webhook missed, delta poll catches up      | 0 duplicates; watermark advances from `source_cursor`          |
| TC-25  | Req-32 | P0       | Two watcher ticks on same location concurrently  | Only one advances the watermark                                |
| TC-26  | Req-32 | P1       | Manual reset to now()-24h                        | Re-discovers 24h files; UNIQUE index skips processed ones      |
| TC-27  | Req-32 | P1       | Watcher fails 5×                                 | `watermarks.status='PAUSED'`, alert event recorded             |
| TC-28  | Req-32 | P1       | 5 locations tick concurrently                    | Each watermark updated independently                           |