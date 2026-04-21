"""Routes Progression"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from supabase import Client
from app.database.connection import get_supabase
from app.schemas.schemas import ProgressCompleteRequest
from app.services.auth_service import get_current_user, verify_student_ownership

router = APIRouter()


@router.post("/lesson/complete")
async def mark_lesson_complete(
    data: ProgressCompleteRequest,
    supabase: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_user),
):
    """Marquer une leçon comme complétée"""
    student = supabase.table("students").select("id").eq("user_id", current_user["id"]).single().execute()
    if not student.data:
        raise HTTPException(status_code=403, detail="Aucun profil étudiant associé à cet utilisateur")

    student_id = student.data["id"]

    progress_data = {
        "student_id": str(student_id),
        "formation_id": str(data.formation_id),
        "lesson_id": str(data.lesson_id),
        "completed": data.completed,
        "last_accessed": "NOW()",
    }

    supabase.table("progress").upsert(
        progress_data, on_conflict="student_id,lesson_id"
    ).execute()

    # Recalculer la progression globale
    updated = await _recalculate_progress(
        supabase, str(student_id), str(data.formation_id)
    )

    return {"message": "Progression mise à jour", "pourcentage": updated}


async def _recalculate_progress(supabase: Client, student_id: str, formation_id: str) -> float:
    """Calcule le pourcentage de completion d'une formation (uniquement les leçons de cette formation)"""
    # Récupérer les IDs des modules publiés de cette formation
    modules = supabase.table("elearning_modules").select("id").eq(
        "formation_id", formation_id
    ).eq("is_published", True).execute()

    if not modules.data:
        return 0.0

    module_ids = [m["id"] for m in modules.data]

    # Total de leçons publiées dans ces modules uniquement
    total = supabase.table("lessons").select(
        "id", count="exact"
    ).eq("is_published", True).in_("module_id", module_ids).execute()

    if not total.count:
        return 0.0

    # Leçons complétées par cet étudiant pour cette formation
    completed = supabase.table("progress").select(
        "id", count="exact"
    ).eq("student_id", student_id).eq("formation_id", formation_id).eq(
        "completed", True
    ).execute()

    pourcentage = round((completed.count or 0) / total.count * 100, 1)

    # Mettre à jour pourcentage global sur tous les enregistrements de cette formation
    supabase.table("progress").update({
        "pourcentage_formation": pourcentage
    }).eq("student_id", student_id).eq("formation_id", formation_id).execute()

    return pourcentage


@router.get("/student/{student_id}/formation/{formation_id}")
async def get_formation_progress(
    student_id: UUID,
    formation_id: UUID,
    supabase: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_user),
):
    """Progression détaillée d'un étudiant pour une formation"""
    await verify_student_ownership(current_user, str(student_id), supabase)

    progress = supabase.table("progress").select("*").eq(
        "student_id", str(student_id)
    ).eq("formation_id", str(formation_id)).execute()

    completed_lessons = {p["lesson_id"] for p in (progress.data or []) if p["completed"]}

    modules = supabase.table("elearning_modules").select(
        "*, lessons(id, titre, ordre, type, duree_minutes)"
    ).eq("formation_id", str(formation_id)).eq("is_published", True).order("ordre").execute()

    modules_data = []
    total_lessons = 0
    completed_count = 0

    for module in (modules.data or []):
        lessons = module.get("lessons", [])
        total_lessons += len(lessons)
        module_completed = sum(1 for l in lessons if l["id"] in completed_lessons)
        completed_count += module_completed

        modules_data.append({
            "id": module["id"],
            "titre": module["titre"],
            "ordre": module["ordre"],
            "total_lessons": len(lessons),
            "completed_lessons": module_completed,
            "pourcentage": round(module_completed / len(lessons) * 100, 1) if lessons else 0,
            "lessons": [
                {**l, "completed": l["id"] in completed_lessons}
                for l in sorted(lessons, key=lambda x: x["ordre"])
            ]
        })

    global_pct = round(completed_count / total_lessons * 100, 1) if total_lessons > 0 else 0

    return {
        "formation_id": str(formation_id),
        "student_id": str(student_id),
        "pourcentage_formation": global_pct,
        "lessons_completed": completed_count,
        "lessons_total": total_lessons,
        "modules": modules_data,
    }
