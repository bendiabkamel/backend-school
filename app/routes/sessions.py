"""Routes Sessions"""
from uuid import UUID
import logging
from fastapi import APIRouter, Depends
from supabase import Client
from app.database.connection import get_supabase
from app.schemas.schemas import SessionCreate
from app.services.auth_service import require_admin

router = APIRouter()
logger = logging.getLogger("albassir_api.sessions")


@router.get("")
async def list_sessions(formation_id: str = None, supabase: Client = Depends(get_supabase)):
    try:
        query = supabase.table("sessions").select("*, formations(titre)")
        normalized_formation_id = (formation_id or "").strip().lower()
        if normalized_formation_id and normalized_formation_id not in {"all", "null", "undefined"}:
            query = query.eq("formation_id", formation_id)
        result = query.order("date_debut").execute()
        return result.data or []
    except Exception as exc:
        logger.warning("[sessions] list_sessions failed, returning empty list: %s", exc)
        return []


@router.post("")
async def create_session(session: SessionCreate, supabase: Client = Depends(get_supabase),
                         _: dict = Depends(require_admin)):
    data = session.model_dump()
    data["formation_id"] = str(data["formation_id"])
    data["date_debut"] = str(data["date_debut"])
    data["date_fin"] = str(data["date_fin"])
    result = supabase.table("sessions").insert(data).execute()
    return result.data[0]


@router.put("/{session_id}")
async def update_session(session_id: UUID, data: dict,
                         supabase: Client = Depends(get_supabase),
                         _: dict = Depends(require_admin)):
    result = supabase.table("sessions").update(data).eq("id", str(session_id)).execute()
    return result.data[0]
