"""Shared repository helpers for Supabase-backed modules."""

from __future__ import annotations

from typing import Any

from supabase import Client


class SupabaseRepository:
    """Thin helper around Supabase responses to normalize data extraction."""

    def __init__(self, supabase: Client):
        self.supabase = supabase

    @staticmethod
    def _as_list(result: Any) -> list[dict[str, Any]]:
        data = getattr(result, "data", None)
        if not data:
            return []
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return [data]
        return []

    @classmethod
    def _first_or_none(cls, result: Any) -> dict[str, Any] | None:
        rows = cls._as_list(result)
        return rows[0] if rows else None

    @staticmethod
    def now_iso() -> str:
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()
