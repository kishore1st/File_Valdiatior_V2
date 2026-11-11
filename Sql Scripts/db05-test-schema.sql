CREATE SCHEMA IF NOT EXISTS fvi_test;

CREATE TABLE fvi_test.test_runs (
  run_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_name    VARCHAR(128) NOT NULL,
  suite       VARCHAR(32) NOT NULL CHECK (suite IN ('SMOKE','E2E','REGRESSION')),
  git_sha     VARCHAR(40),
  environment VARCHAR(16) NOT NULL CHECK (environment IN ('local','dev','staging','prod')),
  started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at TIMESTAMPTZ,
  status      VARCHAR(16) NOT NULL DEFAULT 'RUNNING'
              CHECK (status IN ('RUNNING','PASSED','FAILED','ABORTED')),
  summary     JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE fvi_test.test_cases (
  case_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_code     VARCHAR(24) NOT NULL UNIQUE,
  requirement   VARCHAR(32) NOT NULL,
  title         VARCHAR(255) NOT NULL,
  preconditions TEXT,
  steps         JSONB NOT NULL DEFAULT '[]',
  expected      TEXT NOT NULL,
  priority      VARCHAR(8) NOT NULL CHECK (priority IN ('P0','P1','P2')),
  is_active     BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE fvi_test.test_results (
  result_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id        UUID NOT NULL REFERENCES fvi_test.test_runs(run_id) ON DELETE CASCADE,
  case_id       UUID NOT NULL REFERENCES fvi_test.test_cases(case_id),
  actual        TEXT,
  status        VARCHAR(12) NOT NULL CHECK (status IN ('PASS','FAIL','SKIP','BLOCKED')),
  duration_ms   INT,
  correlation_id UUID,
  evidence      JSONB,
  executed_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (run_id, case_id)
);
CREATE INDEX ix_test_results_fail ON fvi_test.test_results(run_id, executed_at DESC)
  WHERE status = 'FAIL';

CREATE TABLE fvi_test.defects (
  defect_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  result_id   UUID REFERENCES fvi_test.test_results(result_id),
  title       VARCHAR(255) NOT NULL,
  description TEXT NOT NULL,
  severity    VARCHAR(8) NOT NULL CHECK (severity IN ('S1','S2','S3','S4')),
  status      VARCHAR(16) NOT NULL DEFAULT 'OPEN'
              CHECK (status IN ('OPEN','IN_PROGRESS','RESOLVED','CLOSED','WONT_FIX')),
  assigned_to UUID REFERENCES fvi.users(user_id),
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  resolved_at TIMESTAMPTZ
);

CREATE TABLE fvi_test.perf_test_runs (
  perf_run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scenario    VARCHAR(64) NOT NULL,
  tool        VARCHAR(32) NOT NULL,
  target_env  VARCHAR(16) NOT NULL,
  config      JSONB NOT NULL,
  started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at TIMESTAMPTZ,
  status      VARCHAR(16) NOT NULL DEFAULT 'RUNNING'
              CHECK (status IN ('RUNNING','COMPLETED','ABORTED')),
  summary     JSONB
);

CREATE TABLE fvi_test.perf_metrics (
  metric_id   BIGSERIAL PRIMARY KEY,
  perf_run_id UUID NOT NULL REFERENCES fvi_test.perf_test_runs(perf_run_id) ON DELETE CASCADE,
  sampled_at  TIMESTAMPTZ NOT NULL,
  metric_name VARCHAR(64) NOT NULL,
  value       DOUBLE PRECISION NOT NULL,
  dimensions  JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX ix_perf_metrics_run
  ON fvi_test.perf_metrics(perf_run_id, metric_name, sampled_at);