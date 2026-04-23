"""Repositories for M2 school structure, enrollments, and teacher assignments."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.repositories.base_repository import SupabaseRepository


class M2StructureRepository(SupabaseRepository):
    def get_class(self, class_id: UUID | str) -> dict[str, Any] | None:
        result = self.supabase.table("school_classes").select("*").eq("id", str(class_id)).limit(1).execute()
        return self._first_or_none(result)

    def list_classes(self, academic_session_id: UUID | str | None = None) -> list[dict[str, Any]]:
        query = self.supabase.table("school_classes").select("*")
        if academic_session_id:
            query = query.eq("academic_session_id", str(academic_session_id))
        result = query.order("display_order", desc=False).execute()
        return self._as_list(result)

    def create_class(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.supabase.table("school_classes").insert(payload).execute()
        row = self._first_or_none(result)
        if not row:
            raise ValueError("Failed to create class")
        return row

    def update_class(self, class_id: UUID | str, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.supabase.table("school_classes").update(payload).eq("id", str(class_id)).execute()
        row = self._first_or_none(result)
        if not row:
            raise ValueError("Class not found")
        return row

    def get_section(self, section_id: UUID | str) -> dict[str, Any] | None:
        result = self.supabase.table("sections").select("*").eq("id", str(section_id)).limit(1).execute()
        return self._first_or_none(result)

    def list_sections(
        self,
        academic_session_id: UUID | str | None = None,
        class_id: UUID | str | None = None,
    ) -> list[dict[str, Any]]:
        query = self.supabase.table("sections").select("*")
        if academic_session_id:
            query = query.eq("academic_session_id", str(academic_session_id))
        if class_id:
            query = query.eq("class_id", str(class_id))
        result = query.order("section_name", desc=False).execute()
        return self._as_list(result)

    def create_section(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.supabase.table("sections").insert(payload).execute()
        row = self._first_or_none(result)
        if not row:
            raise ValueError("Failed to create section")
        return row

    def update_section(self, section_id: UUID | str, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.supabase.table("sections").update(payload).eq("id", str(section_id)).execute()
        row = self._first_or_none(result)
        if not row:
            raise ValueError("Section not found")
        return row

    def get_course(self, course_id: UUID | str) -> dict[str, Any] | None:
        result = self.supabase.table("courses").select("*").eq("id", str(course_id)).limit(1).execute()
        return self._first_or_none(result)

    def list_courses(
        self,
        academic_session_id: UUID | str | None = None,
        semester_id: UUID | str | None = None,
        class_id: UUID | str | None = None,
    ) -> list[dict[str, Any]]:
        query = self.supabase.table("courses").select("*")
        if academic_session_id:
            query = query.eq("academic_session_id", str(academic_session_id))
        if semester_id:
            query = query.eq("semester_id", str(semester_id))
        if class_id:
            query = query.eq("class_id", str(class_id))
        result = query.order("course_name", desc=False).execute()
        return self._as_list(result)

    def create_course(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.supabase.table("courses").insert(payload).execute()
        row = self._first_or_none(result)
        if not row:
            raise ValueError("Failed to create course")
        return row

    def update_course(self, course_id: UUID | str, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.supabase.table("courses").update(payload).eq("id", str(course_id)).execute()
        row = self._first_or_none(result)
        if not row:
            raise ValueError("Course not found")
        return row

    def get_semester(self, semester_id: UUID | str) -> dict[str, Any] | None:
        result = self.supabase.table("semesters").select("*").eq("id", str(semester_id)).limit(1).execute()
        return self._first_or_none(result)

    def get_enrollment(self, enrollment_id: UUID | str) -> dict[str, Any] | None:
        result = self.supabase.table("student_enrollments").select("*").eq("id", str(enrollment_id)).limit(1).execute()
        return self._first_or_none(result)

    def list_enrollments(
        self,
        student_id: UUID | str | None = None,
        owner_user_id: UUID | str | None = None,
        academic_session_id: UUID | str | None = None,
        class_id: UUID | str | None = None,
        section_id: UUID | str | None = None,
        enrollment_status: str | None = None,
    ) -> list[dict[str, Any]]:
        query = self.supabase.table("student_enrollments").select("*")
        if student_id:
            query = query.eq("student_id", str(student_id))
        if owner_user_id:
            query = query.eq("owner_user_id", str(owner_user_id))
        if academic_session_id:
            query = query.eq("academic_session_id", str(academic_session_id))
        if class_id:
            query = query.eq("class_id", str(class_id))
        if section_id:
            query = query.eq("section_id", str(section_id))
        if enrollment_status:
            query = query.eq("enrollment_status", enrollment_status)

        result = query.order("enrolled_on", desc=True).execute()
        return self._as_list(result)

    def create_enrollment(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.supabase.table("student_enrollments").insert(payload).execute()
        row = self._first_or_none(result)
        if not row:
            raise ValueError("Failed to create enrollment")
        return row

    def update_enrollment(self, enrollment_id: UUID | str, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.supabase.table("student_enrollments").update(payload).eq("id", str(enrollment_id)).execute()
        row = self._first_or_none(result)
        if not row:
            raise ValueError("Enrollment not found")
        return row

    def list_teacher_assignments(
        self,
        teacher_id: UUID | str | None = None,
        academic_session_id: UUID | str | None = None,
        semester_id: UUID | str | None = None,
        class_id: UUID | str | None = None,
        section_id: UUID | str | None = None,
        course_id: UUID | str | None = None,
    ) -> list[dict[str, Any]]:
        query = self.supabase.table("teacher_assignments").select("*")
        if teacher_id:
            query = query.eq("teacher_id", str(teacher_id))
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

        result = query.order("assigned_from", desc=True).execute()
        return self._as_list(result)

    def upsert_teacher_assignments(self, payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result = self.supabase.table("teacher_assignments").upsert(
            payloads,
            on_conflict="teacher_id,academic_session_id,semester_id,class_id,section_id,course_id",
        ).execute()
        return self._as_list(result)

    def list_courses_by_ids(self, course_ids: list[str]) -> list[dict[str, Any]]:
        if not course_ids:
            return []
        result = self.supabase.table("courses").select("*").in_("id", course_ids).execute()
        return self._as_list(result)

    def list_students_by_user(self, user_id: UUID | str) -> list[dict[str, Any]]:
        result = self.supabase.table("students").select("*").eq("user_id", str(user_id)).execute()
        return self._as_list(result)
