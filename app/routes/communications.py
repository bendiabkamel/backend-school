"""Routes for M6 notices, events, and routines."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.database.connection import get_supabase
from app.repositories.m6_communications_repository import M6CommunicationsRepository
from app.schemas.phase3 import EventCreate, NoticeCreate, RoutineBulkCreate
from app.services.auth_service import get_current_user, require_formateur_or_admin
from app.services.exceptions import NotFoundError, PermissionDeniedError, ValidationError
from app.services.m6_communications_service import M6CommunicationsService

router = APIRouter()


def get_service(supabase: Client = Depends(get_supabase)) -> M6CommunicationsService:
    return M6CommunicationsService(M6CommunicationsRepository(supabase))


@router.get("/notices")
async def list_notices(
    academic_session_id: UUID | None = None,
    current_user: dict = Depends(get_current_user),
    service: M6CommunicationsService = Depends(get_service),
):
    return service.list_notices(academic_session_id=academic_session_id, current_user=current_user)


@router.post("/notices")
async def create_notice(
    payload: NoticeCreate,
    current_user: dict = Depends(require_formateur_or_admin),
    service: M6CommunicationsService = Depends(get_service),
):
    try:
        return service.create_notice(payload.model_dump(), current_user)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/events")
async def list_events(
    academic_session_id: UUID | None = None,
    current_user: dict = Depends(get_current_user),
    service: M6CommunicationsService = Depends(get_service),
):
    return service.list_events(academic_session_id=academic_session_id, current_user=current_user)


@router.post("/events")
async def create_event(
    payload: EventCreate,
    current_user: dict = Depends(require_formateur_or_admin),
    service: M6CommunicationsService = Depends(get_service),
):
    try:
        return service.create_event(payload.model_dump(), current_user)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/routines")
async def list_routines(
    academic_session_id: UUID | None = None,
    semester_id: UUID | None = None,
    class_id: UUID | None = None,
    section_id: UUID | None = None,
    course_id: UUID | None = None,
    weekday: int | None = None,
    current_user: dict = Depends(get_current_user),
    service: M6CommunicationsService = Depends(get_service),
):
    return service.list_routines(
        {
            "academic_session_id": academic_session_id,
            "semester_id": semester_id,
            "class_id": class_id,
            "section_id": section_id,
            "course_id": course_id,
            "weekday": weekday,
        },
        current_user=current_user,
    )


@router.post("/routines/bulk")
async def create_routines(
    payload: RoutineBulkCreate,
    current_user: dict = Depends(require_formateur_or_admin),
    service: M6CommunicationsService = Depends(get_service),
):
    try:
        return service.create_routines([item.model_dump() for item in payload.routines], current_user)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
