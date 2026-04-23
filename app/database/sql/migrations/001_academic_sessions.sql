-- 001_academic_sessions.sql
-- Academic year/session root table.

CREATE TABLE IF NOT EXISTS academic_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_name VARCHAR(120) NOT NULL,
  starts_on DATE,
  ends_on DATE,
  is_current BOOLEAN NOT NULL DEFAULT FALSE,
  status VARCHAR(20) NOT NULL DEFAULT 'active'
    CHECK (status IN ('draft', 'active', 'closed', 'archived')),
  created_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  updated_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT chk_academic_sessions_dates
    CHECK (starts_on IS NULL OR ends_on IS NULL OR ends_on >= starts_on)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_academic_sessions_session_name
  ON academic_sessions(session_name);

CREATE UNIQUE INDEX IF NOT EXISTS uq_academic_sessions_single_current
  ON academic_sessions(is_current)
  WHERE is_current = TRUE;

CREATE INDEX IF NOT EXISTS idx_academic_sessions_status
  ON academic_sessions(status);

CREATE INDEX IF NOT EXISTS idx_academic_sessions_date_range
  ON academic_sessions(starts_on, ends_on);

CREATE INDEX IF NOT EXISTS idx_academic_sessions_created_by
  ON academic_sessions(created_by_user_id);
