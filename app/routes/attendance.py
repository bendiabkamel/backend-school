"""Routes Présence"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
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
    if not data.records:
        raise HTTPException(status_code=400, detail="Aucun enregistrement de présence fourni")

    student_ids = [str(record.student_id) for record in data.records]
    existing_students = supabase.table("students").select("id").in_("id", student_ids).execute()
    existing_ids = {row["id"] for row in (existing_students.data or [])}

    missing_ids = [sid for sid in student_ids if sid not in existing_ids]
    if missing_ids:
        raise HTTPException(
            status_code=404,
            detail=f"Les student_id suivants n'existent pas: {', '.join(missing_ids)}",
        )

    records = []
    for record in data.records:
        session_id = record.session_id or data.session_id
        date_seance = record.date_seance or data.date_seance

        if not session_id or not date_seance:
            raise HTTPException(
                status_code=422,
                detail="Chaque enregistrement doit inclure session_id et date_seance",
            )

        records.append({
            "student_id": str(record.student_id),
            "session_id": str(session_id),
            "date_seance": str(date_seance),
            "statut": record.statut,
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
