"""Business service for M6 notices, events, and routines."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.repositories.m6_communications_repository import M6CommunicationsRepository
from app.services.exceptions import NotFoundError, PermissionDeniedError, ValidationError
from app.services.session_isolation_service import SessionIsolationService


class M6CommunicationsService:
    def __init__(self, repository: M6CommunicationsRepository):
        self.repository = repository

    def list_notices(self, academic_session_id: UUID | str | None = None, current_user: dict | None = None) -> list[dict[str, Any]]:
        notices = self.repository.list_notices(academic_session_id=academic_session_id)
        return self._filter_audience(notices, current_user)

    def create_notice(self, payload: dict[str, Any], current_user: dict) -> dict[str, Any]:
        self._ensure_staff(current_user)
        session = self.repository.get_academic_session(payload["academic_session_id"])
        if not session:
            raise NotFoundError("Academic session not found")
        SessionIsolationService.ensure_session_not_locked(session)
        self._validate_notice_scope(payload)

        payload = payload.copy()
        payload["created_by_user_id"] = current_user["id"]
        payload["updated_by_user_id"] = current_user["id"]
        return self.repository.create_notice(payload)

    def list_events(self, academic_session_id: UUID | str | None = None, current_user: dict | None = None) -> list[dict[str, Any]]:
        events = self.repository.list_events(academic_session_id=academic_session_id)
        return self._filter_audience(events, current_user)

    def create_event(self, payload: dict[str, Any], current_user: dict) -> dict[str, Any]:
        self._ensure_staff(current_user)
        session = self.repository.get_academic_session(payload["academic_session_id"])
        if not session:
            raise NotFoundError("Academic session not found")
        SessionIsolationService.ensure_session_not_locked(session)
        if payload["ends_at"] < payload["starts_at"]:
            raise ValidationError("ends_at must be greater than or equal to starts_at")
        self._validate_audience_scope(payload)

        payload = payload.copy()
        payload["created_by_user_id"] = current_user["id"]
        payload["updated_by_user_id"] = current_user["id"]
        return self.repository.create_event(payload)

    def list_routines(self, filters: dict[str, Any], current_user: dict | None = None) -> list[dict[str, Any]]:
        routines = self.repository.list_routines(**filters)
        return self._filter_audience(routines, current_user)

    def create_routines(self, payloads: list[dict[str, Any]], current_user: dict) -> list[dict[str, Any]]:
        self._ensure_staff(current_user)
        normalized = []
        for payload in payloads:
            if payload["end_time"] <= payload["start_time"]:
                raise ValidationError("end_time must be greater than start_time")
            session = self.repository.get_academic_session(payload["academic_session_id"])
            if not session:
                raise NotFoundError("Academic session not found")
            SessionIsolationService.ensure_session_not_locked(session)
            normalized.append({**payload, "created_by_user_id": current_user["id"], "updated_by_user_id": current_user["id"]})
        return self.repository.create_routines(normalized)

    def _filter_audience(self, rows: list[dict[str, Any]], current_user: dict | None) -> list[dict[str, Any]]:
        if not current_user:
            return rows
        role = current_user.get("role")
        if role in {"admin", "formateur"}:
            return rows
        owner_enrollments = self.repository.list_active_enrollments_for_owner(current_user["id"])
        enrollment_contexts = {
            (str(row.get("academic_session_id")), str(row.get("section_id")), str(row.get("class_id")))
            for row in owner_enrollments
        }
        filtered: list[dict[str, Any]] = []
        for row in rows:
            scope = row.get("audience_scope")
            if scope == "all":
                filtered.append(row)
                continue
            class_id = str(row.get("class_id")) if row.get("class_id") else None
            section_id = str(row.get("section_id")) if row.get("section_id") else None
            session_id = str(row.get("academic_session_id")) if row.get("academic_session_id") else None
            if (session_id, section_id, class_id) in enrollment_contexts:
                filtered.append(row)
        return filtered

    @staticmethod
    def _validate_notice_scope(payload: dict[str, Any]) -> None:
        if payload.get("audience_scope") == "section" and not payload.get("section_id"):
            raise ValidationError("section_id is required for section-scoped notices")
        if payload.get("audience_scope") == "class" and not payload.get("class_id"):
            raise ValidationError("class_id is required for class-scoped notices")

    @staticmethod
    def _validate_audience_scope(payload: dict[str, Any]) -> None:
        scope = payload.get("audience_scope", "all")
        if scope == "section" and not payload.get("section_id"):
            raise ValidationError("section_id is required for section-scoped rows")
        if scope == "class" and not payload.get("class_id"):
            raise ValidationError("class_id is required for class-scoped rows")
        if scope not in {"all", "students", "teachers", "class", "section"}:
            raise ValidationError("Invalid audience scope")

    @staticmethod
    def _ensure_staff(current_user: dict) -> None:
        if current_user.get("role") not in {"admin", "formateur"}:
            raise PermissionDeniedError("Operation requires teacher or admin role")
