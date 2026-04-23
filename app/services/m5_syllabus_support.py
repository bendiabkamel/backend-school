"""Optional minimal support for syllabus domain in phase 3."""

from __future__ import annotations

from datetime import datetime, timezone


def syllabus_now() -> str:
    return datetime.now(timezone.utc).isoformat()
