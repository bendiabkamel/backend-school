-- 005_teacher_assignments.sql
-- Teacher to academic context mapping.

CREATE TABLE IF NOT EXISTS teacher_assignments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  teacher_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  academic_session_id UUID NOT NULL REFERENCES academic_sessions(id) ON DELETE CASCADE,
  semester_id UUID NOT NULL REFERENCES semesters(id) ON DELETE CASCADE,
  class_id UUID NOT NULL REFERENCES school_classes(id) ON DELETE CASCADE,
  section_id UUID NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
  course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  assignment_role VARCHAR(20) NOT NULL DEFAULT 'primary'
    CHECK (assignment_role IN ('primary', 'assistant', 'substitute')),
  assigned_from DATE NOT NULL DEFAULT CURRENT_DATE,
  assigned_to DATE,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  assigned_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT chk_teacher_assignments_dates
    CHECK (assigned_to IS NULL OR assigned_to >= assigned_from),
  CONSTRAINT uq_teacher_assignments_context
    UNIQUE (teacher_id, academic_session_id, semester_id, class_id, section_id, course_id)
);

CREATE INDEX IF NOT EXISTS idx_teacher_assignments_teacher
  ON teacher_assignments(teacher_id);

CREATE INDEX IF NOT EXISTS idx_teacher_assignments_session
  ON teacher_assignments(academic_session_id);

CREATE INDEX IF NOT EXISTS idx_teacher_assignments_semester
  ON teacher_assignments(semester_id);

CREATE INDEX IF NOT EXISTS idx_teacher_assignments_context_lookup
  ON teacher_assignments(class_id, section_id, course_id, is_active);

CREATE INDEX IF NOT EXISTS idx_teacher_assignments_assigned_by
  ON teacher_assignments(assigned_by_user_id);
