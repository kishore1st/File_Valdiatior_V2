CREATE VIEW fvi.v_file_status AS
SELECT f.file_id, f.file_name, f.sha256_hash, f.region_code, f.schema_type_key,
       f.status AS current_status, f.latest_validation_status, f.batch_id,
       b.correlation_id, f.destination_path,
       t.transfer_status, t.attempt_number,
       r.is_consistent
FROM   fvi.files f
LEFT   JOIN fvi.upload_batches b ON b.batch_id = f.batch_id
LEFT   JOIN LATERAL (
  SELECT status AS transfer_status, attempt_number
  FROM fvi.transfers
  WHERE file_id = f.file_id
  ORDER BY attempt_number DESC LIMIT 1
) t ON TRUE
LEFT   JOIN fvi.reconciliation r ON r.file_id = f.file_id;

CREATE VIEW fvi.v_batch_summary AS
SELECT b.batch_id, b.correlation_id, b.user_id, b.schema_type_key,
       b.total_files,
       COUNT(*) FILTER (WHERE f.status='PROCESSING_COMPLETED')  AS succeeded,
       COUNT(*) FILTER (WHERE f.status='DUPLICATE_DETECTED')    AS duplicates,
       COUNT(*) FILTER (WHERE f.status='VALIDATION_FAILED')     AS validation_failed,
       COUNT(*) FILTER (WHERE f.status='PROCESSING_FAILED')     AS processing_failed,
       COUNT(*) FILTER (WHERE f.status NOT IN
             ('PROCESSING_COMPLETED','DUPLICATE_DETECTED',
              'VALIDATION_FAILED','PROCESSING_FAILED'))          AS in_progress
FROM   fvi.upload_batches b
LEFT   JOIN fvi.files f ON f.batch_id = b.batch_id
GROUP  BY b.batch_id;

CREATE VIEW fvi.v_duplicate_attempts AS
SELECT f.file_id, f.batch_id, b.correlation_id, b.user_id,
       f.file_name, f.sha256_hash, f.reject_reason, f.created_at
FROM   fvi.files f
JOIN   fvi.upload_batches b ON b.batch_id = f.batch_id
WHERE  f.status = 'DUPLICATE_DETECTED';