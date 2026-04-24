"""Service for routine conflict detection."""

from __future__ import annotations

from datetime import time
from uuid import UUID


def check_time_overlap(
    start_a: time,
    end_a: time,
    start_b: time,
    end_b: time,
) -> bool:
    """Return True if time ranges [start_a, end_a) and [start_b, end_b) overlap."""
    return start_a < end_b and start_b < end_a


def find_conflicts(
    new_weekday: int,
    new_start: time,
    new_end: time,
    existing_routines: list[dict],
    exclude_id: str | None = None,
) -> list[dict]:
    """Return list of conflicting routines from the existing set."""
    conflicts: list[dict] = []
    for routine in existing_routines:
        if exclude_id and str(routine.get("id")) == exclude_id:
            continue
        if routine.get("weekday") != new_weekday:
            continue
        r_start = _parse_time(routine.get("start_time"))
        r_end = _parse_time(routine.get("end_time"))
        if r_start is None or r_end is None:
            continue
        if check_time_overlap(new_start, new_end, r_start, r_end):
            conflicts.append(routine)
    return conflicts


def _parse_time(value: str | None) -> time | None:
    """Parse HH:MM:SS or HH:MM string to time object."""
    if not value:
        return None
    try:
        parts = str(value).split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        second = int(parts[2]) if len(parts) > 2 else 0
        return time(hour, minute, second)
    except Exception:
        return None
