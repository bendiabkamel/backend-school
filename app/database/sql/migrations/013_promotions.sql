-- 013_promotions.sql
-- Promotion workflow state + immutable audit trail.

CREATE TABLE IF NOT EXISTS promotions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  student_id UUID NOT NULL REFERENCES students(id) ON DELETE RESTRICT,
  owner_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  from_enrollment_id UUID REFERENCES student_enrollments(id) ON DELETE SET NULL,
  to_enrollment_id UUID REFERENCES student_enrollments(id) ON DELETE SET NULL,
  from_academic_session_id UUID NOT NULL REFERENCES academic_sessions(id) ON DELETE RESTRICT,
  to_academic_session_id UUID NOT NULL REFERENCES academic_sessions(id) ON DELETE RESTRICT,
  from_class_id UUID REFERENCES school_classes(id) ON DELETE SET NULL,
  from_section_id UUID REFERENCES sections(id) ON DELETE SET NULL,
  to_class_id UUID NOT NULL REFERENCES school_classes(id) ON DELETE RESTRICT,
  to_section_id UUID NOT NULL REFERENCES sections(id) ON DELETE RESTRICT,
  decision_status VARCHAR(20) NOT NULL DEFAULT 'pending'
    CHECK (decision_status IN ('pending', 'promoted', 'repeated', 'transferred', 'withdrawn', 'rejected')),
  decision_reason TEXT,
  id_card_number VARCHAR(80),
  promoted_by_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  promoted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_promotions_target UNIQUE (student_id, to_academic_session_id, to_class_id, to_section_id)
);

CREATE INDEX IF NOT EXISTS idx_promotions_student
  ON promotions(student_id);

CREATE INDEX IF NOT EXISTS idx_promotions_owner
  ON promotions(owner_user_id);

CREATE INDEX IF NOT EXISTS idx_promotions_source_context
  ON promotions(from_academic_session_id, from_class_id, from_section_id);

CREATE INDEX IF NOT EXISTS idx_promotions_target_context
  ON promotions(to_academic_session_id, to_class_id, to_section_id, decision_status);

CREATE INDEX IF NOT EXISTS idx_promotions_promoted_by
  ON promotions(promoted_by_user_id);

CREATE TABLE IF NOT EXISTS promotion_audit_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  promotion_id UUID NOT NULL REFERENCES promotions(id) ON DELETE CASCADE,
  event_type VARCHAR(30) NOT NULL
    CHECK (event_type IN ('created', 'updated', 'status_changed', 'approved', 'rejected', 'reverted', 'commented')),
  actor_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  event_payload JSONB NOT NULL DEFAULT '{}'::JSONB,
  event_note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_promotion_audit_events_promotion
  ON promotion_audit_events(promotion_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_promotion_audit_events_actor
  ON promotion_audit_events(actor_user_id);

CREATE INDEX IF NOT EXISTS idx_promotion_audit_events_payload_gin
  ON promotion_audit_events USING GIN(event_payload);
