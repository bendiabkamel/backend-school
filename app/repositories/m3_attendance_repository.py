"""Repositories for M3 attendance split model."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from app.repositories.base_repository import SupabaseRepository


class M3AttendanceRepository(SupabaseRepository):
    def get_academic_session(self, academic_session_id: UUID | str) -> dict[str, Any] | None:
        result = (
            self.supabase.table("academic_sessions")
            .select("*")
            .eq("id", str(academic_session_id))
            .limit(1)
            .execute()
        )
        return self._first_or_none(result)

    def get_session_settings(self, academic_session_id: UUID | str) -> dict[str, Any] | None:
        result = (
            self.supabase.table("academic_settings")
            .select("*")
            .eq("settings_scope", "session")
            .eq("academic_session_id", str(academic_session_id))
            .limit(1)
            .execute()
        )
        return self._first_or_none(result)

    def get_global_settings(self) -> dict[str, Any] | None:
        result = (
            self.supabase.table("academic_settings")
            .select("*")
            .eq("settings_scope", "global")
            .limit(1)
            .execute()
        )
        return self._first_or_none(result)

    def list_teacher_assignments(
        self,
        teacher_id: UUID | str,
        academic_session_id: UUID | str,
        semester_id: UUID | str,
        class_id: UUID | str,
        section_id: UUID | str,
        course_id: UUID | str | None,
    ) -> list[dict[str, Any]]:
        query = (
            self.supabase.table("teacher_assignments")
            .select("*")
            .eq("teacher_id", str(teacher_id))
            .eq("academic_session_id", str(academic_session_id))
            .eq("semester_id", str(semester_id))
            .eq("class_id", str(class_id))
            .eq("section_id", str(section_id))
            .eq("is_active", True)
        )
        if course_id:
            query = query.eq("course_id", str(course_id))

        result = query.execute()
        return self._as_list(result)

    def find_attendance_session_by_context(
        self,
        academic_session_id: UUID | str,
        semester_id: UUID | str,
        class_id: UUID | str,
        section_id: UUID | str,
        course_id: UUID | str | None,
        attendance_date: date,
        slot_code: str,
    ) -> dict[str, Any] | None:
        query = (
            self.supabase.table("attendance_sessions")
            .select("*")
            .eq("academic_session_id", str(academic_session_id))
            .eq("semester_id", str(semester_id))
            .eq("class_id", str(class_id))
            .eq("section_id", str(section_id))
            .eq("attendance_date", str(attendance_date))
            .eq("slot_code", slot_code)
        )
        if course_id is None:
            query = query.is_("course_id", "null")
        else:
            query = query.eq("course_id", str(course_id))

        result = query.limit(1).execute()
        return self._first_or_none(result)

    def create_attendance_session(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.supabase.table("attendance_sessions").insert(payload).execute()
        row = self._first_or_none(result)
        if not row:
            raise ValueError("Failed to create attendance session")
        return row

    def get_attendance_session(self, attendance_session_id: UUID | str) -> dict[str, Any] | None:
        result = (
            self.supabase.table("attendance_sessions")
            .select("*")
            .eq("id", str(attendance_session_id))
            .limit(1)
            .execute()
        )
        return self._first_or_none(result)

    def list_attendance_records(self, attendance_session_id: UUID | str) -> list[dict[str, Any]]:
        result = (
            self.supabase.table("attendance_records")
            .select("*")
            .eq("attendance_session_id", str(attendance_session_id))
            .execute()
        )
        return self._as_list(result)

    def create_attendance_records(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result = self.supabase.table("attendance_records").insert(records).execute()
        return self._as_list(result)

    def upsert_attendance_records(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result = self.supabase.table("attendance_records").upsert(
            records,
            on_conflict="attendance_session_id,enrollment_id",
        ).execute()
        return self._as_list(result)

    def list_student_attendance(self, owner_user_id: UUID | str, from_date: date | None = None, to_date: date | None = None) -> list[dict[str, Any]]:
        query = self.supabase.table("attendance_records").select("*, attendance_sessions(*)").eq("owner_user_id", str(owner_user_id))
        if from_date:
            query = query.gte("attendance_sessions.attendance_date", str(from_date))
        if to_date:
            query = query.lte("attendance_sessions.attendance_date", str(to_date))
        result = query.execute()
        return self._as_list(result)

    def list_attendance_by_filters(
        self,
        academic_session_id: UUID | str,
        semester_id: UUID | str | None = None,
        class_id: UUID | str | None = None,
        section_id: UUID | str | None = None,
        course_id: UUID | str | None = None,
        attendance_date: date | None = None,
    ) -> list[dict[str, Any]]:
        query = self.supabase.table("attendance_sessions").select("*").eq("academic_session_id", str(academic_session_id))
        if semester_id:
            query = query.eq("semester_id", str(semester_id))
        if class_id:
            query = query.eq("class_id", str(class_id))
        if section_id:
            query = query.eq("section_id", str(section_id))
        if course_id:
            query = query.eq("course_id", str(course_id))
        if attendance_date:
            query = query.eq("attendance_date", str(attendance_date))

        sessions = self._as_list(query.order("attendance_date", desc=True).execute())
        if not sessions:
            return []

        session_ids = [row["id"] for row in sessions]
        records = (
            self.supabase.table("attendance_records")
            .select("*")
            .in_("attendance_session_id", session_ids)
            .execute()
        )
        return self._as_list(records)

    def list_enrollments_by_ids(self, enrollment_ids: list[str]) -> list[dict[str, Any]]:
        if not enrollment_ids:
            return []
        result = self.supabase.table("student_enrollments").select("*").in_("id", enrollment_ids).execute()
        return self._as_list(result)
