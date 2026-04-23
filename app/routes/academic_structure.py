"""Routes for M2 school classes, sections, courses, enrollments, and teacher assignments."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from supabase import Client

from app.database.connection import get_supabase
from app.repositories.m1_sessions_repository import M1SessionsRepository
from app.repositories.m2_structure_repository import M2StructureRepository
from app.schemas.phase3 import (
    CourseCreate,
    CourseUpdate,
    SchoolClassCreate,
    SchoolClassUpdate,
    SectionCreate,
    SectionUpdate,
    StudentEnrollmentCreate,
    StudentEnrollmentStatusUpdate,
    TeacherAssignmentBulkCreate,
)
from app.services.auth_service import get_current_user, require_admin, require_formateur_or_admin
from app.services.exceptions import NotFoundError, PermissionDeniedError, ValidationError
from app.services.m2_structure_service import M2StructureService

router = APIRouter()


def get_service(supabase: Client = Depends(get_supabase)) -> M2StructureService:
    return M2StructureService(M2StructureRepository(supabase), M1SessionsRepository(supabase))


@router.get("/classes")
async def list_classes(academic_session_id: UUID | None = None, service: M2StructureService = Depends(get_service)):
    return service.list_classes(academic_session_id=academic_session_id)


@router.post("/classes")
async def create_class(
    payload: SchoolClassCreate,
    current_user: dict = Depends(require_admin),
    service: M2StructureService = Depends(get_service),
):
    try:
        return service.create_class(payload.model_dump(), current_user["id"])
    except (NotFoundError, ValidationError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.put("/classes/{class_id}")
async def update_class(
    class_id: UUID,
    payload: SchoolClassUpdate,
    current_user: dict = Depends(require_admin),
    service: M2StructureService = Depends(get_service),
):
    try:
        return service.update_class(class_id, payload.model_dump(exclude_none=True), current_user["id"])
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/sections")
async def list_sections(
    academic_session_id: UUID | None = None,
    class_id: UUID | None = None,
    service: M2StructureService = Depends(get_service),
):
    return service.list_sections(academic_session_id=academic_session_id, class_id=class_id)


@router.post("/sections")
async def create_section(
    payload: SectionCreate,
    current_user: dict = Depends(require_admin),
    service: M2StructureService = Depends(get_service),
):
    try:
        return service.create_section(payload.model_dump(), current_user["id"])
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.put("/sections/{section_id}")
async def update_section(
    section_id: UUID,
    payload: SectionUpdate,
    current_user: dict = Depends(require_admin),
    service: M2StructureService = Depends(get_service),
):
    try:
        return service.update_section(section_id, payload.model_dump(exclude_none=True), current_user["id"])
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/courses")
async def list_courses(
    academic_session_id: UUID | None = None,
    semester_id: UUID | None = None,
    class_id: UUID | None = None,
    service: M2StructureService = Depends(get_service),
):
    return service.list_courses(academic_session_id=academic_session_id, semester_id=semester_id, class_id=class_id)


@router.post("/courses")
async def create_course(
    payload: CourseCreate,
    current_user: dict = Depends(require_admin),
    service: M2StructureService = Depends(get_service),
):
    try:
        return service.create_course(payload.model_dump(), current_user["id"])
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.put("/courses/{course_id}")
async def update_course(
    course_id: UUID,
    payload: CourseUpdate,
    current_user: dict = Depends(require_admin),
    service: M2StructureService = Depends(get_service),
):
    try:
        return service.update_course(course_id, payload.model_dump(exclude_none=True), current_user["id"])
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/enrollments")
async def list_enrollments(
    current_user: dict = Depends(get_current_user),
    service: M2StructureService = Depends(get_service),
    student_id: UUID | None = None,
    owner_user_id: UUID | None = None,
    academic_session_id: UUID | None = None,
    class_id: UUID | None = None,
    section_id: UUID | None = None,
    enrollment_status: str | None = None,
):
    filters = {
        "student_id": student_id,
        "owner_user_id": owner_user_id,
        "academic_session_id": academic_session_id,
        "class_id": class_id,
        "section_id": section_id,
        "enrollment_status": enrollment_status,
    }
    try:
        return service.list_enrollments(current_user, filters)
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.post("/enrollments")
async def create_enrollment(
    payload: StudentEnrollmentCreate,
    current_user: dict = Depends(require_admin),
    service: M2StructureService = Depends(get_service),
):
    try:
        return service.create_enrollment(payload.model_dump(), current_user["id"])
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.put("/enrollments/{enrollment_id}/status")
async def update_enrollment_status(
    enrollment_id: UUID,
    payload: StudentEnrollmentStatusUpdate,
    current_user: dict = Depends(require_admin),
    service: M2StructureService = Depends(get_service),
):
    try:
        return service.update_enrollment_status(enrollment_id, payload.model_dump(exclude_none=True), current_user["id"])
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/teacher-assignments")
async def list_teacher_assignments(
    teacher_id: UUID | None = None,
    academic_session_id: UUID | None = None,
    service: M2StructureService = Depends(get_service),
):
    if not teacher_id:
        return []
    return service.repository.list_teacher_assignments(teacher_id=teacher_id, academic_session_id=academic_session_id)


@router.post("/teacher-assignments/bulk")
async def bulk_teacher_assignments(
    payload: TeacherAssignmentBulkCreate,
    current_user: dict = Depends(require_admin),
    service: M2StructureService = Depends(get_service),
):
    try:
        return service.bulk_assign_teachers([item.model_dump() for item in payload.assignments], current_user["id"])
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
