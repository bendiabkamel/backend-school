"""
Routes Formations — CRUD complet
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from supabase import Client
from slugify import slugify

from app.database.connection import get_supabase
from app.schemas.schemas import FormationCreate, FormationUpdate, FormationResponse
from app.services.auth_service import get_current_user, require_admin

router = APIRouter()
MAX_IMAGE_SIZE = 5 * 1024 * 1024


@router.get("", response_model=List[dict])
async def list_formations(
    categorie: Optional[str] = Query(None),
    published_only: bool = Query(True),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    supabase: Client = Depends(get_supabase),
):
    """Liste publique des formations avec filtres"""
    query = supabase.table("formations").select(
        "*, categories(name, slug, color), formateurs(full_name, photo_url)"
    )

    if published_only:
        query = query.eq("is_published", True)

    if categorie:
        # Filtrer par slug de catégorie
        cat = supabase.table("categories").select("id").eq("slug", categorie).single().execute()
        if cat.data:
            query = query.eq("categorie_id", cat.data["id"])

    if search:
        query = query.ilike("titre", f"%{search}%")

    result = query.range(skip, skip + limit - 1).order("created_at", desc=True).execute()
    return result.data or []


@router.get("/{formation_id}", response_model=dict)
async def get_formation(
    formation_id: UUID,
    supabase: Client = Depends(get_supabase),
):
    """Détail d'une formation avec ses modules"""
    result = supabase.table("formations").select(
        "*, categories(*), formateurs(*)"
    ).eq("id", str(formation_id)).single().execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Formation introuvable")

    # Récupérer les modules publiés
    modules = supabase.table("elearning_modules").select(
        "*, lessons(id, titre, type, duree_minutes, ordre)"
    ).eq("formation_id", str(formation_id)).eq("is_published", True).order("ordre").execute()

    # Récupérer les sessions à venir
    from datetime import date
    sessions = supabase.table("sessions").select("*").eq(
        "formation_id", str(formation_id)
    ).gte("date_debut", str(date.today())).order("date_debut").execute()

    return {
        **result.data,
        "modules": modules.data or [],
        "sessions": sessions.data or [],
    }


@router.post("", response_model=dict)
async def create_formation(
    formation: FormationCreate,
    supabase: Client = Depends(get_supabase),
    _: dict = Depends(require_admin),
):
    """Créer une nouvelle formation (admin)"""
    slug = slugify(formation.titre)

    # Vérifier unicité du slug
    existing = supabase.table("formations").select("id").eq("slug", slug).execute()
    if existing.data:
        slug = f"{slug}-{len(existing.data) + 1}"

    data = formation.model_dump()
    data["slug"] = slug
    data["categorie_id"] = str(data["categorie_id"]) if data.get("categorie_id") else None
    data["formateur_id"] = str(data["formateur_id"]) if data.get("formateur_id") else None

    result = supabase.table("formations").insert(data).execute()
    return result.data[0]


@router.put("/{formation_id}", response_model=dict)
async def update_formation(
    formation_id: UUID,
    formation: FormationUpdate,
    supabase: Client = Depends(get_supabase),
    _: dict = Depends(require_admin),
):
    """Modifier une formation (admin)"""
    from datetime import datetime
    data = formation.model_dump(exclude_unset=True)
    data["updated_at"] = datetime.utcnow().isoformat()

    if "categorie_id" in data and data["categorie_id"]:
        data["categorie_id"] = str(data["categorie_id"])
    if "formateur_id" in data and data["formateur_id"]:
        data["formateur_id"] = str(data["formateur_id"])

    result = supabase.table("formations").update(data).eq(
        "id", str(formation_id)
    ).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Formation introuvable")
    return result.data[0]


@router.delete("/{formation_id}")
async def delete_formation(
    formation_id: UUID,
    supabase: Client = Depends(get_supabase),
    _: dict = Depends(require_admin),
):
    """Supprimer une formation (admin)"""
    result = supabase.table("formations").delete().eq("id", str(formation_id)).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Formation introuvable")
    return {"message": "Formation supprimée avec succès"}


@router.post("/{formation_id}/image")
async def upload_formation_image(
    formation_id: UUID,
    file: UploadFile = File(...),
    supabase: Client = Depends(get_supabase),
    _: dict = Depends(require_admin),
):
    """Upload image de formation dans Supabase Storage"""
    ALLOWED_TYPES = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
    }

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Format non supporté. Utilisez jpg, png ou webp.",
        )

    contents = await file.read()
    if len(contents) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="Image trop volumineuse (max 5 Mo)")

    existing = supabase.table("formations").select("id").eq("id", str(formation_id)).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Formation introuvable")

    ext = ALLOWED_TYPES[file.content_type]
    path = f"formations/{formation_id}/cover.{ext}"

    supabase.storage.from_("formations").upload(path, contents, {
        "content-type": file.content_type,
        "upsert": "true",
    })

    public_url = supabase.storage.from_("formations").get_public_url(path)

    supabase.table("formations").update({"image_url": public_url}).eq(
        "id", str(formation_id)
    ).execute()

    return {"image_url": public_url}
