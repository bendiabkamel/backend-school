-- 004_student_enrollments.sql
-- Canonical student academic membership (normalization anchor).

CREATE TABLE IF NOT EXISTS student_enrollments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  owner_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  academic_session_id UUID NOT NULL REFERENCES academic_sessions(id) ON DELETE CASCADE,
  semester_id UUID NOT NULL REFERENCES semesters(id) ON DELETE CASCADE,
  class_id UUID NOT NULL REFERENCES school_classes(id) ON DELETE CASCADE,
  section_id UUID NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
  enrollment_status VARCHAR(20) NOT NULL DEFAULT 'active'
    CHECK (enrollment_status IN ('active', 'promoted', 'repeated', 'transferred', 'withdrawn', 'graduated', 'inactive')),
  enrolled_on DATE NOT NULL DEFAULT CURRENT_DATE,
  exited_on DATE,
  enrollment_no VARCHAR(80),
  notes TEXT,
  created_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  updated_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT chk_student_enrollments_dates
    CHECK (exited_on IS NULL OR exited_on >= enrolled_on),
  CONSTRAINT uq_student_enrollments_context
    UNIQUE (student_id, academic_session_id, semester_id, class_id, section_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_student_enrollments_no
  ON student_enrollments(enrollment_no)
  WHERE enrollment_no IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_student_enrollments_active_per_session
  ON student_enrollments(student_id, academic_session_id)
  WHERE enrollment_status = 'active';

CREATE INDEX IF NOT EXISTS idx_student_enrollments_student
  ON student_enrollments(student_id);

CREATE INDEX IF NOT EXISTS idx_student_enrollments_owner
  ON student_enrollments(owner_user_id);

CREATE INDEX IF NOT EXISTS idx_student_enrollments_session_status
  ON student_enrollments(academic_session_id, enrollment_status);

CREATE INDEX IF NOT EXISTS idx_student_enrollments_semester
  ON student_enrollments(semester_id);

CREATE INDEX IF NOT EXISTS idx_student_enrollments_class_section
  ON student_enrollments(class_id, section_id);
