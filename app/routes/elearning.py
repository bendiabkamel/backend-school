"""
Routes E-Learning — Modules, Leçons, Vidéos, Documents
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from supabase import Client

from app.database.connection import get_supabase
from app.schemas.schemas import ModuleCreate, LessonCreate
from app.services.auth_service import get_current_user, require_admin, require_formateur_or_admin

router = APIRouter()
MAX_VIDEO_SIZE = 250 * 1024 * 1024
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024


# ─── MODULES ─────────────────────────────────────────────────

@router.get("/formations/{formation_id}/modules")
async def get_modules(
    formation_id: UUID,
    supabase: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_user),
):
    """Liste des modules d'une formation"""
    is_admin = current_user.get("role") in ("admin", "formateur")

    query = supabase.table("elearning_modules").select(
        "*, lessons(id, titre, type, duree_minutes, ordre, is_published)"
    ).eq("formation_id", str(formation_id))

    if not is_admin:
        query = query.eq("is_published", True)

    result = query.order("ordre").execute()
    return result.data or []


@router.post("/modules")
async def create_module(
    module: ModuleCreate,
    supabase: Client = Depends(get_supabase),
    _: dict = Depends(require_formateur_or_admin),
):
    """Créer un module e-learning"""
    data = module.model_dump()
    data["formation_id"] = str(data["formation_id"])

    result = supabase.table("elearning_modules").insert(data).execute()

    # Mettre à jour le compteur de modules
    modules_count = supabase.table("elearning_modules").select(
        "id", count="exact"
    ).eq("formation_id", str(module.formation_id)).execute()

    supabase.table("formations").update({
        "nb_modules": modules_count.count or 0
    }).eq("id", str(module.formation_id)).execute()

    return result.data[0]


@router.put("/modules/{module_id}")
async def update_module(
    module_id: UUID,
    data: dict,
    supabase: Client = Depends(get_supabase),
    _: dict = Depends(require_formateur_or_admin),
):
    result = supabase.table("elearning_modules").update(data).eq(
        "id", str(module_id)
    ).execute()
    return result.data[0]


@router.delete("/modules/{module_id}")
async def delete_module(
    module_id: UUID,
    supabase: Client = Depends(get_supabase),
    _: dict = Depends(require_admin),
):
    result = supabase.table("elearning_modules").delete().eq("id", str(module_id)).execute()
    return {"message": "Module supprimé"}


# ─── LEÇONS ──────────────────────────────────────────────────

@router.get("/modules/{module_id}/lessons")
async def get_lessons(
    module_id: UUID,
    supabase: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_user),
):
    """Liste des leçons d'un module"""
    query = supabase.table("lessons").select(
        "*, videos(*), documents(*)"
    ).eq("module_id", str(module_id))

    if current_user.get("role") not in ("admin", "formateur"):
        query = query.eq("is_published", True)

    result = query.order("ordre").execute()
    return result.data or []


@router.post("/lessons")
async def create_lesson(
    lesson: LessonCreate,
    supabase: Client = Depends(get_supabase),
    _: dict = Depends(require_formateur_or_admin),
):
    data = lesson.model_dump()
    data["module_id"] = str(data["module_id"])
    result = supabase.table("lessons").insert(data).execute()
    return result.data[0]


@router.get("/lessons/{lesson_id}")
async def get_lesson(
    lesson_id: UUID,
    supabase: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_user),
):
    """Récupère une leçon avec ses vidéos, documents et module parent"""
    result = supabase.table("lessons").select(
        "*, videos(*), documents(*), elearning_modules(id, titre, formation_id)"
    ).eq("id", str(lesson_id)).single().execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Leçon introuvable")

    lesson = result.data
    if not lesson.get("is_published") and current_user.get("role") not in ("admin", "formateur"):
        raise HTTPException(status_code=403, detail="Leçon non publiée")

    return lesson


@router.post("/lessons/{lesson_id}/video")
async def upload_video(
    lesson_id: UUID,
    titre: str = Form(...),
    file: UploadFile = File(...),
    supabase: Client = Depends(get_supabase),
    _: dict = Depends(require_formateur_or_admin),
):
    """Upload vidéo de cours dans Supabase Storage"""
    allowed = ["video/mp4", "video/webm", "video/ogg"]
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="Format vidéo non supporté (mp4, webm, ogg)")

    contents = await file.read()
    if len(contents) > MAX_VIDEO_SIZE:
        raise HTTPException(status_code=400, detail="Vidéo trop volumineuse (max 250 Mo)")
    path = f"videos/{lesson_id}/{file.filename}"

    supabase.storage.from_("elearning").upload(path, contents, {
        "content-type": file.content_type
    })

    url = supabase.storage.from_("elearning").get_public_url(path)

    result = supabase.table("videos").insert({
        "lesson_id": str(lesson_id),
        "titre": titre,
        "url": url,
        "storage_path": path,
    }).execute()

    return result.data[0]


@router.post("/lessons/{lesson_id}/document")
async def upload_document(
    lesson_id: UUID,
    titre: str = Form(...),
    file: UploadFile = File(...),
    supabase: Client = Depends(get_supabase),
    _: dict = Depends(require_formateur_or_admin),
):
    """Upload document PDF"""
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Seuls les fichiers PDF sont acceptés")

    contents = await file.read()
    if len(contents) > MAX_DOCUMENT_SIZE:
        raise HTTPException(status_code=400, detail="Document trop volumineux (max 10 Mo)")
    path = f"documents/{lesson_id}/{file.filename}"

    supabase.storage.from_("elearning").upload(path, contents, {
        "content-type": "application/pdf"
    })

    url = supabase.storage.from_("elearning").get_public_url(path)
    size_kb = len(contents) // 1024

    result = supabase.table("documents").insert({
        "lesson_id": str(lesson_id),
        "titre": titre,
        "url": url,
        "storage_path": path,
        "taille_kb": size_kb,
    }).execute()

    return result.data[0]
