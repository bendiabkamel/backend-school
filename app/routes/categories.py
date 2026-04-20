"""Routes Catégories"""
from fastapi import APIRouter, Depends
from supabase import Client
from app.database.connection import get_supabase
from app.schemas.schemas import CategoryCreate
from app.services.auth_service import require_admin
from slugify import slugify

router = APIRouter()


@router.get("")
async def list_categories(supabase: Client = Depends(get_supabase)):
    result = supabase.table("categories").select("*").order("name").execute()
    return result.data or []


@router.post("")
async def create_category(cat: CategoryCreate, supabase: Client = Depends(get_supabase),
                          _: dict = Depends(require_admin)):
    data = cat.model_dump()
    data["slug"] = slugify(cat.name)
    result = supabase.table("categories").insert(data).execute()
    return result.data[0]
