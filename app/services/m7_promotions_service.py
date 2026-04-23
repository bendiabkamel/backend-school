"""Business service for M7 promotions and audit trail."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.repositories.m7_promotions_repository import M7PromotionsRepository
from app.services.exceptions import NotFoundError, PermissionDeniedError, ValidationError
from app.services.session_isolation_service import SessionIsolationService


class M7PromotionsService:
    def __init__(self, repository: M7PromotionsRepository):
        self.repository = repository

    def list_promotions(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        return self.repository.list_promotions(**filters)

    def create_promotions(self, payload: dict[str, Any], current_user: dict) -> list[dict[str, Any]]:
        self._ensure_admin(current_user)
        session = self.repository.get_academic_session(payload["to_academic_session_id"])
        if not session:
            raise NotFoundError("Target academic session not found")
        SessionIsolationService.ensure_session_not_locked(session)

        enrollment_ids = payload["enrollment_ids"]
        enrollments = self.repository.list_enrollments_by_ids([str(value) for value in enrollment_ids])
        if len(enrollments) != len(enrollment_ids):
            raise ValidationError("Some enrollment_ids were not found")

        source_session = str(payload["from_academic_session_id"])
        target_session = str(payload["to_academic_session_id"])
        if source_session == target_session:
            raise ValidationError("from_academic_session_id and to_academic_session_id must differ")

        rows = []
        for enrollment in enrollments:
            rows.append(
                {
                    "student_id": enrollment["student_id"],
                    "owner_user_id": enrollment["owner_user_id"],
                    "from_enrollment_id": enrollment["id"],
                    "to_enrollment_id": None,
                    "from_academic_session_id": payload["from_academic_session_id"],
                    "to_academic_session_id": payload["to_academic_session_id"],
                    "from_class_id": enrollment["class_id"],
                    "from_section_id": enrollment["section_id"],
                    "to_class_id": payload["to_class_id"],
                    "to_section_id": payload["to_section_id"],
                    "decision_status": payload.get("decision_status", "pending"),
                    "decision_reason": payload.get("decision_reason"),
                    "id_card_number": payload.get("id_card_number"),
                    "promoted_by_user_id": current_user["id"],
                    "promoted_at": datetime.now(timezone.utc).isoformat(),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )

        created = self.repository.create_promotions(rows)
        for promotion in created:
            self.repository.create_audit_event(
                {
                    "promotion_id": promotion["id"],
                    "event_type": "created",
                    "actor_user_id": current_user["id"],
                    "event_payload": {"source": "bulk_promotion", "promotion_id": promotion["id"]},
                    "event_note": "Promotion created",
                }
            )
        return created

    def update_status(self, promotion_id: UUID | str, payload: dict[str, Any], current_user: dict) -> dict[str, Any]:
        self._ensure_admin(current_user)
        promotion = self.repository.get_promotion(promotion_id)
        if not promotion:
            raise NotFoundError("Promotion not found")

        session = self.repository.get_academic_session(promotion["to_academic_session_id"])
        if not session:
            raise NotFoundError("Target academic session not found")
        SessionIsolationService.ensure_session_not_locked(session)

        updated = self.repository.update_promotion(
            promotion_id,
            {
                "decision_status": payload["decision_status"],
                "decision_reason": payload.get("decision_reason"),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        self.repository.create_audit_event(
            {
                "promotion_id": promotion_id,
                "event_type": "status_changed",
                "actor_user_id": current_user["id"],
                "event_payload": {"decision_status": payload["decision_status"]},
                "event_note": payload.get("decision_reason"),
            }
        )
        return updated

    def get_audit_events(self, promotion_id: UUID | str, current_user: dict) -> list[dict[str, Any]]:
        promotion = self.repository.get_promotion(promotion_id)
        if not promotion:
            raise NotFoundError("Promotion not found")
        if current_user.get("role") == "student" and str(current_user.get("id")) != str(promotion.get("owner_user_id")):
            raise PermissionDeniedError("Students can only access their own promotion audit history")
        return self.repository.list_audit_events(promotion_id)

    def stats(self, filters: dict[str, Any], current_user: dict) -> dict[str, Any]:
        self._ensure_admin(current_user)
        promotions = self.repository.list_promotions(**filters)
        counts: dict[str, int] = {}
        for row in promotions:
            status = row.get("decision_status", "pending")
            counts[status] = counts.get(status, 0) + 1
        return {"counts": counts, "total": len(promotions)}

    @staticmethod
    def _ensure_admin(current_user: dict) -> None:
        if current_user.get("role") != "admin":
            raise PermissionDeniedError("Operation requires admin role")
