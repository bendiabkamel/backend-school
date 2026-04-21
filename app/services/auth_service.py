"""
Authentification JWT + Supabase Auth
"""
import os

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from supabase import Client

from app.database.connection import get_supabase

SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

security = HTTPBearer()


def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase: Client = Depends(get_supabase),
) -> dict:
    """Vérifie le token JWT Supabase et retourne l'utilisateur"""
    token = credentials.credentials
    try:
        # Vérification avec Supabase Auth
        user_response = supabase.auth.get_user(token)
        if not user_response.user:
            raise HTTPException(status_code=401, detail="Non authentifié")

        # Récupérer le profil complet
        profile_data = None
        try:
            profile = supabase.table("users").select("*").eq(
                "id", user_response.user.id
            ).single().execute()
            profile_data = profile.data
        except Exception as profile_err:
            print(f"[AUTH PROFILE ERROR] {profile_err}")
            profile_data = None

        role = profile_data.get("role", "student") if profile_data else "student"

        # 🚀 Forcer le rôle "admin" si c'est l'email d'administration global
        admin_email = os.getenv("ADMIN_EMAIL", "").strip()
        user_email = user_response.user.email.strip() if user_response.user.email else ""
        
        print(f"[AUTH DEBUG] Email utilisateur: '{user_email}', Email admin: '{admin_email}', match: {user_email == admin_email}")
        
        if admin_email and user_email == admin_email:
            role = "admin"

        # Vérification du statut étudiant (Règle 3: Chaque requête vérifie l'accès)
        if role == "student":
            try:
                student_resp = supabase.table("students").select("statut").eq(
                    "user_id", user_response.user.id
                ).execute()
                
                if not student_resp.data or student_resp.data[0].get("statut") != "Actif":
                    raise HTTPException(status_code=401, detail="Compte étudiant inactif, révoqué ou introuvable.")
            except HTTPException:
                raise
            except Exception as stu_err:
                print(f"[AUTH STUDENT ERROR] {stu_err}")
                raise HTTPException(status_code=401, detail="Impossible de vérifier le statut étudiant.")

        return {
            "id": user_response.user.id,
            "email": user_response.user.email,
            "role": role,
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[AUTH GLOB ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=401, detail=f"Erreur technique: {str(e)}")


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Dépendance: nécessite le rôle admin"""
    if current_user.get("role") not in ("admin",):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs",
        )
    return current_user


async def require_formateur_or_admin(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Dépendance: formateur ou admin"""
    if current_user.get("role") not in ("admin", "formateur"):
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    return current_user


async def verify_student_ownership(current_user, student_id: str, supabase: Client) -> bool:
    """Vérifie que current_user est soit admin/formateur, soit l'étudiant lui-même."""
    role = current_user.get("role") if isinstance(current_user, dict) else getattr(current_user, "role", None)
    user_id = current_user.get("id") if isinstance(current_user, dict) else getattr(current_user, "id", None)

    if role in ("admin", "formateur"):
        return True

    if not user_id:
        raise HTTPException(status_code=403, detail="Accès non autorisé")

    student = supabase.table("students").select("id").eq("user_id", user_id).single().execute()
    if not student.data or student.data["id"] != student_id:
        raise HTTPException(status_code=403, detail="Accès non autorisé")

    return True
