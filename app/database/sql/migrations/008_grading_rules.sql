-- 008_grading_rules.sql
-- Grading systems and non-overlapping grade ranges.

CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE IF NOT EXISTS grading_systems (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  academic_session_id UUID NOT NULL REFERENCES academic_sessions(id) ON DELETE CASCADE,
  semester_id UUID NOT NULL REFERENCES semesters(id) ON DELETE CASCADE,
  class_id UUID NOT NULL REFERENCES school_classes(id) ON DELETE CASCADE,
  system_name VARCHAR(120) NOT NULL,
  min_score NUMERIC(5,2) NOT NULL DEFAULT 0,
  max_score NUMERIC(5,2) NOT NULL DEFAULT 100,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  updated_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT chk_grading_systems_score_bounds CHECK (max_score >= min_score),
  CONSTRAINT uq_grading_systems_name_context UNIQUE (academic_session_id, semester_id, class_id, system_name)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_grading_systems_single_active
  ON grading_systems(academic_session_id, semester_id, class_id)
  WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_grading_systems_context
  ON grading_systems(academic_session_id, semester_id, class_id);

CREATE INDEX IF NOT EXISTS idx_grading_systems_created_by
  ON grading_systems(created_by_user_id);

CREATE TABLE IF NOT EXISTS grade_rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  grading_system_id UUID NOT NULL REFERENCES grading_systems(id) ON DELETE CASCADE,
  grade_label VARCHAR(20) NOT NULL,
  grade_point NUMERIC(4,2) NOT NULL CHECK (grade_point >= 0),
  min_score NUMERIC(5,2) NOT NULL,
  max_score NUMERIC(5,2) NOT NULL,
  is_passing BOOLEAN NOT NULL DEFAULT TRUE,
  created_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  updated_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  score_range NUMRANGE GENERATED ALWAYS AS (numrange(min_score, max_score, '[]')) STORED,
  CONSTRAINT chk_grade_rules_min_max CHECK (min_score <= max_score),
  CONSTRAINT uq_grade_rules_label_per_system UNIQUE (grading_system_id, grade_label)
);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'ex_grade_rules_no_overlap'
  ) THEN
    ALTER TABLE grade_rules
      ADD CONSTRAINT ex_grade_rules_no_overlap
      EXCLUDE USING GIST (
        grading_system_id WITH =,
        score_range WITH &&
      );
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_grade_rules_grading_system
  ON grade_rules(grading_system_id);

CREATE INDEX IF NOT EXISTS idx_grade_rules_created_by
  ON grade_rules(created_by_user_id);
