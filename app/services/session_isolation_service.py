"""Cross-module session isolation and lock checks."""

from __future__ import annotations

from app.services.exceptions import ValidationError


class SessionIsolationService:
    LOCKED_STATUSES = {"closed", "archived"}

    @classmethod
    def ensure_session_not_locked(cls, session_row: dict) -> None:
        status = session_row.get("status")
        if status in cls.LOCKED_STATUSES:
            raise ValidationError("Academic session is locked for write operations")

    @staticmethod
    def ensure_same_session(
        expected_session_id: str,
        semester_row: dict | None = None,
        class_row: dict | None = None,
        section_row: dict | None = None,
        course_row: dict | None = None,
    ) -> None:
        expected = str(expected_session_id)
        for entity_name, row in (
            ("semester", semester_row),
            ("class", class_row),
            ("section", section_row),
            ("course", course_row),
        ):
            if not row:
                continue
            row_session = str(row.get("academic_session_id"))
            if row_session != expected:
                raise ValidationError(f"{entity_name} does not belong to academic_session_id={expected}")

    @staticmethod
    def ensure_section_belongs_to_class(section_row: dict, class_id: str) -> None:
        if str(section_row.get("class_id")) != str(class_id):
            raise ValidationError("section_id does not belong to class_id")

    @staticmethod
    def ensure_course_belongs_to_class(course_row: dict, class_id: str) -> None:
        if str(course_row.get("class_id")) != str(class_id):
            raise ValidationError("course_id does not belong to class_id")

    @staticmethod
    def ensure_course_belongs_to_semester(course_row: dict, semester_id: str) -> None:
        if str(course_row.get("semester_id")) != str(semester_id):
            raise ValidationError("course_id does not belong to semester_id")
