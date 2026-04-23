-- 012_routines_events_notices.sql
-- Timetables, calendar events, and notices.

CREATE TABLE IF NOT EXISTS routines (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  academic_session_id UUID NOT NULL REFERENCES academic_sessions(id) ON DELETE CASCADE,
  semester_id UUID NOT NULL REFERENCES semesters(id) ON DELETE CASCADE,
  class_id UUID NOT NULL REFERENCES school_classes(id) ON DELETE CASCADE,
  section_id UUID NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
  course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  teacher_assignment_id UUID REFERENCES teacher_assignments(id) ON DELETE SET NULL,
  weekday SMALLINT NOT NULL CHECK (weekday BETWEEN 1 AND 7),
  start_time TIME NOT NULL,
  end_time TIME NOT NULL,
  room_no VARCHAR(60),
  created_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  updated_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT chk_routines_time CHECK (end_time > start_time),
  CONSTRAINT uq_routines_slot UNIQUE (
    academic_session_id,
    semester_id,
    class_id,
    section_id,
    course_id,
    weekday,
    start_time,
    end_time
  )
);

CREATE INDEX IF NOT EXISTS idx_routines_context
  ON routines(academic_session_id, semester_id, class_id, section_id, course_id);

CREATE INDEX IF NOT EXISTS idx_routines_teacher_assignment
  ON routines(teacher_assignment_id);

CREATE INDEX IF NOT EXISTS idx_routines_created_by
  ON routines(created_by_user_id);

CREATE TABLE IF NOT EXISTS events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  academic_session_id UUID NOT NULL REFERENCES academic_sessions(id) ON DELETE CASCADE,
  event_title VARCHAR(220) NOT NULL,
  event_type VARCHAR(30) NOT NULL DEFAULT 'general'
    CHECK (event_type IN ('academic', 'exam', 'holiday', 'meeting', 'general')),
  starts_at TIMESTAMPTZ NOT NULL,
  ends_at TIMESTAMPTZ NOT NULL,
  location VARCHAR(220),
  description TEXT,
  audience_scope VARCHAR(20) NOT NULL DEFAULT 'all'
    CHECK (audience_scope IN ('all', 'students', 'teachers', 'class', 'section')),
  class_id UUID REFERENCES school_classes(id) ON DELETE SET NULL,
  section_id UUID REFERENCES sections(id) ON DELETE SET NULL,
  created_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  updated_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT chk_events_time CHECK (ends_at >= starts_at),
  CONSTRAINT uq_events_title_start UNIQUE (academic_session_id, event_title, starts_at)
);

CREATE INDEX IF NOT EXISTS idx_events_session_time
  ON events(academic_session_id, starts_at, ends_at);

CREATE INDEX IF NOT EXISTS idx_events_audience
  ON events(audience_scope, class_id, section_id);

CREATE INDEX IF NOT EXISTS idx_events_created_by
  ON events(created_by_user_id);

CREATE TABLE IF NOT EXISTS notices (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  academic_session_id UUID NOT NULL REFERENCES academic_sessions(id) ON DELETE CASCADE,
  title VARCHAR(220) NOT NULL,
  body TEXT NOT NULL,
  audience_scope VARCHAR(20) NOT NULL DEFAULT 'all'
    CHECK (audience_scope IN ('all', 'students', 'teachers', 'class', 'section')),
  class_id UUID REFERENCES school_classes(id) ON DELETE SET NULL,
  section_id UUID REFERENCES sections(id) ON DELETE SET NULL,
  published_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ,
  is_pinned BOOLEAN NOT NULL DEFAULT FALSE,
  created_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  updated_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT chk_notices_expiry CHECK (expires_at IS NULL OR expires_at >= published_at)
);

CREATE INDEX IF NOT EXISTS idx_notices_session_published
  ON notices(academic_session_id, published_at DESC);

CREATE INDEX IF NOT EXISTS idx_notices_audience
  ON notices(audience_scope, class_id, section_id);

CREATE INDEX IF NOT EXISTS idx_notices_pinned
  ON notices(is_pinned);
