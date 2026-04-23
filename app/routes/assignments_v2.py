"""Routes for M5 assignments and syllabi."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.database.connection import get_supabase
from app.repositories.m5_assignments_repository import M5AssignmentsRepository
from app.schemas.phase3 import (
    AssignmentCreate,
    AssignmentUpdate,
    AssignmentSubmissionCreate,
    AssignmentSubmissionGradeUpdate,
    SyllabusCreate,
    SyllabusUpdate,
)
from app.services.auth_service import get_current_user, require_formateur_or_admin
from app.services.exceptions import NotFoundError, PermissionDeniedError, ValidationError
from app.services.m5_assignments_service import M5AssignmentsService

router = APIRouter()


def get_service(supabase: Client = Depends(get_supabase)) -> M5AssignmentsService:
    return M5AssignmentsService(M5AssignmentsRepository(supabase))


@router.get("")
async def list_assignments(
    academic_session_id: UUID | None = None,
    semester_id: UUID | None = None,
    class_id: UUID | None = None,
    section_id: UUID | None = None,
    course_id: UUID | None = None,
    is_published: bool | None = None,
    service: M5AssignmentsService = Depends(get_service),
):
    return service.list_assignments(
        {
            "academic_session_id": academic_session_id,
            "semester_id": semester_id,
            "class_id": class_id,
            "section_id": section_id,
            "course_id": course_id,
            "is_published": is_published,
        }
    )


@router.post("")
async def create_assignment(
    payload: AssignmentCreate,
    current_user: dict = Depends(require_formateur_or_admin),
    service: M5AssignmentsService = Depends(get_service),
):
    try:
        return service.create_assignment(payload.model_dump(), current_user)
    except (NotFoundError, ValidationError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.put("/{assignment_id}")
async def update_assignment(
    assignment_id: UUID,
    payload: AssignmentUpdate,
    current_user: dict = Depends(require_formateur_or_admin),
    service: M5AssignmentsService = Depends(get_service),
):
    try:
        return service.update_assignment(assignment_id, payload.model_dump(exclude_none=True), current_user)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/{assignment_id}/submissions")
async def create_submission(
    assignment_id: UUID,
    payload: AssignmentSubmissionCreate,
    current_user: dict = Depends(get_current_user),
    service: M5AssignmentsService = Depends(get_service),
):
    try:
        data = payload.model_dump()
        data["assignment_id"] = assignment_id
        return service.create_submission(data, current_user)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.put("/submissions/{submission_id}/grade")
async def grade_submission(
    submission_id: UUID,
    payload: AssignmentSubmissionGradeUpdate,
    current_user: dict = Depends(require_formateur_or_admin),
    service: M5AssignmentsService = Depends(get_service),
):
    try:
        return service.grade_submission(submission_id, payload.model_dump(exclude_none=True), current_user)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/submissions")
async def list_submissions(
    assignment_id: UUID | None = None,
    service: M5AssignmentsService = Depends(get_service),
):
    return service.list_submission_metadata(assignment_id=assignment_id)


@router.get("/syllabi")
async def list_syllabi(
    academic_session_id: UUID | None = None,
    semester_id: UUID | None = None,
    class_id: UUID | None = None,
    course_id: UUID | None = None,
    is_published: bool | None = None,
    service: M5AssignmentsService = Depends(get_service),
):
    return service.list_syllabi(
        {
            "academic_session_id": academic_session_id,
            "semester_id": semester_id,
            "class_id": class_id,
            "course_id": course_id,
            "is_published": is_published,
        }
    )


@router.post("/syllabi")
async def create_syllabus(
    payload: SyllabusCreate,
    current_user: dict = Depends(require_formateur_or_admin),
    service: M5AssignmentsService = Depends(get_service),
):
    try:
        return service.create_syllabus(payload.model_dump(), current_user)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.put("/syllabi/{syllabus_id}")
async def update_syllabus(
    syllabus_id: UUID,
    payload: SyllabusUpdate,
    current_user: dict = Depends(require_formateur_or_admin),
    service: M5AssignmentsService = Depends(get_service),
):
    try:
        return service.update_syllabus(syllabus_id, payload.model_dump(exclude_none=True), current_user)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
