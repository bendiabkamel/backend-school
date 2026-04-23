"""Routes for M3 attendance split model."""

from __future__ import annotations

from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.database.connection import get_supabase
from app.repositories.m3_attendance_repository import M3AttendanceRepository
from app.schemas.phase3 import AttendanceBulkCreate
from app.services.auth_service import get_current_user, require_formateur_or_admin
from app.services.exceptions import NotFoundError, PermissionDeniedError, ValidationError
from app.services.m3_attendance_service import M3AttendanceService

router = APIRouter()


def get_service(supabase: Client = Depends(get_supabase)) -> M3AttendanceService:
    return M3AttendanceService(M3AttendanceRepository(supabase))


@router.post("")
async def mark_bulk(
    payload: AttendanceBulkCreate,
    current_user: dict = Depends(require_formateur_or_admin),
    service: M3AttendanceService = Depends(get_service),
):
    try:
        return service.mark_bulk(payload.model_dump(), current_user)
    except (NotFoundError, ValidationError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.get("/student/{owner_user_id}")
async def get_student_attendance(
    owner_user_id: str,
    current_user: dict = Depends(get_current_user),
    service: M3AttendanceService = Depends(get_service),
    from_date: date | None = None,
    to_date: date | None = None,
):
    try:
        return service.get_student_attendance(owner_user_id, current_user, from_date=from_date, to_date=to_date)
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.get("/report")
async def report(
    academic_session_id: str,
    current_user: dict = Depends(require_formateur_or_admin),
    service: M3AttendanceService = Depends(get_service),
    semester_id: str | None = None,
    class_id: str | None = None,
    section_id: str | None = None,
    course_id: str | None = None,
    attendance_date: date | None = None,
):
    try:
        return service.report(
            current_user,
            academic_session_id=academic_session_id,
            semester_id=semester_id,
            class_id=class_id,
            section_id=section_id,
            course_id=course_id,
            attendance_date=attendance_date,
        )
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
