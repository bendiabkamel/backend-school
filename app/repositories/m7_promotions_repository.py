"""Repositories for M7 promotions, validation checks, and audit trail."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.repositories.base_repository import SupabaseRepository


class M7PromotionsRepository(SupabaseRepository):
    def get_academic_session(self, academic_session_id: UUID | str) -> dict[str, Any] | None:
        result = self.supabase.table("academic_sessions").select("*").eq("id", str(academic_session_id)).limit(1).execute()
        return self._first_or_none(result)

    def list_enrollments_by_ids(self, enrollment_ids: list[str]) -> list[dict[str, Any]]:
        if not enrollment_ids:
            return []
        result = self.supabase.table("student_enrollments").select("*").in_("id", enrollment_ids).execute()
        return self._as_list(result)

    def create_enrollment(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.supabase.table("student_enrollments").insert(payload).execute()
        row = self._first_or_none(result)
        if not row:
            raise ValueError("Failed to create target enrollment")
        return row

    def list_courses_for_context(
        self,
        academic_session_id: UUID | str,
        semester_id: UUID | str,
        class_id: UUID | str,
    ) -> list[dict[str, Any]]:
        result = (
            self.supabase.table("courses")
            .select("*")
            .eq("academic_session_id", str(academic_session_id))
            .eq("semester_id", str(semester_id))
            .eq("class_id", str(class_id))
            .eq("is_active", True)
            .execute()
        )
        return self._as_list(result)

    def list_final_marks_for_enrollment(self, enrollment_id: UUID | str, semester_id: UUID | str) -> list[dict[str, Any]]:
        result = (
            self.supabase.table("final_marks")
            .select("*")
            .eq("enrollment_id", str(enrollment_id))
            .eq("semester_id", str(semester_id))
            .execute()
        )
        return self._as_list(result)

    def list_attendance_sessions_for_context(
        self,
        academic_session_id: UUID | str,
        semester_id: UUID | str,
        class_id: UUID | str,
        section_id: UUID | str,
    ) -> list[dict[str, Any]]:
        result = (
            self.supabase.table("attendance_sessions")
            .select("id")
            .eq("academic_session_id", str(academic_session_id))
            .eq("semester_id", str(semester_id))
            .eq("class_id", str(class_id))
            .eq("section_id", str(section_id))
            .execute()
        )
        return self._as_list(result)

    def list_attendance_records_for_enrollment(
        self,
        enrollment_id: UUID | str,
        attendance_session_ids: list[str],
    ) -> list[dict[str, Any]]:
        if not attendance_session_ids:
            return []
        result = (
            self.supabase.table("attendance_records")
            .select("*")
            .eq("enrollment_id", str(enrollment_id))
            .in_("attendance_session_id", attendance_session_ids)
            .execute()
        )
        return self._as_list(result)

    def create_promotions(self, payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result = self.supabase.table("promotions").upsert(
            payloads,
            on_conflict="student_id,to_academic_session_id,to_class_id,to_section_id",
        ).execute()
        return self._as_list(result)

    def list_promotions(
        self,
        from_academic_session_id: UUID | str | None = None,
        to_academic_session_id: UUID | str | None = None,
        decision_status: str | None = None,
    ) -> list[dict[str, Any]]:
        query = self.supabase.table("promotions").select("*")
        if from_academic_session_id:
            query = query.eq("from_academic_session_id", str(from_academic_session_id))
        if to_academic_session_id:
            query = query.eq("to_academic_session_id", str(to_academic_session_id))
        if decision_status:
            query = query.eq("decision_status", decision_status)

        result = query.order("promoted_at", desc=True).execute()
        return self._as_list(result)

    def get_promotion(self, promotion_id: UUID | str) -> dict[str, Any] | None:
        result = self.supabase.table("promotions").select("*").eq("id", str(promotion_id)).limit(1).execute()
        return self._first_or_none(result)

    def update_promotion(self, promotion_id: UUID | str, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.supabase.table("promotions").update(payload).eq("id", str(promotion_id)).execute()
        row = self._first_or_none(result)
        if not row:
            raise ValueError("Promotion not found")
        return row

    def create_audit_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.supabase.table("promotion_audit_events").insert(payload).execute()
        row = self._first_or_none(result)
        if not row:
            raise ValueError("Failed to create promotion audit event")
        return row

    def list_audit_events(self, promotion_id: UUID | str) -> list[dict[str, Any]]:
        result = (
            self.supabase.table("promotion_audit_events")
            .select("*")
            .eq("promotion_id", str(promotion_id))
            .order("created_at", desc=True)
            .execute()
        )
        return self._as_list(result)
