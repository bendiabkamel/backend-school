-- 010_attendance_sessions_records.sql
-- Attendance split model: session header + per-enrollment records.

CREATE TABLE IF NOT EXISTS attendance_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  academic_session_id UUID NOT NULL REFERENCES academic_sessions(id) ON DELETE CASCADE,
  semester_id UUID NOT NULL REFERENCES semesters(id) ON DELETE CASCADE,
  class_id UUID NOT NULL REFERENCES school_classes(id) ON DELETE CASCADE,
  section_id UUID NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
  course_id UUID REFERENCES courses(id) ON DELETE SET NULL,
  attendance_mode VARCHAR(20) NOT NULL DEFAULT 'section'
    CHECK (attendance_mode IN ('section', 'course')),
  attendance_date DATE NOT NULL,
  slot_code VARCHAR(60) NOT NULL DEFAULT 'default',
  notes TEXT,
  marked_by_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_attendance_sessions_context
  ON attendance_sessions(
    academic_session_id,
    semester_id,
    class_id,
    section_id,
    COALESCE(course_id, '00000000-0000-0000-0000-000000000000'::uuid),
    attendance_date,
    slot_code
  );

CREATE INDEX IF NOT EXISTS idx_attendance_sessions_session_date
  ON attendance_sessions(academic_session_id, attendance_date);

CREATE INDEX IF NOT EXISTS idx_attendance_sessions_context
  ON attendance_sessions(class_id, section_id, course_id);

CREATE INDEX IF NOT EXISTS idx_attendance_sessions_marked_by
  ON attendance_sessions(marked_by_user_id);

CREATE TABLE IF NOT EXISTS attendance_records (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  attendance_session_id UUID NOT NULL REFERENCES attendance_sessions(id) ON DELETE CASCADE,
  enrollment_id UUID NOT NULL REFERENCES student_enrollments(id) ON DELETE CASCADE,
  owner_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  attendance_status VARCHAR(20) NOT NULL
    CHECK (attendance_status IN ('present', 'absent', 'late', 'excused')),
  remarks TEXT,
  recorded_by_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_attendance_records_single UNIQUE (attendance_session_id, enrollment_id)
);

CREATE INDEX IF NOT EXISTS idx_attendance_records_enrollment
  ON attendance_records(enrollment_id);

CREATE INDEX IF NOT EXISTS idx_attendance_records_owner
  ON attendance_records(owner_user_id);

CREATE INDEX IF NOT EXISTS idx_attendance_records_status
  ON attendance_records(attendance_status);

CREATE INDEX IF NOT EXISTS idx_attendance_records_recorded_by
  ON attendance_records(recorded_by_user_id);
