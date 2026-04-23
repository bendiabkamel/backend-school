-- 006_academic_settings.sql
-- Academic behavior toggles and submission windows.

CREATE TABLE IF NOT EXISTS academic_settings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  settings_scope VARCHAR(20) NOT NULL DEFAULT 'global'
    CHECK (settings_scope IN ('global', 'session')),
  academic_session_id UUID REFERENCES academic_sessions(id) ON DELETE CASCADE,
  attendance_mode VARCHAR(20) NOT NULL DEFAULT 'section'
    CHECK (attendance_mode IN ('section', 'course')),
  marks_submission_status VARCHAR(10) NOT NULL DEFAULT 'off'
    CHECK (marks_submission_status IN ('on', 'off')),
  grading_policy VARCHAR(30) NOT NULL DEFAULT 'percentage',
  promotion_policy VARCHAR(30) NOT NULL DEFAULT 'manual',
  created_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  updated_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT chk_academic_settings_scope_fk
    CHECK (
      (settings_scope = 'global' AND academic_session_id IS NULL)
      OR (settings_scope = 'session' AND academic_session_id IS NOT NULL)
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_academic_settings_global
  ON academic_settings(settings_scope)
  WHERE settings_scope = 'global';

CREATE UNIQUE INDEX IF NOT EXISTS uq_academic_settings_per_session
  ON academic_settings(academic_session_id)
  WHERE settings_scope = 'session';

CREATE INDEX IF NOT EXISTS idx_academic_settings_created_by
  ON academic_settings(created_by_user_id);
