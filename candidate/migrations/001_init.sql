CREATE TABLE IF NOT EXISTS workflows (
  id TEXT PRIMARY KEY,
  request_key TEXT NOT NULL,
  workflow_type TEXT NOT NULL,
  resource_id TEXT NOT NULL,
  state TEXT NOT NULL,
  external_job_id TEXT,
  requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  lease_expires_at TIMESTAMPTZ,
  last_error TEXT,
  last_external_state TEXT,
  recommended_action TEXT
);

CREATE TABLE IF NOT EXISTS workflow_attempts (
  id BIGSERIAL PRIMARY KEY,
  workflow_id TEXT NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
  attempt_no INTEGER NOT NULL,
  action TEXT NOT NULL,
  status TEXT NOT NULL,
  external_job_id TEXT,
  error TEXT,
  evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS workflow_audit (
  id BIGSERIAL PRIMARY KEY,
  workflow_id TEXT NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
  event_key TEXT,
  event_type TEXT NOT NULL,
  details JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_workflows_request_key ON workflows(request_key);
CREATE INDEX IF NOT EXISTS idx_workflows_state_updated ON workflows(state, updated_at);
CREATE INDEX IF NOT EXISTS idx_attempts_workflow ON workflow_attempts(workflow_id, attempt_no);
CREATE INDEX IF NOT EXISTS idx_audit_workflow_key ON workflow_audit(workflow_id, event_key);

