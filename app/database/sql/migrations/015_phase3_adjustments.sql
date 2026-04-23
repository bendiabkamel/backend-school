-- 015_phase3_adjustments.sql
-- Phase 3 schema adjustments for backend service parity.

ALTER TABLE school_exams
  ADD COLUMN IF NOT EXISTS is_locked BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE final_marks
  ADD COLUMN IF NOT EXISTS grade_snapshot JSONB NOT NULL DEFAULT '{}'::JSONB;

CREATE TABLE IF NOT EXISTS syllabi (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  academic_session_id UUID NOT NULL REFERENCES academic_sessions(id) ON DELETE CASCADE,
  semester_id UUID NOT NULL REFERENCES semesters(id) ON DELETE CASCADE,
  class_id UUID NOT NULL REFERENCES school_classes(id) ON DELETE CASCADE,
  course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  title VARCHAR(220) NOT NULL,
  syllabus_path TEXT,
  content TEXT,
  is_published BOOLEAN NOT NULL DEFAULT FALSE,
  created_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  updated_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_syllabi_context_title UNIQUE (academic_session_id, semester_id, class_id, course_id, title)
);

CREATE INDEX IF NOT EXISTS idx_syllabi_session
  ON syllabi(academic_session_id);

CREATE INDEX IF NOT EXISTS idx_syllabi_semester
  ON syllabi(semester_id);

CREATE INDEX IF NOT EXISTS idx_syllabi_class_course
  ON syllabi(class_id, course_id);
