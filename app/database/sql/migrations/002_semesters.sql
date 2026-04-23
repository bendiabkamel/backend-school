-- 002_semesters.sql
-- Academic terms within an academic session.

CREATE TABLE IF NOT EXISTS semesters (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  academic_session_id UUID NOT NULL REFERENCES academic_sessions(id) ON DELETE CASCADE,
  semester_name VARCHAR(80) NOT NULL,
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  updated_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT chk_semesters_dates CHECK (end_date >= start_date),
  CONSTRAINT uq_semesters_name_per_session UNIQUE (academic_session_id, semester_name)
);

CREATE INDEX IF NOT EXISTS idx_semesters_academic_session
  ON semesters(academic_session_id);

CREATE INDEX IF NOT EXISTS idx_semesters_is_active
  ON semesters(is_active);

CREATE INDEX IF NOT EXISTS idx_semesters_date_range
  ON semesters(start_date, end_date);

CREATE INDEX IF NOT EXISTS idx_semesters_created_by
  ON semesters(created_by_user_id);
