"""Repositories for M6 notices, events, and routines."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.repositories.base_repository import SupabaseRepository


class M6CommunicationsRepository(SupabaseRepository):
    def get_academic_session(self, academic_session_id: UUID | str) -> dict[str, Any] | None:
        result = self.supabase.table("academic_sessions").select("*").eq("id", str(academic_session_id)).limit(1).execute()
        return self._first_or_none(result)

    def list_active_enrollments_for_owner(self, owner_user_id: UUID | str) -> list[dict[str, Any]]:
        result = (
            self.supabase.table("student_enrollments")
            .select("*")
            .eq("owner_user_id", str(owner_user_id))
            .eq("enrollment_status", "active")
            .execute()
        )
        return self._as_list(result)

    def create_notice(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.supabase.table("notices").insert(payload).execute()
        row = self._first_or_none(result)
        if not row:
            raise ValueError("Failed to create notice")
        return row

    def list_notices(self, academic_session_id: UUID | str | None = None) -> list[dict[str, Any]]:
        query = self.supabase.table("notices").select("*")
        if academic_session_id:
            query = query.eq("academic_session_id", str(academic_session_id))
        result = query.order("published_at", desc=True).execute()
        return self._as_list(result)

    def create_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.supabase.table("events").insert(payload).execute()
        row = self._first_or_none(result)
        if not row:
            raise ValueError("Failed to create event")
        return row

    def list_events(self, academic_session_id: UUID | str | None = None) -> list[dict[str, Any]]:
        query = self.supabase.table("events").select("*")
        if academic_session_id:
            query = query.eq("academic_session_id", str(academic_session_id))
        result = query.order("starts_at", desc=False).execute()
        return self._as_list(result)

    def create_routines(self, payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result = self.supabase.table("routines").insert(payloads).execute()
        return self._as_list(result)

    def list_routines(
        self,
        academic_session_id: UUID | str | None = None,
        semester_id: UUID | str | None = None,
        class_id: UUID | str | None = None,
        section_id: UUID | str | None = None,
        course_id: UUID | str | None = None,
        weekday: int | None = None,
    ) -> list[dict[str, Any]]:
        query = self.supabase.table("routines").select("*")
        if academic_session_id:
            query = query.eq("academic_session_id", str(academic_session_id))
        if semester_id:
            query = query.eq("semester_id", str(semester_id))
        if class_id:
            query = query.eq("class_id", str(class_id))
        if section_id:
            query = query.eq("section_id", str(section_id))
        if course_id:
            query = query.eq("course_id", str(course_id))
        if weekday:
            query = query.eq("weekday", weekday)

        result = query.order("weekday", desc=False).order("start_time", desc=False).execute()
        return self._as_list(result)

    def list_teacher_assignments(
        self,
        teacher_id: UUID | str,
        academic_session_id: UUID | str,
        semester_id: UUID | str,
        class_id: UUID | str,
        section_id: UUID | str,
        course_id: UUID | str,
    ) -> list[dict[str, Any]]:
        result = (
            self.supabase.table("teacher_assignments")
            .select("*")
            .eq("teacher_id", str(teacher_id))
            .eq("academic_session_id", str(academic_session_id))
            .eq("semester_id", str(semester_id))
            .eq("class_id", str(class_id))
            .eq("section_id", str(section_id))
            .eq("course_id", str(course_id))
            .eq("is_active", True)
            .execute()
        )
        return self._as_list(result)
