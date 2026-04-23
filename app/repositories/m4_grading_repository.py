"""Repositories for M4 exams, grading, marks, and final marks."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.repositories.base_repository import SupabaseRepository


class M4GradingRepository(SupabaseRepository):
    def get_academic_session(self, academic_session_id: UUID | str) -> dict[str, Any] | None:
        result = self.supabase.table("academic_sessions").select("*").eq("id", str(academic_session_id)).limit(1).execute()
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
        result = self.supabase.table("academic_settings").select("*").eq("settings_scope", "global").limit(1).execute()
        return self._first_or_none(result)

    def create_exam(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.supabase.table("school_exams").insert(payload).execute()
        row = self._first_or_none(result)
        if not row:
            raise ValueError("Failed to create exam")
        return row

    def list_exams(
        self,
        academic_session_id: UUID | str | None = None,
        semester_id: UUID | str | None = None,
        class_id: UUID | str | None = None,
        section_id: UUID | str | None = None,
        course_id: UUID | str | None = None,
    ) -> list[dict[str, Any]]:
        query = self.supabase.table("school_exams").select("*")
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

        result = query.order("starts_at", desc=False).execute()
        return self._as_list(result)

    def get_exam(self, exam_id: UUID | str) -> dict[str, Any] | None:
        result = self.supabase.table("school_exams").select("*").eq("id", str(exam_id)).limit(1).execute()
        return self._first_or_none(result)

    def update_exam(self, exam_id: UUID | str, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.supabase.table("school_exams").update(payload).eq("id", str(exam_id)).execute()
        row = self._first_or_none(result)
        if not row:
            raise ValueError("Exam not found")
        return row

    def upsert_exam_rule(self, payload: dict[str, Any]) -> dict[str, Any]:
        exam_id = payload["school_exam_id"]
        existing = self.get_exam_rule_by_exam(exam_id)
        if existing:
            result = self.supabase.table("exam_rules").update(payload).eq("id", existing["id"]).execute()
        else:
            result = self.supabase.table("exam_rules").insert(payload).execute()

        row = self._first_or_none(result)
        if not row:
            raise ValueError("Failed to upsert exam rule")
        return row

    def get_exam_rule_by_exam(self, exam_id: UUID | str) -> dict[str, Any] | None:
        result = self.supabase.table("exam_rules").select("*").eq("school_exam_id", str(exam_id)).limit(1).execute()
        return self._first_or_none(result)

    def create_grading_system(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.supabase.table("grading_systems").insert(payload).execute()
        row = self._first_or_none(result)
        if not row:
            raise ValueError("Failed to create grading system")
        return row

    def list_grading_systems(
        self,
        academic_session_id: UUID | str | None = None,
        semester_id: UUID | str | None = None,
        class_id: UUID | str | None = None,
    ) -> list[dict[str, Any]]:
        query = self.supabase.table("grading_systems").select("*")
        if academic_session_id:
            query = query.eq("academic_session_id", str(academic_session_id))
        if semester_id:
            query = query.eq("semester_id", str(semester_id))
        if class_id:
            query = query.eq("class_id", str(class_id))

        result = query.order("created_at", desc=True).execute()
        return self._as_list(result)

    def get_grading_system(self, grading_system_id: UUID | str) -> dict[str, Any] | None:
        result = self.supabase.table("grading_systems").select("*").eq("id", str(grading_system_id)).limit(1).execute()
        return self._first_or_none(result)

    def create_grade_rules(self, payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result = self.supabase.table("grade_rules").insert(payloads).execute()
        return self._as_list(result)

    def list_grade_rules(self, grading_system_id: UUID | str) -> list[dict[str, Any]]:
        result = (
            self.supabase.table("grade_rules")
            .select("*")
            .eq("grading_system_id", str(grading_system_id))
            .order("min_score", desc=False)
            .execute()
        )
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

    def upsert_marks(self, payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result = self.supabase.table("marks").upsert(payloads, on_conflict="school_exam_id,enrollment_id").execute()
        return self._as_list(result)

    def list_marks_by_exam(self, school_exam_id: UUID | str) -> list[dict[str, Any]]:
        result = self.supabase.table("marks").select("*").eq("school_exam_id", str(school_exam_id)).execute()
        return self._as_list(result)

    def list_marks_by_context(
        self,
        academic_session_id: UUID | str,
        semester_id: UUID | str,
        class_id: UUID | str,
        section_id: UUID | str,
        course_id: UUID | str,
    ) -> list[dict[str, Any]]:
        exams = (
            self.supabase.table("school_exams")
            .select("id")
            .eq("academic_session_id", str(academic_session_id))
            .eq("semester_id", str(semester_id))
            .eq("class_id", str(class_id))
            .eq("section_id", str(section_id))
            .eq("course_id", str(course_id))
            .execute()
        )
        exam_ids = [row["id"] for row in self._as_list(exams)]
        if not exam_ids:
            return []

        result = self.supabase.table("marks").select("*").in_("school_exam_id", exam_ids).execute()
        return self._as_list(result)

    def list_exams_by_context(
        self,
        academic_session_id: UUID | str,
        semester_id: UUID | str,
        class_id: UUID | str,
        section_id: UUID | str,
        course_id: UUID | str,
    ) -> list[dict[str, Any]]:
        result = (
            self.supabase.table("school_exams")
            .select("*")
            .eq("academic_session_id", str(academic_session_id))
            .eq("semester_id", str(semester_id))
            .eq("class_id", str(class_id))
            .eq("section_id", str(section_id))
            .eq("course_id", str(course_id))
            .execute()
        )
        return self._as_list(result)

    def get_enrollment(self, enrollment_id: UUID | str) -> dict[str, Any] | None:
        result = self.supabase.table("student_enrollments").select("*").eq("id", str(enrollment_id)).limit(1).execute()
        return self._first_or_none(result)

    def list_enrollments(
        self,
        academic_session_id: UUID | str,
        semester_id: UUID | str,
        class_id: UUID | str,
        section_id: UUID | str,
        status: str | None = "active",
    ) -> list[dict[str, Any]]:
        query = (
            self.supabase.table("student_enrollments")
            .select("*")
            .eq("academic_session_id", str(academic_session_id))
            .eq("semester_id", str(semester_id))
            .eq("class_id", str(class_id))
            .eq("section_id", str(section_id))
        )
        if status is not None:
            query = query.eq("enrollment_status", status)
        result = query.execute()
        return self._as_list(result)

    def upsert_final_marks(self, payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result = self.supabase.table("final_marks").upsert(
            payloads,
            on_conflict="enrollment_id,semester_id,course_id",
        ).execute()
        return self._as_list(result)

    def get_final_mark(self, final_mark_id: UUID | str) -> dict[str, Any] | None:
        result = self.supabase.table("final_marks").select("*").eq("id", str(final_mark_id)).limit(1).execute()
        return self._first_or_none(result)

    def update_final_mark(self, final_mark_id: UUID | str, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.supabase.table("final_marks").update(payload).eq("id", str(final_mark_id)).execute()
        row = self._first_or_none(result)
        if not row:
            raise ValueError("Final mark not found")
        return row

    def list_final_marks(
        self,
        academic_session_id: UUID | str,
        semester_id: UUID | str,
        course_id: UUID | str,
    ) -> list[dict[str, Any]]:
        result = (
            self.supabase.table("final_marks")
            .select("*")
            .eq("academic_session_id", str(academic_session_id))
            .eq("semester_id", str(semester_id))
            .eq("course_id", str(course_id))
            .execute()
        )
        return self._as_list(result)
