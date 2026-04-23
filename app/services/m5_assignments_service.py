"""Business service for M5 assignments and syllabi."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.repositories.m5_assignments_repository import M5AssignmentsRepository
from app.services.exceptions import NotFoundError, PermissionDeniedError, ValidationError
from app.services.session_isolation_service import SessionIsolationService


class M5AssignmentsService:
    def __init__(self, repository: M5AssignmentsRepository):
        self.repository = repository

    def list_assignments(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        return self.repository.list_assignments(**filters)

    def list_syllabi(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        return self.repository.list_syllabi(**filters)

    def create_assignment(self, payload: dict[str, Any], current_user: dict) -> dict[str, Any]:
        self._ensure_staff(current_user)
        session = self.repository.get_academic_session(payload["academic_session_id"])
        if not session:
            raise NotFoundError("Academic session not found")
        SessionIsolationService.ensure_session_not_locked(session)

        payload = payload.copy()
        if not payload.get("assigned_at"):
            payload["assigned_at"] = datetime.now(timezone.utc).isoformat()

        self._validate_assignment_due_dates(payload.get("assigned_at"), payload.get("due_at"))
        self._ensure_teacher_access_for_context(payload, current_user)

        payload["created_by_user_id"] = current_user["id"]
        payload["updated_by_user_id"] = current_user["id"]
        return self.repository.create_assignment(payload)

    def update_assignment(self, assignment_id: UUID | str, payload: dict[str, Any], current_user: dict) -> dict[str, Any]:
        assignment = self.repository.get_assignment(assignment_id)
        if not assignment:
            raise NotFoundError("Assignment not found")

        session = self.repository.get_academic_session(assignment["academic_session_id"])
        if not session:
            raise NotFoundError("Academic session not found")
        SessionIsolationService.ensure_session_not_locked(session)

        self._ensure_assignment_teacher_access(assignment, current_user)

        merged = {**assignment, **payload}
        self._validate_assignment_due_dates(merged.get("assigned_at"), merged.get("due_at"))

        payload = payload.copy()
        payload["updated_by_user_id"] = current_user["id"]
        return self.repository.update_assignment(assignment_id, payload)

    def create_submission(self, payload: dict[str, Any], current_user: dict) -> dict[str, Any]:
        assignment = self.repository.get_assignment(payload["assignment_id"])
        if not assignment:
            raise NotFoundError("Assignment not found")
        if not assignment.get("is_published", False):
            raise ValidationError("Assignment is not published")

        enrollment = self.repository.get_enrollment(payload["enrollment_id"])
        if not enrollment:
            raise NotFoundError("Enrollment not found")
        if str(enrollment["owner_user_id"]) != str(current_user["id"]) and current_user.get("role") != "admin":
            raise PermissionDeniedError("Students can only submit for their own enrollment")

        self._ensure_assignment_submission_context(assignment, enrollment)

        payload = payload.copy()
        payload.pop("submission_metadata", None)
        if current_user.get("role") == "admin":
            payload["owner_user_id"] = str(payload.get("owner_user_id") or enrollment["owner_user_id"])
        else:
            payload["owner_user_id"] = current_user["id"]
        payload["submitted_at"] = payload.get("submitted_at") or datetime.now(timezone.utc).isoformat()
        self._validate_submission_timing(assignment, payload)
        return self.repository.create_submission(payload)

    def grade_submission(self, submission_id: UUID | str, payload: dict[str, Any], current_user: dict) -> dict[str, Any]:
        submission = self.repository.get_submission(submission_id)
        if not submission:
            raise NotFoundError("Submission not found")
        assignment = self.repository.get_assignment(submission["assignment_id"])
        if not assignment:
            raise NotFoundError("Assignment not found")
        self._ensure_assignment_teacher_access(assignment, current_user)

        payload = payload.copy()
        score = payload.get("score")
        if score is not None and Decimal(str(score)) > Decimal(str(assignment["max_score"])):
            raise ValidationError("score cannot exceed assignment max_score")

        payload.setdefault("submission_status", "graded")
        payload["graded_by_user_id"] = current_user["id"]
        payload["graded_at"] = datetime.now(timezone.utc).isoformat()
        return self.repository.update_submission(submission_id, payload)

    def create_syllabus(self, payload: dict[str, Any], current_user: dict) -> dict[str, Any]:
        self._ensure_staff(current_user)
        session = self.repository.get_academic_session(payload["academic_session_id"])
        if not session:
            raise NotFoundError("Academic session not found")
        SessionIsolationService.ensure_session_not_locked(session)

        payload = payload.copy()
        payload["created_by_user_id"] = current_user["id"]
        payload["updated_by_user_id"] = current_user["id"]
        return self.repository.create_syllabus(payload)

    def update_syllabus(self, syllabus_id: UUID | str, payload: dict[str, Any], current_user: dict) -> dict[str, Any]:
        syllabus = self.repository.get_syllabus(syllabus_id)
        if not syllabus:
            raise NotFoundError("Syllabus not found")

        session = self.repository.get_academic_session(syllabus["academic_session_id"])
        if not session:
            raise NotFoundError("Academic session not found")
        SessionIsolationService.ensure_session_not_locked(session)

        self._ensure_staff(current_user)
        payload = payload.copy()
        payload["updated_by_user_id"] = current_user["id"]
        return self.repository.update_syllabus(syllabus_id, payload)

    def list_submission_metadata(self, assignment_id: UUID | str | None = None) -> list[dict[str, Any]]:
        return self.repository.list_submissions(assignment_id=assignment_id)

    @staticmethod
    def _ensure_staff(current_user: dict) -> None:
        if current_user.get("role") not in {"admin", "formateur"}:
            raise PermissionDeniedError("Operation requires teacher or admin role")

    def _ensure_assignment_teacher_access(self, assignment: dict[str, Any], current_user: dict) -> None:
        if current_user.get("role") == "admin":
            return
        assignments = self.repository.list_teacher_assignments(
            teacher_id=current_user["id"],
            academic_session_id=assignment["academic_session_id"],
            semester_id=assignment["semester_id"],
            class_id=assignment["class_id"],
            section_id=assignment["section_id"],
            course_id=assignment["course_id"],
        )
        if not assignments:
            raise PermissionDeniedError("Teacher is not assigned to this assignment context")

    def _ensure_teacher_access_for_context(self, context: dict[str, Any], current_user: dict) -> None:
        if current_user.get("role") == "admin":
            return
        assignments = self.repository.list_teacher_assignments(
            teacher_id=current_user["id"],
            academic_session_id=context["academic_session_id"],
            semester_id=context["semester_id"],
            class_id=context["class_id"],
            section_id=context["section_id"],
            course_id=context["course_id"],
        )
        if not assignments:
            raise PermissionDeniedError("Teacher is not assigned to this assignment context")

    @staticmethod
    def _ensure_assignment_submission_context(assignment: dict[str, Any], enrollment: dict[str, Any]) -> None:
        context_map = {
            "academic_session_id": "academic_session_id",
            "semester_id": "semester_id",
            "class_id": "class_id",
            "section_id": "section_id",
        }
        for assignment_key, enrollment_key in context_map.items():
            if str(assignment.get(assignment_key)) != str(enrollment.get(enrollment_key)):
                raise ValidationError(f"Enrollment does not belong to assignment {assignment_key}")

    @staticmethod
    def _parse_datetime(value: Any, field_name: str) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            result = value
        elif isinstance(value, str):
            normalized = value.replace("Z", "+00:00")
            try:
                result = datetime.fromisoformat(normalized)
            except ValueError as exc:
                raise ValidationError(f"{field_name} must be a valid ISO datetime") from exc
        else:
            raise ValidationError(f"{field_name} must be a valid ISO datetime")

        if result.tzinfo is None:
            result = result.replace(tzinfo=timezone.utc)
        return result

    def _validate_assignment_due_dates(self, assigned_at: Any, due_at: Any) -> None:
        assigned_at_dt = self._parse_datetime(assigned_at, "assigned_at")
        due_at_dt = self._parse_datetime(due_at, "due_at")
        if assigned_at_dt and due_at_dt and due_at_dt < assigned_at_dt:
            raise ValidationError("due_at must be greater than or equal to assigned_at")

    def _validate_submission_timing(self, assignment: dict[str, Any], payload: dict[str, Any]) -> None:
        due_at_dt = self._parse_datetime(assignment.get("due_at"), "due_at")
        submitted_at_dt = self._parse_datetime(payload.get("submitted_at"), "submitted_at")
        if due_at_dt and submitted_at_dt and submitted_at_dt > due_at_dt:
            if not assignment.get("allow_late_submission", False):
                raise ValidationError("Late submission is not allowed for this assignment")
