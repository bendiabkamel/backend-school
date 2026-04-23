"""Repositories for M1 academic sessions, semesters, and settings."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.repositories.base_repository import SupabaseRepository


class M1SessionsRepository(SupabaseRepository):
    table_sessions = "academic_sessions"
    table_semesters = "semesters"
    table_settings = "academic_settings"

    def list_sessions(self, scope: str | None = None) -> list[dict[str, Any]]:
        query = self.supabase.table(self.table_sessions).select("*")
        if scope == "active":
            query = query.eq("status", "active")
        elif scope == "archived":
            query = query.eq("status", "archived")
        result = query.order("starts_on", desc=False).execute()
        return self._as_list(result)

    def get_session(self, session_id: UUID | str) -> dict[str, Any] | None:
        result = (
            self.supabase.table(self.table_sessions)
            .select("*")
            .eq("id", str(session_id))
            .limit(1)
            .execute()
        )
        return self._first_or_none(result)

    def get_current_session(self) -> dict[str, Any] | None:
        result = (
            self.supabase.table(self.table_sessions)
            .select("*")
            .eq("is_current", True)
            .limit(1)
            .execute()
        )
        return self._first_or_none(result)

    def create_session(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.supabase.table(self.table_sessions).insert(payload).execute()
        row = self._first_or_none(result)
        if not row:
            raise ValueError("Failed to create academic session")
        return row

    def update_session(self, session_id: UUID | str, payload: dict[str, Any]) -> dict[str, Any]:
        result = (
            self.supabase.table(self.table_sessions)
            .update(payload)
            .eq("id", str(session_id))
            .execute()
        )
        row = self._first_or_none(result)
        if not row:
            raise ValueError("Academic session not found")
        return row

    def unset_all_current_sessions(self) -> None:
        self.supabase.table(self.table_sessions).update({"is_current": False}).eq("is_current", True).execute()

    def set_current_session(self, session_id: UUID | str) -> dict[str, Any]:
        result = (
            self.supabase.table(self.table_sessions)
            .update({"is_current": True, "updated_at": self.now_iso()})
            .eq("id", str(session_id))
            .execute()
        )
        row = self._first_or_none(result)
        if not row:
            raise ValueError("Academic session not found")
        return row

    def list_semesters(self, academic_session_id: UUID | str | None = None) -> list[dict[str, Any]]:
        query = self.supabase.table(self.table_semesters).select("*")
        if academic_session_id is not None:
            query = query.eq("academic_session_id", str(academic_session_id))
        result = query.order("start_date", desc=False).execute()
        return self._as_list(result)

    def get_semester(self, semester_id: UUID | str) -> dict[str, Any] | None:
        result = (
            self.supabase.table(self.table_semesters)
            .select("*")
            .eq("id", str(semester_id))
            .limit(1)
            .execute()
        )
        return self._first_or_none(result)

    def create_semester(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.supabase.table(self.table_semesters).insert(payload).execute()
        row = self._first_or_none(result)
        if not row:
            raise ValueError("Failed to create semester")
        return row

    def update_semester(self, semester_id: UUID | str, payload: dict[str, Any]) -> dict[str, Any]:
        result = (
            self.supabase.table(self.table_semesters)
            .update(payload)
            .eq("id", str(semester_id))
            .execute()
        )
        row = self._first_or_none(result)
        if not row:
            raise ValueError("Semester not found")
        return row

    def get_settings(self, settings_scope: str, academic_session_id: UUID | str | None = None) -> dict[str, Any] | None:
        query = self.supabase.table(self.table_settings).select("*").eq("settings_scope", settings_scope)
        if settings_scope == "session" and academic_session_id is not None:
            query = query.eq("academic_session_id", str(academic_session_id))
        result = query.limit(1).execute()
        return self._first_or_none(result)

    def upsert_settings(self, payload: dict[str, Any]) -> dict[str, Any]:
        settings_scope = payload["settings_scope"]
        session_id = payload.get("academic_session_id")
        existing = self.get_settings(settings_scope=settings_scope, academic_session_id=session_id)
        if existing:
            result = (
                self.supabase.table(self.table_settings)
                .update(payload)
                .eq("id", existing["id"])
                .execute()
            )
        else:
            result = self.supabase.table(self.table_settings).insert(payload).execute()

        row = self._first_or_none(result)
        if not row:
            raise ValueError("Failed to upsert academic settings")
        return row
