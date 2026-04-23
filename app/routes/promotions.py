"""Routes for M7 promotions and audit trail."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.database.connection import get_supabase
from app.repositories.m7_promotions_repository import M7PromotionsRepository
from app.schemas.phase3 import PromotionBulkCreate, PromotionStatusUpdate
from app.services.auth_service import get_current_user, require_admin
from app.services.exceptions import NotFoundError, PermissionDeniedError, ValidationError
from app.services.m7_promotions_service import M7PromotionsService

router = APIRouter()


def get_service(supabase: Client = Depends(get_supabase)) -> M7PromotionsService:
    return M7PromotionsService(M7PromotionsRepository(supabase))


@router.get("")
async def list_promotions(
    from_academic_session_id: UUID | None = None,
    to_academic_session_id: UUID | None = None,
    decision_status: str | None = None,
    service: M7PromotionsService = Depends(get_service),
):
    return service.list_promotions(
        {
            "from_academic_session_id": from_academic_session_id,
            "to_academic_session_id": to_academic_session_id,
            "decision_status": decision_status,
        }
    )


@router.post("")
async def create_promotions(
    payload: PromotionBulkCreate,
    current_user: dict = Depends(require_admin),
    service: M7PromotionsService = Depends(get_service),
):
    try:
        return service.create_promotions(payload.model_dump(), current_user)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.put("/{promotion_id}/status")
async def update_status(
    promotion_id: UUID,
    payload: PromotionStatusUpdate,
    current_user: dict = Depends(require_admin),
    service: M7PromotionsService = Depends(get_service),
):
    try:
        return service.update_status(promotion_id, payload.model_dump(exclude_none=True), current_user)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/{promotion_id}/audit-events")
async def list_audit_events(
    promotion_id: UUID,
    current_user: dict = Depends(get_current_user),
    service: M7PromotionsService = Depends(get_service),
):
    try:
        return service.get_audit_events(promotion_id, current_user)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
