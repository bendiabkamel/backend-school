-- 007_exam_structure.sql
-- School exam entities separated from existing e-learning exam table.

CREATE TABLE IF NOT EXISTS school_exams (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  academic_session_id UUID NOT NULL REFERENCES academic_sessions(id) ON DELETE CASCADE,
  semester_id UUID NOT NULL REFERENCES semesters(id) ON DELETE CASCADE,
  class_id UUID NOT NULL REFERENCES school_classes(id) ON DELETE CASCADE,
  section_id UUID NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
  course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  exam_name VARCHAR(160) NOT NULL,
  exam_type VARCHAR(30) NOT NULL
    CHECK (exam_type IN ('quiz', 'midterm', 'final', 'assignment', 'practical', 'oral', 'continuous')),
  starts_at TIMESTAMPTZ NOT NULL,
  ends_at TIMESTAMPTZ NOT NULL,
  max_marks NUMERIC(6,2) NOT NULL DEFAULT 100 CHECK (max_marks > 0),
  pass_marks NUMERIC(6,2) NOT NULL DEFAULT 0,
  weight_percent NUMERIC(5,2) NOT NULL DEFAULT 100 CHECK (weight_percent > 0 AND weight_percent <= 100),
  is_published BOOLEAN NOT NULL DEFAULT FALSE,
  created_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  updated_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT chk_school_exams_time CHECK (ends_at > starts_at),
  CONSTRAINT chk_school_exams_pass_marks CHECK (pass_marks >= 0 AND pass_marks <= max_marks),
  CONSTRAINT uq_school_exams_context
    UNIQUE (academic_session_id, semester_id, class_id, section_id, course_id, exam_name, exam_type, starts_at)
);

CREATE INDEX IF NOT EXISTS idx_school_exams_session
  ON school_exams(academic_session_id);

CREATE INDEX IF NOT EXISTS idx_school_exams_semester
  ON school_exams(semester_id);

CREATE INDEX IF NOT EXISTS idx_school_exams_context_lookup
  ON school_exams(class_id, section_id, course_id, starts_at);

CREATE INDEX IF NOT EXISTS idx_school_exams_published
  ON school_exams(is_published);

CREATE TABLE IF NOT EXISTS exam_rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  school_exam_id UUID NOT NULL REFERENCES school_exams(id) ON DELETE CASCADE,
  rule_name VARCHAR(120) NOT NULL DEFAULT 'default',
  total_marks NUMERIC(6,2) NOT NULL CHECK (total_marks > 0),
  pass_marks NUMERIC(6,2) NOT NULL CHECK (pass_marks >= 0),
  marks_distribution_note TEXT,
  allow_retake BOOLEAN NOT NULL DEFAULT FALSE,
  max_attempts INTEGER NOT NULL DEFAULT 1 CHECK (max_attempts >= 1),
  created_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  updated_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT chk_exam_rules_pass_marks CHECK (pass_marks <= total_marks),
  CONSTRAINT uq_exam_rules_exam UNIQUE (school_exam_id)
);

CREATE INDEX IF NOT EXISTS idx_exam_rules_exam
  ON exam_rules(school_exam_id);

CREATE INDEX IF NOT EXISTS idx_exam_rules_created_by
  ON exam_rules(created_by_user_id);
