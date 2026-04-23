-- 009_marks_final_marks.sql
-- Raw marks and consolidated final marks.

CREATE TABLE IF NOT EXISTS marks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  enrollment_id UUID NOT NULL REFERENCES student_enrollments(id) ON DELETE CASCADE,
  owner_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  school_exam_id UUID NOT NULL REFERENCES school_exams(id) ON DELETE CASCADE,
  exam_rule_id UUID REFERENCES exam_rules(id) ON DELETE SET NULL,
  marks_obtained NUMERIC(6,2) NOT NULL DEFAULT 0 CHECK (marks_obtained >= 0),
  is_absent BOOLEAN NOT NULL DEFAULT FALSE,
  is_excused BOOLEAN NOT NULL DEFAULT FALSE,
  remarks TEXT,
  entered_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT chk_marks_absent_value CHECK (is_absent = FALSE OR marks_obtained = 0),
  CONSTRAINT uq_marks_exam_enrollment UNIQUE (school_exam_id, enrollment_id)
);

CREATE INDEX IF NOT EXISTS idx_marks_enrollment
  ON marks(enrollment_id);

CREATE INDEX IF NOT EXISTS idx_marks_owner
  ON marks(owner_user_id);

CREATE INDEX IF NOT EXISTS idx_marks_exam
  ON marks(school_exam_id);

CREATE INDEX IF NOT EXISTS idx_marks_entered_by
  ON marks(entered_by_user_id);

CREATE TABLE IF NOT EXISTS final_marks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  enrollment_id UUID NOT NULL REFERENCES student_enrollments(id) ON DELETE CASCADE,
  owner_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  academic_session_id UUID NOT NULL REFERENCES academic_sessions(id) ON DELETE CASCADE,
  semester_id UUID NOT NULL REFERENCES semesters(id) ON DELETE CASCADE,
  course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  grading_system_id UUID REFERENCES grading_systems(id) ON DELETE SET NULL,
  grade_rule_id UUID REFERENCES grade_rules(id) ON DELETE SET NULL,
  calculated_marks NUMERIC(6,2) NOT NULL DEFAULT 0 CHECK (calculated_marks >= 0),
  final_marks NUMERIC(6,2) NOT NULL DEFAULT 0 CHECK (final_marks >= 0),
  grade_label VARCHAR(20),
  grade_point NUMERIC(4,2) CHECK (grade_point IS NULL OR grade_point >= 0),
  note TEXT,
  finalized_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  finalized_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_final_marks_target UNIQUE (enrollment_id, semester_id, course_id)
);

CREATE INDEX IF NOT EXISTS idx_final_marks_enrollment
  ON final_marks(enrollment_id);

CREATE INDEX IF NOT EXISTS idx_final_marks_owner
  ON final_marks(owner_user_id);

CREATE INDEX IF NOT EXISTS idx_final_marks_session_semester
  ON final_marks(academic_session_id, semester_id);

CREATE INDEX IF NOT EXISTS idx_final_marks_course
  ON final_marks(course_id);

CREATE INDEX IF NOT EXISTS idx_final_marks_grade_rule
  ON final_marks(grade_rule_id);
