"""
Routes Inscriptions — Formulaire public + Gestion admin
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from pydantic import EmailStr
from supabase import Client

import logging
logger = logging.getLogger("albassir_api.inscriptions")

from app.database.connection import get_supabase
from app.schemas.schemas import InscriptionStatusUpdate
from app.services.auth_service import require_admin
from app.core.limiter import limiter


router = APIRouter()
MAX_IMAGE_SIZE = 5 * 1024 * 1024
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024


def _get_frontend_url(request: Optional[Request] = None) -> str:
    configured_url = os.getenv("FRONTEND_URL", "").strip()
    if configured_url:
        return configured_url.rstrip("/")

    if request:
        origin = request.headers.get("origin", "").strip()
        if origin:
            return origin.rstrip("/")

    return "https://frontend-school-alpha.vercel.app"


@router.post("")
@limiter.limit("5/minute")
async def create_inscription(
    request: Request,
    nom: str = Form(...),
    prenom: str = Form(...),
    email: str = Form(...),
    telephone: str = Form(...),
    formation_id: str = Form(...),
    session_id: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    carte_nationale: Optional[UploadFile] = File(None),
    supabase: Client = Depends(get_supabase),
):
    """Formulaire d'inscription public avec upload documents"""

    # Vérifier que la formation existe
    formation = supabase.table("formations").select("id, titre").eq(
        "id", formation_id
    ).eq("is_published", True).single().execute()

    if not formation.data:
        raise HTTPException(status_code=404, detail="Formation introuvable")

    # Vérifier doublon inscription
    existing = supabase.table("inscriptions").select("id").eq(
        "email", email
    ).eq("formation_id", formation_id).eq("statut", "En attente").execute()

    if existing.data:
        raise HTTPException(
            status_code=409,
            detail="Une inscription en attente existe déjà pour cette formation avec cet email"
        )

    photo_url = None
    carte_url = None

    # Upload photo personnelle
    if photo and photo.filename:
        if not photo.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="La photo doit être une image")
        contents = await photo.read()
        if len(contents) > MAX_IMAGE_SIZE:
            raise HTTPException(status_code=400, detail="La photo dépasse la taille maximale de 5 Mo")
        path = f"inscriptions/{email}/photo_{photo.filename}"
        supabase.storage.from_("documents").upload(path, contents, {
    "content-type": photo.content_type,
    "upsert": "true"  # 
})
        photo_url = supabase.storage.from_("documents").get_public_url(path)

    # Upload carte nationale
    if carte_nationale and carte_nationale.filename:
        allowed = ["image/jpeg", "image/png", "application/pdf"]
        if carte_nationale.content_type not in allowed:
            raise HTTPException(status_code=400, detail="Format de carte nationale invalide")
        contents = await carte_nationale.read()
        if len(contents) > MAX_DOCUMENT_SIZE:
            raise HTTPException(status_code=400, detail="La carte nationale dépasse la taille maximale de 10 Mo")
        path = f"inscriptions/{email}/carte_{carte_nationale.filename}"
        supabase.storage.from_("documents").upload(path, contents, {
            "content-type": carte_nationale.content_type,
            "upsert": "true"
        })
        carte_url = supabase.storage.from_("documents").get_public_url(path)

    # Créer l'inscription
    inscription_data = {
        "nom": nom,
        "prenom": prenom,
        "email": email,
        "telephone": telephone,
        "formation_id": formation_id,
        "session_id": session_id,
        "photo_url": photo_url,
        "carte_nationale_url": carte_url,
        "statut": "En attente",
    }

    result = supabase.table("inscriptions").insert(inscription_data).execute()

    return {
        "message": "Inscription enregistrée avec succès. Vous serez contacté pour confirmation.",
        "inscription_id": result.data[0]["id"],
        "statut": "En attente",
    }


@router.get("")
async def list_inscriptions(
    statut: Optional[str] = None,
    formation_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    supabase: Client = Depends(get_supabase),
    _: dict = Depends(require_admin),
):
    """Liste de toutes les inscriptions (admin)"""
    query = supabase.table("inscriptions").select(
        "*, formations(titre, categorie_id)"
    )

    if statut:
        query = query.eq("statut", statut)
    if formation_id:
        query = query.eq("formation_id", formation_id)

    result = query.order("created_at", desc=True).range(skip, skip + limit - 1).execute()
    return result.data or []


@router.put("/{inscription_id}/status")
async def update_inscription_status(
    inscription_id: UUID,
    update: InscriptionStatusUpdate,
    request: Request,
    supabase: Client = Depends(get_supabase),
    current_user: dict = Depends(require_admin),
):
    """Valider ou refuser une inscription (admin)"""
    from datetime import datetime

    update_data = {
        "statut": update.statut,
        "notes_admin": update.notes_admin,
        "validated_by": current_user["id"],
    }

    if update.statut == "Validé":
        update_data["date_validation"] = datetime.utcnow().isoformat()
        # Créer automatiquement un compte étudiant si pas existant
        inscription = supabase.table("inscriptions").select("*").eq(
            "id", str(inscription_id)
        ).single().execute()

        account_info = None
        if inscription.data:
            account_info = await _create_student_from_inscription(
                supabase,
                inscription.data,
                _get_frontend_url(request),
            )

    result = supabase.table("inscriptions").update(update_data).eq(
        "id", str(inscription_id)
    ).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Inscription introuvable")

    logger.info(f"Inscription {inscription_id} passée à {update.statut} par admin {current_user['id']}")

    response = {"message": f"Statut mis à jour: {update.statut}", "data": result.data[0]}
    if update.statut == "Validé" and account_info:
        response["compte_etudiant"] = {
            "cree": account_info.get("account_created", False),
            "email": result.data[0].get("email"),
            "mot_de_passe_temporaire": account_info.get("temp_password"),
            "info": "Un email de réinitialisation du mot de passe a été envoyé à l'étudiant.",
        }
    return response


async def _create_student_from_inscription(supabase: Client, inscription: dict, frontend_url: str):
    """
    Crée automatiquement un compte auth + profil users + profil étudiant
    lors de la validation d'une inscription.
    Retourne un dict avec les infos du compte créé.
    """
    import os
    import secrets

    email = inscription["email"]
    nom = inscription.get("nom", "")
    prenom = inscription.get("prenom", "")
    full_name = f"{prenom} {nom}".strip()

    # Vérifier si étudiant existe déjà
    existing = supabase.table("students").select("id, user_id").eq(
        "email", email
    ).execute()
    if existing.data:
        return existing.data[0]

    # ── 1. Créer le compte Supabase Auth (auth.users) ─────────────────────
    # Mot de passe temporaire — l'étudiant devra le changer via le lien envoyé
    temp_password = secrets.token_urlsafe(12)
    user_id = None

    try:
        auth_response = supabase.auth.admin.create_user({
            "email": email,
            "password": temp_password,
            "email_confirm": True,          # Email confirmé immédiatement
            "user_metadata": {"full_name": full_name},
        })
        if auth_response.user:
            user_id = auth_response.user.id
    except Exception as auth_err:
        print(f"[inscription] ❌ ERREUR auth.admin.create_user: {auth_err}")  # 👈
        # L'utilisateur existe peut-être déjà dans auth.users
        # On essaie de retrouver son ID
        try:
            users_page = supabase.auth.admin.list_users()
            for u in (users_page or []):
                if getattr(u, "email", None) == email:
                    user_id = u.id
                    break
        except Exception:
            pass  # On continue sans user_id plutôt que de bloquer la validation

    # ── 2. Créer le profil dans la table users ────────────────────────────
    if user_id:
        try:
            # Vérifier si le profil existe déjà
            existing_profile = supabase.table("users").select("id").eq("id", user_id).execute()
            if not existing_profile.data:
                supabase.table("users").insert({
                    "id": user_id,
                    "email": email,
                    "full_name": full_name,
                    "role": "student",
                }).execute()
                print(f"[inscription] ✅ Profil users créé pour {email}")
            else:
                print(f"[inscription] ℹ️ Profil users déjà existant pour {email}")
        except Exception as e:
            print(f"[inscription] ⚠️ Erreur création profil users pour {email}: {e}")

    # ── 3. Générer numéro étudiant ────────────────────────────────────────
    count = supabase.table("students").select("id", count="exact").execute()
    numero = f"ABP-{str((count.count or 0) + 1).zfill(5)}"

    # ── 4. Créer le profil étudiant ───────────────────────────────────────
    student_data = {
        "nom": nom,
        "prenom": prenom,
        "email": email,
        "telephone": inscription.get("telephone"),
        "photo_url": inscription.get("photo_url"),
        "carte_nationale_url": inscription.get("carte_nationale_url"),
        "numero_etudiant": numero,
        "statut": "Actif",
    }
    if user_id:
        student_data["user_id"] = user_id

    result = supabase.table("students").insert(student_data).execute()
    print(f"[inscription] ✅ Profil étudiant créé : {numero}")

    # ── 5. Envoyer email de réinitialisation du mot de passe ─────────────
    # L'étudiant reçoit un lien pour définir son propre mot de passe
    try:
        supabase.auth.reset_password_email(
            email,
            options={"redirect_to": f"{frontend_url}/update-password"},
        )
        print(f"[inscription] 📧 Email de réinitialisation envoyé à {email}")
    except Exception as e:
        print(f"[inscription] ⚠️ Erreur envoi email à {email}: {e}")
        print(f"[inscription] 🔑 IMPORTANT : Mot de passe temporaire pour {email} : {temp_password}")

    return {
        "student": result.data[0] if result.data else None,
        "user_id": user_id,
        "temp_password": temp_password,   # À transmettre à l'étudiant si l'email échoue
        "account_created": user_id is not None,
    }
