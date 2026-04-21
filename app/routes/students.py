"""
Routes Étudiants
"""
import csv
import io
import random
from secrets import token_urlsafe
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from supabase import Client
from app.database.connection import get_supabase
from app.schemas.schemas import CreateStudentDirectRequest, StudentStatusUpdate
from app.services.auth_service import get_current_user, require_admin, verify_student_ownership

import logging

logger = logging.getLogger("albassir_api.students")

router = APIRouter()


@router.post("/create-direct")
async def create_student_direct(
    data: CreateStudentDirectRequest,
    supabase: Client = Depends(get_supabase),
    _: dict = Depends(require_admin),
):
    """Créer un étudiant directement depuis l'interface admin"""
    # 1. Vérifier que l'email n'existe pas déjà
    existing = supabase.table("users").select("id").eq("email", data.email).execute()
    if existing.data:
        raise HTTPException(status_code=409, detail="Un compte avec cet email existe déjà")

    # 2. Créer le compte Auth Supabase
    password = token_urlsafe(12)
    try:
        auth_response = supabase.auth.admin.create_user({
            "email": data.email,
            "email_confirm": True,
            "password": password,
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur création compte Auth: {e}")

    auth_user_id = auth_response.user.id

    # 3. Créer / mettre à jour le profil users (role = student)
    try:
        supabase.table("users").upsert({
            "id": auth_user_id,
            "email": data.email,
            "full_name": f"{data.prenom} {data.nom}",
            "role": "student",
        }).execute()
    except Exception as e:
        try:
            supabase.auth.admin.delete_user(auth_user_id)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Erreur création profil utilisateur: {e}")

    # 4. Générer un numéro étudiant unique (ABP-XXXXX)
    numero = ""
    for _ in range(10):
        candidate = f"ABP-{random.randint(10000, 99999)}"
        check = supabase.table("students").select("id").eq("numero_etudiant", candidate).execute()
        if not check.data:
            numero = candidate
            break
    if not numero:
        numero = f"ABP-{random.randint(100000, 999999)}"

    # Créer le profil students
    student_payload: dict = {
        "user_id": auth_user_id,
        "nom": data.nom,
        "prenom": data.prenom,
        "email": data.email,
        "telephone": data.telephone,
        "numero_etudiant": numero,
        "statut": "Actif",
    }
    if data.wilaya:
        student_payload["wilaya"] = data.wilaya
    if data.niveau_etudes:
        student_payload["niveau_etudes"] = data.niveau_etudes

    try:
        student_result = supabase.table("students").insert(student_payload).execute()
    except Exception as e:
        try:
            supabase.auth.admin.delete_user(auth_user_id)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Erreur création étudiant: {e}")

    student = student_result.data[0]

    # 5. Si formation_id fourni, créer une inscription avec statut = 'Validé'
    if data.formation_id:
        try:
            supabase.table("inscriptions").insert({
                "student_id": student["id"],
                "formation_id": str(data.formation_id),
                "statut": "Validé",
                "nom": data.nom,
                "prenom": data.prenom,
                "email": data.email,
                "telephone": data.telephone,
            }).execute()
        except Exception as e:
            logger.warning(f"Inscription formation échouée pour étudiant {student['id']}: {e}")

    # 6. Déclencher l'email de définition de mot de passe via recovery link
    email_sent = False
    try:
        supabase.auth.admin.generate_link({
            "type": "recovery",
            "email": data.email,
        })
        email_sent = True
    except Exception as e:
        logger.warning(f"Email de recovery non envoyé pour {data.email}: {e}")

    logger.info(f"Étudiant créé directement: {student['id']} ({data.email}) — email_sent={email_sent}")

    return {
        "student": student,
        "numero_etudiant": numero,
        "email_sent": email_sent,
    }


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
    await verify_student_ownership(current_user, str(student_id), supabase)
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
    await verify_student_ownership(current_user, str(student_id), supabase)

    inscriptions = supabase.table("inscriptions").select(
        "*, formations(*, categories(name, color))"
    ).eq("student_id", str(student_id)).eq("statut", "Validé").execute()

    return inscriptions.data or []
