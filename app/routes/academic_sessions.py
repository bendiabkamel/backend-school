"""Routes for M1 academic sessions, semesters, and academic settings."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.database.connection import get_supabase
from app.schemas.phase3 import AcademicSettingsUpsert, SchoolSessionCreate, SchoolSessionUpdate, SemesterCreate, SemesterUpdate
from app.services.auth_service import get_current_user, require_admin
from app.repositories.m1_sessions_repository import M1SessionsRepository
from app.services.m1_sessions_service import M1SessionsService
from app.services.exceptions import NotFoundError, PermissionDeniedError, ValidationError

router = APIRouter()


def get_service(supabase: Client = Depends(get_supabase)) -> M1SessionsService:
    return M1SessionsService(M1SessionsRepository(supabase))


@router.get("")
async def list_sessions(scope: str | None = None, service: M1SessionsService = Depends(get_service)):
    return service.list_sessions(scope=scope)


@router.get("/current")
async def get_current_session(service: M1SessionsService = Depends(get_service)):
    return service.repository.get_current_session()


@router.post("")
async def create_session(
    payload: SchoolSessionCreate,
    current_user: dict = Depends(require_admin),
    service: M1SessionsService = Depends(get_service),
):
    try:
        return service.create_session(payload.model_dump(), current_user["id"])
    except (ValidationError, NotFoundError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.put("/{session_id}")
async def update_session(
    session_id: UUID,
    payload: SchoolSessionUpdate,
    current_user: dict = Depends(require_admin),
    service: M1SessionsService = Depends(get_service),
):
    try:
        return service.update_session(session_id, payload.model_dump(exclude_none=True), current_user["id"])
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/{session_id}/activate")
async def activate_session(
    session_id: UUID,
    current_user: dict = Depends(require_admin),
    service: M1SessionsService = Depends(get_service),
):
    try:
        return service.activate_current_session(session_id, current_user["id"])
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/semesters")
async def list_semesters(academic_session_id: UUID | None = None, service: M1SessionsService = Depends(get_service)):
    return service.list_semesters(academic_session_id=academic_session_id)


@router.post("/semesters")
async def create_semester(
    payload: SemesterCreate,
    current_user: dict = Depends(require_admin),
    service: M1SessionsService = Depends(get_service),
):
    try:
        return service.create_semester(payload.model_dump(), current_user["id"])
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.put("/semesters/{semester_id}")
async def update_semester(
    semester_id: UUID,
    payload: SemesterUpdate,
    current_user: dict = Depends(require_admin),
    service: M1SessionsService = Depends(get_service),
):
    try:
        return service.update_semester(semester_id, payload.model_dump(exclude_none=True), current_user["id"])
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/settings")
async def get_settings(academic_session_id: UUID | None = None, service: M1SessionsService = Depends(get_service)):
    return service.get_effective_settings(academic_session_id)


@router.post("/settings")
async def upsert_settings(
    payload: AcademicSettingsUpsert,
    current_user: dict = Depends(require_admin),
    service: M1SessionsService = Depends(get_service),
):
    try:
        return service.upsert_settings(payload.model_dump(), current_user["id"])
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
