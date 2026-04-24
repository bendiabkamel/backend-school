"""Routes for class routines / timetables."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from supabase import Client

from app.database.connection import get_supabase
from app.schemas.phase3 import RoutineCreate, RoutineUpdate
from app.services.auth_service import get_current_user, require_admin, require_formateur_or_admin
from app.services.routine_service import find_conflicts, _parse_time

router = APIRouter()


@router.get("")
async def list_routines(
    academic_session_id: UUID | None = Query(default=None),
    class_id: UUID | None = Query(default=None),
    section_id: UUID | None = Query(default=None),
    semester_id: UUID | None = Query(default=None),
    supabase: Client = Depends(get_supabase),
    _: dict = Depends(get_current_user),
):
    """List routines with optional filters."""
    query = supabase.table("routines").select(
        "*, school_classes(*), sections(*), courses(*), semesters(*), teacher_assignments(*, users(*))"
    )
    if academic_session_id:
        query = query.eq("academic_session_id", str(academic_session_id))
    if class_id:
        query = query.eq("class_id", str(class_id))
    if section_id:
        query = query.eq("section_id", str(section_id))
    if semester_id:
        query = query.eq("semester_id", str(semester_id))

    result = query.order("weekday").order("start_time").execute()
    return result.data or []


@router.get("/timetable/{section_id}")
async def get_section_timetable(
    section_id: UUID,
    academic_session_id: UUID | None = Query(default=None),
    supabase: Client = Depends(get_supabase),
    _: dict = Depends(get_current_user),
):
    """Return weekly timetable grid for a section, grouped by weekday."""
    query = supabase.table("routines").select(
        "*, school_classes(*), sections(*), courses(*), semesters(*), teacher_assignments(*, users(*))"
    ).eq("section_id", str(section_id))

    if academic_session_id:
        query = query.eq("academic_session_id", str(academic_session_id))

    result = query.order("weekday").order("start_time").execute()
    routines = result.data or []

    # Group by weekday (1=Monday … 7=Sunday)
    timetable: dict[int, list[dict]] = {d: [] for d in range(1, 8)}
    for r in routines:
        day = r.get("weekday", 1)
        if 1 <= day <= 7:
            timetable[day].append(r)

    return timetable


@router.post("")
async def create_routine(
    payload: RoutineCreate,
    supabase: Client = Depends(get_supabase),
    current_user: dict = Depends(require_formateur_or_admin),
):
    """Create a routine slot, checking for time conflicts in the same section."""
    # Fetch existing routines for this section on the same weekday
    existing = (
        supabase.table("routines")
        .select("id, weekday, start_time, end_time")
        .eq("section_id", str(payload.section_id))
        .eq("academic_session_id", str(payload.academic_session_id))
        .execute()
    )

    new_start = payload.start_time
    new_end = payload.end_time
    conflicts = find_conflicts(payload.weekday, new_start, new_end, existing.data or [])

    if conflicts:
        raise HTTPException(
            status_code=409,
            detail=f"Time conflict detected with {len(conflicts)} existing routine(s) on this weekday.",
        )

    data = payload.model_dump()
    data["start_time"] = str(data["start_time"])
    data["end_time"] = str(data["end_time"])
    data["academic_session_id"] = str(data["academic_session_id"])
    data["semester_id"] = str(data["semester_id"])
    data["class_id"] = str(data["class_id"])
    data["section_id"] = str(data["section_id"])
    data["course_id"] = str(data["course_id"])
    if data.get("teacher_assignment_id"):
        data["teacher_assignment_id"] = str(data["teacher_assignment_id"])

    result = supabase.table("routines").insert(data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create routine")
    return result.data[0]


@router.put("/{routine_id}")
async def update_routine(
    routine_id: UUID,
    payload: RoutineUpdate,
    supabase: Client = Depends(get_supabase),
    current_user: dict = Depends(require_formateur_or_admin),
):
    """Update a routine slot."""
    existing_row = (
        supabase.table("routines")
        .select("*")
        .eq("id", str(routine_id))
        .single()
        .execute()
    )
    if not existing_row.data:
        raise HTTPException(status_code=404, detail="Routine not found")

    row = existing_row.data
    updates = payload.model_dump(exclude_none=True)

    # Determine merged values for conflict check
    check_weekday = updates.get("weekday", row["weekday"])
    check_start = _parse_time(str(updates.get("start_time", row["start_time"])))
    check_end = _parse_time(str(updates.get("end_time", row["end_time"])))

    if check_start and check_end:
        peers = (
            supabase.table("routines")
            .select("id, weekday, start_time, end_time")
            .eq("section_id", row["section_id"])
            .eq("academic_session_id", row["academic_session_id"])
            .execute()
        )
        conflicts = find_conflicts(
            check_weekday,
            check_start,
            check_end,
            peers.data or [],
            exclude_id=str(routine_id),
        )
        if conflicts:
            raise HTTPException(
                status_code=409,
                detail=f"Time conflict with {len(conflicts)} existing routine(s).",
            )

    # Serialize time fields
    if "start_time" in updates:
        updates["start_time"] = str(updates["start_time"])
    if "end_time" in updates:
        updates["end_time"] = str(updates["end_time"])

    result = supabase.table("routines").update(updates).eq("id", str(routine_id)).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Routine not found")
    return result.data[0]


@router.delete("/{routine_id}")
async def delete_routine(
    routine_id: UUID,
    supabase: Client = Depends(get_supabase),
    _: dict = Depends(require_admin),
):
    """Delete a routine slot (admin only)."""
    result = supabase.table("routines").delete().eq("id", str(routine_id)).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Routine not found")
    return {"message": "Routine deleted successfully"}
