"""Business service for M2 school structure and enrollments."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.repositories.m1_sessions_repository import M1SessionsRepository
from app.repositories.m2_structure_repository import M2StructureRepository
from app.services.exceptions import NotFoundError, PermissionDeniedError, ValidationError
from app.services.session_isolation_service import SessionIsolationService


class M2StructureService:
    def __init__(self, repository: M2StructureRepository, sessions_repository: M1SessionsRepository):
        self.repository = repository
        self.sessions_repository = sessions_repository

    # Classes
    def list_classes(self, academic_session_id: UUID | str | None = None) -> list[dict[str, Any]]:
        return self.repository.list_classes(academic_session_id=academic_session_id)

    def create_class(self, payload: dict[str, Any], actor_user_id: str) -> dict[str, Any]:
        session = self.sessions_repository.get_session(payload["academic_session_id"])
        if not session:
            raise NotFoundError("Academic session not found")
        SessionIsolationService.ensure_session_not_locked(session)

        payload = payload.copy()
        payload["created_by_user_id"] = actor_user_id
        payload["updated_by_user_id"] = actor_user_id
        return self.repository.create_class(payload)

    def update_class(self, class_id: UUID | str, payload: dict[str, Any], actor_user_id: str) -> dict[str, Any]:
        current = self.repository.get_class(class_id)
        if not current:
            raise NotFoundError("Class not found")

        session = self.sessions_repository.get_session(current["academic_session_id"])
        if not session:
            raise NotFoundError("Academic session not found")
        SessionIsolationService.ensure_session_not_locked(session)

        payload = payload.copy()
        payload["updated_by_user_id"] = actor_user_id
        return self.repository.update_class(class_id, payload)

    # Sections
    def list_sections(
        self,
        academic_session_id: UUID | str | None = None,
        class_id: UUID | str | None = None,
    ) -> list[dict[str, Any]]:
        return self.repository.list_sections(academic_session_id=academic_session_id, class_id=class_id)

    def create_section(self, payload: dict[str, Any], actor_user_id: str) -> dict[str, Any]:
        class_row = self.repository.get_class(payload["class_id"])
        if not class_row:
            raise NotFoundError("Class not found")

        session = self.sessions_repository.get_session(payload["academic_session_id"])
        if not session:
            raise NotFoundError("Academic session not found")
        SessionIsolationService.ensure_session_not_locked(session)
        SessionIsolationService.ensure_same_session(payload["academic_session_id"], class_row=class_row)

        payload = payload.copy()
        payload["created_by_user_id"] = actor_user_id
        payload["updated_by_user_id"] = actor_user_id
        return self.repository.create_section(payload)

    def update_section(self, section_id: UUID | str, payload: dict[str, Any], actor_user_id: str) -> dict[str, Any]:
        section = self.repository.get_section(section_id)
        if not section:
            raise NotFoundError("Section not found")

        session = self.sessions_repository.get_session(section["academic_session_id"])
        if not session:
            raise NotFoundError("Academic session not found")
        SessionIsolationService.ensure_session_not_locked(session)

        payload = payload.copy()
        payload["updated_by_user_id"] = actor_user_id
        return self.repository.update_section(section_id, payload)

    # Courses
    def list_courses(
        self,
        academic_session_id: UUID | str | None = None,
        semester_id: UUID | str | None = None,
        class_id: UUID | str | None = None,
    ) -> list[dict[str, Any]]:
        return self.repository.list_courses(
            academic_session_id=academic_session_id,
            semester_id=semester_id,
            class_id=class_id,
        )

    def create_course(self, payload: dict[str, Any], actor_user_id: str) -> dict[str, Any]:
        class_row = self.repository.get_class(payload["class_id"])
        if not class_row:
            raise NotFoundError("Class not found")
        semester_row = self.repository.get_semester(payload["semester_id"])
        if not semester_row:
            raise NotFoundError("Semester not found")

        session = self.sessions_repository.get_session(payload["academic_session_id"])
        if not session:
            raise NotFoundError("Academic session not found")
        SessionIsolationService.ensure_session_not_locked(session)
        SessionIsolationService.ensure_same_session(
            payload["academic_session_id"],
            semester_row=semester_row,
            class_row=class_row,
        )

        payload = payload.copy()
        payload["created_by_user_id"] = actor_user_id
        payload["updated_by_user_id"] = actor_user_id
        return self.repository.create_course(payload)

    def update_course(self, course_id: UUID | str, payload: dict[str, Any], actor_user_id: str) -> dict[str, Any]:
        course_row = self.repository.get_course(course_id)
        if not course_row:
            raise NotFoundError("Course not found")

        session = self.sessions_repository.get_session(course_row["academic_session_id"])
        if not session:
            raise NotFoundError("Academic session not found")
        SessionIsolationService.ensure_session_not_locked(session)

        payload = payload.copy()
        payload["updated_by_user_id"] = actor_user_id
        return self.repository.update_course(course_id, payload)

    # Enrollments
    def list_enrollments(self, current_user: dict, filters: dict[str, Any]) -> list[dict[str, Any]]:
        role = current_user.get("role")
        if role == "student":
            students = self.repository.list_students_by_user(current_user["id"])
            if not students:
                return []
            student_id = students[0]["id"]
            filters = filters.copy()
            filters["student_id"] = student_id
            filters["owner_user_id"] = current_user["id"]

        return self.repository.list_enrollments(**filters)

    def create_enrollment(self, payload: dict[str, Any], actor_user_id: str) -> dict[str, Any]:
        session = self.sessions_repository.get_session(payload["academic_session_id"])
        if not session:
            raise NotFoundError("Academic session not found")
        SessionIsolationService.ensure_session_not_locked(session)

        semester_row = self.repository.get_semester(payload["semester_id"])
        class_row = self.repository.get_class(payload["class_id"])
        section_row = self.repository.get_section(payload["section_id"])

        if not semester_row:
            raise NotFoundError("Semester not found")
        if not class_row:
            raise NotFoundError("Class not found")
        if not section_row:
            raise NotFoundError("Section not found")

        SessionIsolationService.ensure_same_session(
            payload["academic_session_id"],
            semester_row=semester_row,
            class_row=class_row,
            section_row=section_row,
        )
        SessionIsolationService.ensure_section_belongs_to_class(section_row=section_row, class_id=payload["class_id"])

        payload = payload.copy()
        payload["created_by_user_id"] = actor_user_id
        payload["updated_by_user_id"] = actor_user_id
        return self.repository.create_enrollment(payload)

    def update_enrollment_status(self, enrollment_id: UUID | str, payload: dict[str, Any], actor_user_id: str) -> dict[str, Any]:
        enrollment = self.repository.get_enrollment(enrollment_id)
        if not enrollment:
            raise NotFoundError("Enrollment not found")

        session = self.sessions_repository.get_session(enrollment["academic_session_id"])
        if not session:
            raise NotFoundError("Academic session not found")
        SessionIsolationService.ensure_session_not_locked(session)

        current_status = enrollment["enrollment_status"]
        new_status = payload["enrollment_status"]
        self._validate_enrollment_transition(current_status, new_status)

        if payload.get("exited_on") and str(payload["exited_on"]) < str(enrollment["enrolled_on"]):
            raise ValidationError("exited_on must be greater than or equal to enrolled_on")

        payload = payload.copy()
        payload["updated_by_user_id"] = actor_user_id
        return self.repository.update_enrollment(enrollment_id, payload)

    # Teacher assignments
    def bulk_assign_teachers(self, payloads: list[dict[str, Any]], actor_user_id: str) -> list[dict[str, Any]]:
        seen_keys: set[tuple[str, str, str, str, str, str]] = set()
        normalized_payloads: list[dict[str, Any]] = []

        for payload in payloads:
            session = self.sessions_repository.get_session(payload["academic_session_id"])
            if not session:
                raise NotFoundError("Academic session not found")
            SessionIsolationService.ensure_session_not_locked(session)

            semester_row = self.repository.get_semester(payload["semester_id"])
            class_row = self.repository.get_class(payload["class_id"])
            section_row = self.repository.get_section(payload["section_id"])
            course_row = self.repository.get_course(payload["course_id"])

            if not semester_row:
                raise NotFoundError("Semester not found")
            if not class_row:
                raise NotFoundError("Class not found")
            if not section_row:
                raise NotFoundError("Section not found")
            if not course_row:
                raise NotFoundError("Course not found")

            SessionIsolationService.ensure_same_session(
                payload["academic_session_id"],
                semester_row=semester_row,
                class_row=class_row,
                section_row=section_row,
                course_row=course_row,
            )
            SessionIsolationService.ensure_section_belongs_to_class(section_row=section_row, class_id=payload["class_id"])
            SessionIsolationService.ensure_course_belongs_to_class(course_row=course_row, class_id=payload["class_id"])
            SessionIsolationService.ensure_course_belongs_to_semester(course_row=course_row, semester_id=payload["semester_id"])

            key = (
                str(payload["teacher_id"]),
                str(payload["academic_session_id"]),
                str(payload["semester_id"]),
                str(payload["class_id"]),
                str(payload["section_id"]),
                str(payload["course_id"]),
            )
            if key in seen_keys:
                raise ValidationError("Duplicate teacher assignment detected in bulk payload")
            seen_keys.add(key)

            row = payload.copy()
            row["assigned_by_user_id"] = actor_user_id
            normalized_payloads.append(row)

        return self.repository.upsert_teacher_assignments(normalized_payloads)

    def list_teacher_courses(self, teacher_id: UUID | str, academic_session_id: UUID | str | None = None) -> list[dict[str, Any]]:
        assignments = self.repository.list_teacher_assignments(
            teacher_id=teacher_id,
            academic_session_id=academic_session_id,
        )
        course_ids = [str(row["course_id"]) for row in assignments]
        courses = self.repository.list_courses_by_ids(course_ids)
        courses_by_id = {str(row["id"]): row for row in courses}

        output: list[dict[str, Any]] = []
        for assignment in assignments:
            row = assignment.copy()
            row["course"] = courses_by_id.get(str(assignment["course_id"]))
            output.append(row)
        return output

    @staticmethod
    def _validate_enrollment_transition(current_status: str, new_status: str) -> None:
        allowed = {
            "active": {"active", "promoted", "repeated", "transferred", "withdrawn", "graduated", "inactive"},
            "promoted": {"promoted", "graduated", "inactive"},
            "repeated": {"repeated", "active", "withdrawn", "inactive"},
            "transferred": {"transferred", "inactive"},
            "withdrawn": {"withdrawn", "inactive"},
            "graduated": {"graduated"},
            "inactive": {"inactive", "active"},
        }
        current_allowed = allowed.get(current_status, {current_status})
        if new_status not in current_allowed:
            raise ValidationError(f"Invalid enrollment lifecycle transition from {current_status} to {new_status}")

    @staticmethod
    def ensure_student_access(current_user: dict, owner_user_id: str) -> None:
        if current_user.get("role") == "student" and str(current_user.get("id")) != str(owner_user_id):
            raise PermissionDeniedError("Students can only access their own enrollment data")
