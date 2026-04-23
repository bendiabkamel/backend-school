"""Business service for M1 academic sessions, semesters, and settings."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from app.repositories.m1_sessions_repository import M1SessionsRepository
from app.services.exceptions import NotFoundError, ValidationError


class M1SessionsService:
    def __init__(self, repository: M1SessionsRepository):
        self.repository = repository

    def list_sessions(self, scope: str | None = None) -> list[dict[str, Any]]:
        return self.repository.list_sessions(scope=scope)

    def create_session(self, payload: dict[str, Any], actor_user_id: str) -> dict[str, Any]:
        payload = payload.copy()
        payload["created_by_user_id"] = actor_user_id
        payload["updated_by_user_id"] = actor_user_id

        row = self.repository.create_session(payload)
        if payload.get("is_current"):
            self.activate_current_session(row["id"], actor_user_id)
            row = self.repository.get_session(row["id"]) or row
        return row

    def update_session(self, session_id: UUID | str, payload: dict[str, Any], actor_user_id: str) -> dict[str, Any]:
        session = self.repository.get_session(session_id)
        if not session:
            raise NotFoundError("Academic session not found")

        if "status" in payload:
            self._validate_session_status_transition(current_status=session["status"], new_status=payload["status"])

        merged = {**session, **payload}
        starts_on = merged.get("starts_on")
        ends_on = merged.get("ends_on")
        if starts_on and ends_on and str(ends_on) < str(starts_on):
            raise ValidationError("ends_on must be greater than or equal to starts_on")

        if payload.get("is_current") is True and merged.get("status") != "active":
            raise ValidationError("Only active sessions can be marked current")

        payload = payload.copy()
        payload["updated_by_user_id"] = actor_user_id

        updated = self.repository.update_session(session_id, payload)
        if payload.get("is_current") is True:
            self.activate_current_session(session_id, actor_user_id)
            updated = self.repository.get_session(session_id) or updated
        return updated

    def activate_current_session(self, session_id: UUID | str, actor_user_id: str) -> dict[str, Any]:
        session = self.repository.get_session(session_id)
        if not session:
            raise NotFoundError("Academic session not found")
        if session.get("status") != "active":
            raise ValidationError("Only active sessions can be set as current")

        self.repository.unset_all_current_sessions()
        updated = self.repository.set_current_session(session_id)
        if updated.get("updated_by_user_id") != actor_user_id:
            updated = self.repository.update_session(
                session_id,
                {
                    "updated_by_user_id": actor_user_id,
                    "updated_at": self.repository.now_iso(),
                },
            )
        return updated

    def list_semesters(self, academic_session_id: UUID | str | None = None) -> list[dict[str, Any]]:
        return self.repository.list_semesters(academic_session_id=academic_session_id)

    def create_semester(self, payload: dict[str, Any], actor_user_id: str) -> dict[str, Any]:
        session_id = payload["academic_session_id"]
        session = self.repository.get_session(session_id)
        if not session:
            raise NotFoundError("Academic session not found")

        start_date = payload["start_date"]
        end_date = payload["end_date"]
        if end_date < start_date:
            raise ValidationError("end_date must be greater than or equal to start_date")

        self._validate_semester_overlap(
            academic_session_id=session_id,
            start_date=start_date,
            end_date=end_date,
            semester_id_to_ignore=None,
        )

        payload = payload.copy()
        payload["created_by_user_id"] = actor_user_id
        payload["updated_by_user_id"] = actor_user_id
        return self.repository.create_semester(payload)

    def update_semester(self, semester_id: UUID | str, payload: dict[str, Any], actor_user_id: str) -> dict[str, Any]:
        semester = self.repository.get_semester(semester_id)
        if not semester:
            raise NotFoundError("Semester not found")

        merged = {**semester, **payload}
        if merged["end_date"] < merged["start_date"]:
            raise ValidationError("end_date must be greater than or equal to start_date")

        self._validate_semester_overlap(
            academic_session_id=merged["academic_session_id"],
            start_date=merged["start_date"],
            end_date=merged["end_date"],
            semester_id_to_ignore=str(semester_id),
        )

        payload = payload.copy()
        payload["updated_by_user_id"] = actor_user_id
        return self.repository.update_semester(semester_id, payload)

    def upsert_settings(self, payload: dict[str, Any], actor_user_id: str) -> dict[str, Any]:
        payload = payload.copy()
        settings_scope = payload["settings_scope"]
        session_id = payload.get("academic_session_id")

        if settings_scope == "session":
            if not session_id:
                raise ValidationError("session scope requires academic_session_id")
            session = self.repository.get_session(session_id)
            if not session:
                raise NotFoundError("Academic session not found")
        elif settings_scope == "global":
            if payload.get("academic_session_id") is not None:
                raise ValidationError("global scope cannot define academic_session_id")

        payload["updated_by_user_id"] = actor_user_id
        existing = self.repository.get_settings(settings_scope=settings_scope, academic_session_id=session_id)
        if not existing:
            payload["created_by_user_id"] = actor_user_id

        return self.repository.upsert_settings(payload)

    def get_effective_settings(self, academic_session_id: UUID | str | None) -> dict[str, Any] | None:
        if academic_session_id:
            settings = self.repository.get_settings("session", academic_session_id=academic_session_id)
            if settings:
                return settings
        return self.repository.get_settings("global")

    def _validate_semester_overlap(
        self,
        academic_session_id: UUID | str,
        start_date: date,
        end_date: date,
        semester_id_to_ignore: str | None,
    ) -> None:
        semesters = self.repository.list_semesters(academic_session_id=academic_session_id)
        for semester in semesters:
            if semester_id_to_ignore and semester["id"] == semester_id_to_ignore:
                continue

            existing_start = date.fromisoformat(str(semester["start_date"]))
            existing_end = date.fromisoformat(str(semester["end_date"]))
            overlap = not (end_date < existing_start or start_date > existing_end)
            if overlap:
                raise ValidationError(
                    "Semester date range overlaps with an existing semester in this academic session"
                )

    @staticmethod
    def _validate_session_status_transition(current_status: str, new_status: str) -> None:
        allowed_transitions = {
            "draft": {"draft", "active", "archived"},
            "active": {"active", "closed", "archived"},
            "closed": {"closed", "archived"},
            "archived": {"archived"},
        }
        allowed = allowed_transitions.get(current_status, {current_status})
        if new_status not in allowed:
            raise ValidationError(f"Invalid status transition from {current_status} to {new_status}")
