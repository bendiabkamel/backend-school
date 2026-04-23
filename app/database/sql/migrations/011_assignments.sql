-- 011_assignments.sql
-- Assignment publication and submissions.

CREATE TABLE IF NOT EXISTS assignments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  academic_session_id UUID NOT NULL REFERENCES academic_sessions(id) ON DELETE CASCADE,
  semester_id UUID NOT NULL REFERENCES semesters(id) ON DELETE CASCADE,
  class_id UUID NOT NULL REFERENCES school_classes(id) ON DELETE CASCADE,
  section_id UUID NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
  course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  teacher_assignment_id UUID REFERENCES teacher_assignments(id) ON DELETE SET NULL,
  assignment_name VARCHAR(220) NOT NULL,
  description TEXT,
  instructions TEXT,
  attachment_path TEXT,
  assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  due_at TIMESTAMPTZ,
  max_score NUMERIC(6,2) NOT NULL DEFAULT 100 CHECK (max_score > 0),
  allow_late_submission BOOLEAN NOT NULL DEFAULT FALSE,
  is_published BOOLEAN NOT NULL DEFAULT FALSE,
  created_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  updated_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT chk_assignments_due_after_assigned CHECK (due_at IS NULL OR due_at >= assigned_at),
  CONSTRAINT uq_assignments_context_name
    UNIQUE (academic_session_id, semester_id, class_id, section_id, course_id, assignment_name)
);

CREATE INDEX IF NOT EXISTS idx_assignments_context
  ON assignments(academic_session_id, semester_id, class_id, section_id, course_id);

CREATE INDEX IF NOT EXISTS idx_assignments_due_at
  ON assignments(due_at);

CREATE INDEX IF NOT EXISTS idx_assignments_published
  ON assignments(is_published);

CREATE INDEX IF NOT EXISTS idx_assignments_created_by
  ON assignments(created_by_user_id);

CREATE TABLE IF NOT EXISTS assignment_submissions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  assignment_id UUID NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
  enrollment_id UUID NOT NULL REFERENCES student_enrollments(id) ON DELETE CASCADE,
  owner_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  attempt_no INTEGER NOT NULL DEFAULT 1 CHECK (attempt_no >= 1),
  submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  submission_path TEXT,
  submission_text TEXT,
  submission_status VARCHAR(20) NOT NULL DEFAULT 'submitted'
    CHECK (submission_status IN ('draft', 'submitted', 'resubmitted', 'graded', 'late', 'rejected')),
  score NUMERIC(6,2) CHECK (score IS NULL OR score >= 0),
  feedback TEXT,
  graded_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  graded_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_assignment_submissions_attempt
    UNIQUE (assignment_id, enrollment_id, attempt_no)
);

CREATE INDEX IF NOT EXISTS idx_assignment_submissions_assignment
  ON assignment_submissions(assignment_id);

CREATE INDEX IF NOT EXISTS idx_assignment_submissions_enrollment
  ON assignment_submissions(enrollment_id);

CREATE INDEX IF NOT EXISTS idx_assignment_submissions_owner
  ON assignment_submissions(owner_user_id);

CREATE INDEX IF NOT EXISTS idx_assignment_submissions_status
  ON assignment_submissions(submission_status);
