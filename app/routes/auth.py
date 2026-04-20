"""
Routes Authentification — Supabase Auth
"""
import os
from typing import Optional
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, HTTPException, Request
from supabase import Client

from app.database.connection import get_supabase
from app.schemas.schemas import LoginRequest, RegisterRequest, TokenResponse, CreateAdminRequest
from app.services.auth_service import get_current_user
from app.services.password_reset_service import send_password_recovery_email
from app.core.limiter import limiter

import logging
logger = logging.getLogger("albassir_api.auth")

router = APIRouter()

DEFAULT_FRONTEND_URL = "https://frontend-school-alpha.vercel.app"
LOCAL_HOSTNAMES = {"localhost", "127.0.0.1", "0.0.0.0"}


def _get_frontend_url(request: Optional[Request] = None) -> str:
    configured_url = os.getenv("FRONTEND_URL", "").strip()
    if configured_url:
        normalized_url = configured_url.rstrip("/")
        parsed = urlparse(normalized_url)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            is_production = os.getenv("ENVIRONMENT", "").strip().lower() == "production"
            if is_production and parsed.hostname in LOCAL_HOSTNAMES:
                logger.warning(
                    "FRONTEND_URL points to a local host in production (%s). Falling back to default URL.",
                    normalized_url,
                )
            else:
                return normalized_url
        else:
            logger.warning("FRONTEND_URL is invalid (%s). Falling back to default URL.", configured_url)

    return DEFAULT_FRONTEND_URL

@router.post("/register")
@limiter.limit("5/minute")
async def register(
    request: Request,
    data: RegisterRequest,
    supabase: Client = Depends(get_supabase),
):
    """Inscription d'un nouvel utilisateur (Désactivée)"""
    raise HTTPException(
        status_code=403, 
        detail="Règle 1: L'inscription libre est désactivée. Un étudiant doit soumettre une demande d'inscription et attendre l'approbation d'un administrateur."
    )


@router.post("/login")
@limiter.limit("10/minute")
async def login(
    request: Request,
    data: LoginRequest,
    supabase: Client = Depends(get_supabase),
):
    """Connexion utilisateur"""
    try:
        # Créer un client local pour ne pas polluer l'instance globale (service_role)
        from supabase import create_client
        local_supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY", os.getenv("SUPABASE_SERVICE_ROLE_KEY")))
        
        response = local_supabase.auth.sign_in_with_password({
            "email": data.email,
            "password": data.password,
        })

        if not getattr(response, "user", None):
            logger.warning(f"Tentative de connexion échouée (anonymisé). IP: {request.client.host}")
            raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")

        # Récupérer ou créer le profil utilisateur avec l'instance globale (qui a les droits bypass RLS pour insérer)
        try:
            profile_result = supabase.table("users").select("*").eq(
                "id", response.user.id
            ).single().execute()
            profile = profile_result.data
        except Exception:
            profile = None

        admin_email = os.getenv("ADMIN_EMAIL", "")
        # Vérification globale de l'email d'administration
        is_global_admin = (admin_email and response.user.email == admin_email)
        
        # Si le profil n'existe pas, le créer
        if not profile:
            role = "admin" if is_global_admin else "student"
            try:
                insert_result = supabase.table("users").insert({
                    "id": response.user.id,
                    "email": response.user.email,
                    "full_name": response.user.user_metadata.get("full_name", "") if response.user.user_metadata else "",
                    "role": role,
                }).execute()
                profile = insert_result.data[0] if insert_result.data else {}
            except Exception:
                profile = {}
        else:
            # Si le profil existe mais que c'est le super-admin, s'assurer que son rôle est bien admin
            if is_global_admin and profile.get("role") != "admin":
                supabase.table("users").update({"role": "admin"}).eq("id", response.user.id).execute()
                profile["role"] = "admin"

        logger.info(f"Connexion réussie pour l'utilisateur: {response.user.id}")

        return {
            "access_token": response.session.access_token,
            "token_type": "bearer",
            "user": {
                "id": response.user.id,
                "email": response.user.email,
                "full_name": profile.get("full_name", "") if profile else "",
                "role": "admin" if is_global_admin else profile.get("role", "student"),
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail="Identifiants invalides")


@router.post("/create-admin")
async def create_admin(
    data: CreateAdminRequest,
    supabase: Client = Depends(get_supabase),
):
    """
    Crée un compte administrateur dans Supabase Auth + table users.
    Protégé par ADMIN_SETUP_SECRET défini dans le fichier .env.
    À utiliser UNE SEULE FOIS pour chaque nouvel admin (ou via le dashboard Supabase).
    """
    setup_secret = os.getenv("ADMIN_SETUP_SECRET", "")
    if not setup_secret or data.setup_secret != setup_secret:
        raise HTTPException(status_code=403, detail="Secret invalide ou non configuré")

    try:
        # Créer l'utilisateur dans Supabase Auth (auth.users)
        user_id = None
        try:
            auth_response = supabase.auth.admin.create_user({
                "email": data.email,
                "password": data.password,
                "email_confirm": True,
                "user_metadata": {"full_name": data.full_name},
            })
            if auth_response.user:
                user_id = auth_response.user.id
        except Exception as auth_err:
            error_msg = str(auth_err)
            # Si l'utilisateur existe déjà (doublon ou ghost), récupérer son ID
            if "already" in error_msg.lower() or "duplicate" in error_msg.lower() or "23505" in error_msg or "database error" in error_msg.lower():
                users_list = supabase.auth.admin.list_users()
                for u in (users_list or []):
                    if getattr(u, "email", None) == data.email:
                        user_id = u.id
                        break
                if not user_id:
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            f"L'email {data.email} est bloqué par un compte fantôme (soft-deleted) dans Supabase Auth. "
                            "Allez dans le dashboard Supabase > SQL Editor et exécutez : "
                            f"DELETE FROM auth.users WHERE email = '{data.email}' AND deleted_at IS NOT NULL; "
                            "Puis réessayez."
                        ),
                    )
            else:
                raise HTTPException(status_code=400, detail=f"Erreur création auth: {error_msg}")

        if not user_id:
            raise HTTPException(status_code=400, detail="Échec de création dans Supabase Auth")

        # Créer ou mettre à jour le profil dans la table users avec rôle admin
        try:
            existing = supabase.table("users").select("id").eq("id", user_id).execute()
            if existing.data:
                # Mettre à jour le rôle en admin si le profil existe déjà
                supabase.table("users").update({
                    "role": "admin",
                    "full_name": data.full_name,
                }).eq("id", user_id).execute()
            else:
                supabase.table("users").insert({
                    "id": user_id,
                    "email": data.email,
                    "full_name": data.full_name,
                    "role": "admin",
                }).execute()
        except Exception as profile_err:
            print(f"[create-admin] Erreur profil users: {profile_err}")

        return {
            "message": "Administrateur créé avec succès. Vous pouvez maintenant vous connecter.",
            "user_id": user_id,
            "email": data.email,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/logout")
async def logout():
    """Déconnexion purement locale au frontend (le JWT Supabase expire de lui-même)"""
    return {"message": "Déconnexion réussie"}


@router.get("/me")
@limiter.limit("60/minute")
async def get_me(
    request: Request,
    supabase: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_user),
):
    """Retourne le profil de l'utilisateur connecté"""
    try:
        profile = supabase.table("users").select("*").eq(
            "id", current_user["id"]
        ).single().execute()
        return {
            "auth": current_user,
            "profile": profile.data,
        }
    except Exception as e:
        return {
            "auth": current_user,
            "profile": None,
            "error": str(e)
        }


@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    email: str,
    supabase: Client = Depends(get_supabase),
):
    """Demande de réinitialisation de mot de passe"""
    redirect_to = f"{_get_frontend_url(request)}/update-password"
    logger.info(f"URL de redirection reset-password: {redirect_to}")
    send_password_recovery_email(email, redirect_to)
    return {"message": "Email de réinitialisation envoyé"}
