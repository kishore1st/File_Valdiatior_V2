-- Atomic registration with duplicate detection.
-- Called from FastAPI on every new file (browser or channel).
CREATE OR REPLACE FUNCTION fvi.register_file(
  p_batch           UUID,
  p_sha             CHAR(64),
  p_name            VARCHAR,
  p_size            BIGINT,
  p_ext             VARCHAR,
  p_region          VARCHAR,
  p_stype           VARCHAR,
  p_user            UUID,
  p_host            VARCHAR,
  p_ip              INET,
  p_source_id       UUID,
  p_source_ref      VARCHAR
) RETURNS TABLE (file_id UUID, is_duplicate BOOLEAN) AS $$
DECLARE v UUID;
BEGIN
  SELECT f.file_id INTO v FROM fvi.files f WHERE f.sha256_hash = p_sha;
  IF v IS NOT NULL THEN
    RETURN QUERY SELECT v, TRUE;
    RETURN;
  END IF;
  BEGIN
    RETURN QUERY
    INSERT INTO fvi.files
      (batch_id, sha256_hash, file_name, file_size_bytes, file_extension,
       region_code, schema_type_key, uploaded_by, machine_host, ip_address,
       source_id, source_ref)
    VALUES
      (p_batch, p_sha, p_name, p_size, p_ext,
       p_region, p_stype, p_user, p_host, p_ip,
       p_source_id, p_source_ref)
    RETURNING files.file_id, FALSE;
  EXCEPTION WHEN unique_violation THEN
    SELECT f.file_id INTO v FROM fvi.files f WHERE f.sha256_hash = p_sha;
    RETURN QUERY SELECT v, TRUE;
  END;
END;
$$ LANGUAGE plpgsql;