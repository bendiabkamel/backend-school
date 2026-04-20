"""Routes Présence"""
from uuid import UUID
from fastapi import APIRouter, Depends
from supabase import Client
from app.database.connection import get_supabase
from app.schemas.schemas import AttendanceBulkCreate
from app.services.auth_service import get_current_user, require_formateur_or_admin

router = APIRouter()


@router.post("/bulk")
async def mark_attendance_bulk(
    data: AttendanceBulkCreate,
    supabase: Client = Depends(get_supabase),
    current_user: dict = Depends(require_formateur_or_admin),
):
    """Marquer la présence/absence pour une séance entière"""
    records = []
    for record in data.records:
        records.append({
            "student_id": record["student_id"],
            "session_id": str(data.session_id),
            "date_seance": str(data.date_seance),
            "statut": record.get("statut", "Absent"),
            "marked_by": current_user["id"],
        })

    result = supabase.table("attendance").upsert(
        records,
        on_conflict="student_id,session_id,date_seance"
    ).execute()

    return {"message": f"{len(records)} présences enregistrées", "data": result.data}


@router.get("/student/{student_id}")
async def get_student_attendance(
    student_id: UUID,
    supabase: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_user),
):
    """Historique présence d'un étudiant"""
    result = supabase.table("attendance").select(
        "*, sessions(date_debut, formations(titre))"
    ).eq("student_id", str(student_id)).order("date_seance", desc=True).execute()

    data = result.data or []
    total = len(data)
    presents = sum(1 for r in data if r["statut"] == "Présent")
    taux = round(presents / total * 100, 1) if total > 0 else 0

    return {
        "records": data,
        "stats": {"total": total, "presents": presents, "taux_presence": taux}
    }
