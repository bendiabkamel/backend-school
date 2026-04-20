"""
Routes Étudiants
"""
import csv
import io
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from supabase import Client
from app.database.connection import get_supabase
from app.schemas.schemas import StudentStatusUpdate
from app.services.auth_service import get_current_user, require_admin

import logging

logger = logging.getLogger("albassir_api.students")

router = APIRouter()


@router.put("/{student_id}/status")
async def update_student_status(
    student_id: UUID,
    update_data: StudentStatusUpdate,
    supabase: Client = Depends(get_supabase),
    current_user: dict = Depends(require_admin)
):
    """Mettre à jour le statut d'un étudiant (Actif, Suspendu, Inactif)"""
    result = supabase.table("students").update({"statut": update_data.statut}).eq(
        "id", str(student_id)
    ).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Étudiant introuvable")
    
    logger.info(f"Statut modifié par l'admin {current_user['id']} pour l'étudiant {student_id} -> {update_data.statut}")
    return {"message": "Statut mis à jour avec succès", "student": result.data[0]}


@router.get("")
async def list_students(
    search: Optional[str] = Query(None),
    statut: Optional[str] = Query(None),
    wilaya: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 50,
    supabase: Client = Depends(get_supabase),
    _: dict = Depends(require_admin),
):
    """Liste des étudiants avec recherche et filtres (admin)"""
    query = supabase.table("students").select("*")

    if search:
        query = query.or_(
            f"nom.ilike.%{search}%,prenom.ilike.%{search}%,email.ilike.%{search}%,numero_etudiant.ilike.%{search}%"
        )
    if statut:
        query = query.eq("statut", statut)
    if wilaya:
        query = query.eq("wilaya", wilaya)

    result = query.order("created_at", desc=True).range(skip, skip + limit - 1).execute()
    return result.data or []


@router.get("/export/csv")
async def export_students_csv(
    supabase: Client = Depends(get_supabase),
    _: dict = Depends(require_admin),
):
    """Export CSV de tous les étudiants"""
    result = supabase.table("students").select("*").order("nom").execute()

    output = io.StringIO()
    fieldnames = ["numero_etudiant", "nom", "prenom", "email", "telephone",
                  "wilaya", "niveau_etudes", "statut", "created_at"]

    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()

    for student in (result.data or []):
        writer.writerow(student)

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=etudiants.csv"}
    )


@router.get("/{student_id}")
async def get_student(
    student_id: UUID,
    supabase: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_user),
):
    result = supabase.table("students").select("*").eq("id", str(student_id)).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Étudiant introuvable")
    return result.data


@router.get("/{student_id}/formations")
async def get_student_formations(
    student_id: UUID,
    supabase: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_user),
):
    """Formations d'un étudiant avec progression"""
    inscriptions = supabase.table("inscriptions").select(
        "*, formations(*, categories(name, color))"
    ).eq("student_id", str(student_id)).eq("statut", "Validé").execute()

    return inscriptions.data or []
