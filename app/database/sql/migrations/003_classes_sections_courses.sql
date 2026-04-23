-- 003_classes_sections_courses.sql
-- Core academic structure: classes, sections, courses.

CREATE TABLE IF NOT EXISTS school_classes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  academic_session_id UUID NOT NULL REFERENCES academic_sessions(id) ON DELETE CASCADE,
  class_name VARCHAR(120) NOT NULL,
  display_order INTEGER NOT NULL DEFAULT 0,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  updated_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_school_classes_name_per_session UNIQUE (academic_session_id, class_name)
);

CREATE INDEX IF NOT EXISTS idx_school_classes_session
  ON school_classes(academic_session_id);

CREATE INDEX IF NOT EXISTS idx_school_classes_is_active
  ON school_classes(is_active);

CREATE INDEX IF NOT EXISTS idx_school_classes_created_by
  ON school_classes(created_by_user_id);

CREATE TABLE IF NOT EXISTS sections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  academic_session_id UUID NOT NULL REFERENCES academic_sessions(id) ON DELETE CASCADE,
  class_id UUID NOT NULL REFERENCES school_classes(id) ON DELETE CASCADE,
  section_name VARCHAR(120) NOT NULL,
  room_no VARCHAR(60),
  capacity INTEGER CHECK (capacity IS NULL OR capacity > 0),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  updated_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_sections_name_per_class_session UNIQUE (academic_session_id, class_id, section_name)
);

CREATE INDEX IF NOT EXISTS idx_sections_session
  ON sections(academic_session_id);

CREATE INDEX IF NOT EXISTS idx_sections_class
  ON sections(class_id);

CREATE INDEX IF NOT EXISTS idx_sections_is_active
  ON sections(is_active);

CREATE INDEX IF NOT EXISTS idx_sections_created_by
  ON sections(created_by_user_id);

CREATE TABLE IF NOT EXISTS courses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  academic_session_id UUID NOT NULL REFERENCES academic_sessions(id) ON DELETE CASCADE,
  semester_id UUID NOT NULL REFERENCES semesters(id) ON DELETE CASCADE,
  class_id UUID NOT NULL REFERENCES school_classes(id) ON DELETE CASCADE,
  course_name VARCHAR(200) NOT NULL,
  course_code VARCHAR(60),
  course_type VARCHAR(30) NOT NULL DEFAULT 'core'
    CHECK (course_type IN ('core', 'elective', 'lab', 'activity')),
  credit_hours NUMERIC(4,2) NOT NULL DEFAULT 0 CHECK (credit_hours >= 0),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  updated_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_courses_name_context UNIQUE (academic_session_id, semester_id, class_id, course_name)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_courses_code_per_session
  ON courses(academic_session_id, course_code)
  WHERE course_code IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_courses_session
  ON courses(academic_session_id);

CREATE INDEX IF NOT EXISTS idx_courses_semester
  ON courses(semester_id);

CREATE INDEX IF NOT EXISTS idx_courses_class
  ON courses(class_id);

CREATE INDEX IF NOT EXISTS idx_courses_is_active
  ON courses(is_active);

CREATE INDEX IF NOT EXISTS idx_courses_created_by
  ON courses(created_by_user_id);
