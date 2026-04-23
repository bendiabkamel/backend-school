"""Routes for M4 exams, grading systems, marks, and final marks."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.database.connection import get_supabase
from app.repositories.m4_grading_repository import M4GradingRepository
from app.schemas.phase3 import (
    ExamRuleUpsert,
    FinalMarksComputeRequest,
    GradingSystemCreate,
    GradeRuleCreate,
    GradeRuleSetCreate,
    MarksBulkUpsert,
    SchoolExamCreate,
    SchoolExamUpdate,
)
from app.services.auth_service import get_current_user, require_formateur_or_admin
from app.services.exceptions import NotFoundError, PermissionDeniedError, ValidationError
from app.services.m4_grading_service import M4GradingService

router = APIRouter()


def get_service(supabase: Client = Depends(get_supabase)) -> M4GradingService:
    return M4GradingService(M4GradingRepository(supabase))


@router.get("/exams")
async def list_exams(
    academic_session_id: UUID | None = None,
    semester_id: UUID | None = None,
    class_id: UUID | None = None,
    section_id: UUID | None = None,
    course_id: UUID | None = None,
    service: M4GradingService = Depends(get_service),
):
    return service.list_exams(
        {
            "academic_session_id": academic_session_id,
            "semester_id": semester_id,
            "class_id": class_id,
            "section_id": section_id,
            "course_id": course_id,
        }
    )


@router.post("/exams")
async def create_exam(
    payload: SchoolExamCreate,
    current_user: dict = Depends(require_formateur_or_admin),
    service: M4GradingService = Depends(get_service),
):
    try:
        return service.create_exam(payload.model_dump(), current_user)
    except (NotFoundError, ValidationError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.put("/exams/{exam_id}")
async def update_exam(
    exam_id: UUID,
    payload: SchoolExamUpdate,
    current_user: dict = Depends(require_formateur_or_admin),
    service: M4GradingService = Depends(get_service),
):
    try:
        return service.update_exam(exam_id, payload.model_dump(exclude_none=True), current_user)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/exams/{exam_id}/lock")
async def lock_exam(
    exam_id: UUID,
    current_user: dict = Depends(require_formateur_or_admin),
    service: M4GradingService = Depends(get_service),
):
    try:
        return service.lock_exam(exam_id, current_user)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/exam-rules")
async def upsert_exam_rule(
    payload: ExamRuleUpsert,
    current_user: dict = Depends(require_formateur_or_admin),
    service: M4GradingService = Depends(get_service),
):
    try:
        return service.upsert_exam_rule(payload.model_dump(), current_user)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/grading-systems")
async def create_grading_system(
    payload: GradingSystemCreate,
    current_user: dict = Depends(require_formateur_or_admin),
    service: M4GradingService = Depends(get_service),
):
    try:
        return service.create_grading_system(payload.model_dump(), current_user)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/grading-systems/{grading_system_id}/rules")
async def create_grade_rules(
    grading_system_id: UUID,
    payload: GradeRuleSetCreate,
    current_user: dict = Depends(require_formateur_or_admin),
    service: M4GradingService = Depends(get_service),
):
    try:
        rules = [rule.model_dump() for rule in payload.rules]
        return service.create_grade_rules(grading_system_id, rules, current_user)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/marks/bulk")
async def upsert_marks(
    payload: MarksBulkUpsert,
    current_user: dict = Depends(require_formateur_or_admin),
    service: M4GradingService = Depends(get_service),
):
    try:
        return service.upsert_marks(payload.model_dump(), current_user)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/final-marks/compute")
async def compute_final_marks(
    payload: FinalMarksComputeRequest,
    current_user: dict = Depends(require_formateur_or_admin),
    service: M4GradingService = Depends(get_service),
):
    try:
        return service.compute_final_marks(payload.model_dump(), current_user)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/final-marks/{final_mark_id}/finalize")
async def finalize_final_mark(
    final_mark_id: UUID,
    current_user: dict = Depends(require_formateur_or_admin),
    service: M4GradingService = Depends(get_service),
):
    try:
        return service.finalize_final_mark(final_mark_id, current_user)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
