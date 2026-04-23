"""Repositories for M5 assignments and syllabi."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.repositories.base_repository import SupabaseRepository


class M5AssignmentsRepository(SupabaseRepository):
    def get_academic_session(self, academic_session_id: UUID | str) -> dict[str, Any] | None:
        result = self.supabase.table("academic_sessions").select("*").eq("id", str(academic_session_id)).limit(1).execute()
        return self._first_or_none(result)

    def get_assignment(self, assignment_id: UUID | str) -> dict[str, Any] | None:
        result = self.supabase.table("assignments").select("*").eq("id", str(assignment_id)).limit(1).execute()
        return self._first_or_none(result)

    def list_assignments(
        self,
        academic_session_id: UUID | str | None = None,
        semester_id: UUID | str | None = None,
        class_id: UUID | str | None = None,
        section_id: UUID | str | None = None,
        course_id: UUID | str | None = None,
        is_published: bool | None = None,
    ) -> list[dict[str, Any]]:
        query = self.supabase.table("assignments").select("*")
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
        if is_published is not None:
            query = query.eq("is_published", is_published)
        result = query.order("assigned_at", desc=True).execute()
        return self._as_list(result)

    def create_assignment(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.supabase.table("assignments").insert(payload).execute()
        row = self._first_or_none(result)
        if not row:
            raise ValueError("Failed to create assignment")
        return row

    def update_assignment(self, assignment_id: UUID | str, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.supabase.table("assignments").update(payload).eq("id", str(assignment_id)).execute()
        row = self._first_or_none(result)
        if not row:
            raise ValueError("Assignment not found")
        return row

    def get_enrollment(self, enrollment_id: UUID | str) -> dict[str, Any] | None:
        result = self.supabase.table("student_enrollments").select("*").eq("id", str(enrollment_id)).limit(1).execute()
        return self._first_or_none(result)

    def create_submission(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.supabase.table("assignment_submissions").insert(payload).execute()
        row = self._first_or_none(result)
        if not row:
            raise ValueError("Failed to create submission")
        return row

    def list_submissions(
        self,
        assignment_id: UUID | str | None = None,
        enrollment_id: UUID | str | None = None,
        owner_user_id: UUID | str | None = None,
        submission_status: str | None = None,
    ) -> list[dict[str, Any]]:
        query = self.supabase.table("assignment_submissions").select("*")
        if assignment_id:
            query = query.eq("assignment_id", str(assignment_id))
        if enrollment_id:
            query = query.eq("enrollment_id", str(enrollment_id))
        if owner_user_id:
            query = query.eq("owner_user_id", str(owner_user_id))
        if submission_status:
            query = query.eq("submission_status", submission_status)

        result = query.order("submitted_at", desc=True).execute()
        return self._as_list(result)

    def get_submission(self, submission_id: UUID | str) -> dict[str, Any] | None:
        result = self.supabase.table("assignment_submissions").select("*").eq("id", str(submission_id)).limit(1).execute()
        return self._first_or_none(result)

    def update_submission(self, submission_id: UUID | str, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.supabase.table("assignment_submissions").update(payload).eq("id", str(submission_id)).execute()
        row = self._first_or_none(result)
        if not row:
            raise ValueError("Submission not found")
        return row

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

    def create_syllabus(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.supabase.table("syllabi").insert(payload).execute()
        row = self._first_or_none(result)
        if not row:
            raise ValueError("Failed to create syllabus")
        return row

    def list_syllabi(
        self,
        academic_session_id: UUID | str | None = None,
        semester_id: UUID | str | None = None,
        class_id: UUID | str | None = None,
        course_id: UUID | str | None = None,
        is_published: bool | None = None,
    ) -> list[dict[str, Any]]:
        query = self.supabase.table("syllabi").select("*")
        if academic_session_id:
            query = query.eq("academic_session_id", str(academic_session_id))
        if semester_id:
            query = query.eq("semester_id", str(semester_id))
        if class_id:
            query = query.eq("class_id", str(class_id))
        if course_id:
            query = query.eq("course_id", str(course_id))
        if is_published is not None:
            query = query.eq("is_published", is_published)

        result = query.order("created_at", desc=True).execute()
        return self._as_list(result)

    def get_syllabus(self, syllabus_id: UUID | str) -> dict[str, Any] | None:
        result = self.supabase.table("syllabi").select("*").eq("id", str(syllabus_id)).limit(1).execute()
        return self._first_or_none(result)

    def update_syllabus(self, syllabus_id: UUID | str, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.supabase.table("syllabi").update(payload).eq("id", str(syllabus_id)).execute()
        row = self._first_or_none(result)
        if not row:
            raise ValueError("Syllabus not found")
        return row
