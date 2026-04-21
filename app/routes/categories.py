"""Routes Catégories"""
from fastapi import APIRouter, Depends, HTTPException
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


@router.get("/{category_id}")
async def get_category(category_id: str, supabase: Client = Depends(get_supabase)):
    result = supabase.table("categories").select("*").eq("id", category_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Catégorie introuvable")
    return result.data[0]


@router.post("")
async def create_category(
    cat: CategoryCreate,
    supabase: Client = Depends(get_supabase),
    _: dict = Depends(require_admin),
):
    slug = cat.slug or slugify(cat.name)

    # Vérifier unicité du name
    name_check = supabase.table("categories").select("id").eq("name", cat.name).execute()
    if name_check.data:
        raise HTTPException(status_code=409, detail="Ce nom de catégorie existe déjà")

    # Vérifier unicité du slug
    slug_check = supabase.table("categories").select("id").eq("slug", slug).execute()
    if slug_check.data:
        raise HTTPException(status_code=409, detail="Ce slug est déjà utilisé")

    data = cat.model_dump(exclude={"slug"})
    data["slug"] = slug
    result = supabase.table("categories").insert(data).execute()
    return result.data[0]
