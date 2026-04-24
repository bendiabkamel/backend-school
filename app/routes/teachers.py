"""Routes for school teachers (users with role 'formateur')."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from supabase import Client

from app.database.connection import get_supabase
from app.schemas.phase3 import TeacherCreate, TeacherUpdate
from app.services.auth_service import get_current_user, require_admin, require_formateur_or_admin

router = APIRouter()


@router.get("")
async def list_teachers(
    search: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    supabase: Client = Depends(get_supabase),
    _: dict = Depends(require_formateur_or_admin),
):
    """List all teachers (users with role formateur)."""
    query = supabase.table("users").select("*").eq("role", "formateur")

    if search:
        query = query.or_(
            f"full_name.ilike.%{search}%,email.ilike.%{search}%"
        )
    if is_active is not None:
        query = query.eq("is_active", is_active)

    result = query.order("full_name").execute()
    return result.data or []


@router.post("")
async def create_teacher(
    payload: TeacherCreate,
    supabase: Client = Depends(get_supabase),
    current_user: dict = Depends(require_admin),
):
    """Create a teacher account (admin only)."""
    existing = supabase.table("users").select("id").eq("email", payload.email).execute()
    if existing.data:
        raise HTTPException(status_code=409, detail="A user with this email already exists")

    try:
        auth_response = supabase.auth.admin.create_user(
            {
                "email": payload.email,
                "email_confirm": True,
                "password": __import__("secrets").token_urlsafe(16),
            }
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Auth creation error: {exc}")

    auth_user_id = auth_response.user.id

    profile = {
        "id": auth_user_id,
        "email": payload.email,
        "full_name": payload.full_name,
        "role": "formateur",
        "phone": payload.phone,
        "photo_url": payload.photo_url,
        "bio": payload.bio,
    }

    try:
        result = supabase.table("users").upsert(profile).execute()
    except Exception as exc:
        try:
            supabase.auth.admin.delete_user(auth_user_id)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Profile creation error: {exc}")

    # Send password recovery email so teacher can set their password
    try:
        supabase.auth.admin.generate_link({"type": "recovery", "email": payload.email})
    except Exception:
        pass

    return result.data[0]


@router.get("/{teacher_id}")
async def get_teacher(
    teacher_id: UUID,
    supabase: Client = Depends(get_supabase),
    _: dict = Depends(require_formateur_or_admin),
):
    """Get teacher profile by ID."""
    result = (
        supabase.table("users")
        .select("*")
        .eq("id", str(teacher_id))
        .eq("role", "formateur")
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Teacher not found")
    return result.data


@router.put("/{teacher_id}")
async def update_teacher(
    teacher_id: UUID,
    payload: TeacherUpdate,
    supabase: Client = Depends(get_supabase),
    current_user: dict = Depends(require_formateur_or_admin),
):
    """Update teacher profile (admin or the teacher themselves)."""
    # Allow teacher to update their own profile
    if current_user["role"] != "admin" and current_user["id"] != str(teacher_id):
        raise HTTPException(status_code=403, detail="You can only update your own profile")

    existing = (
        supabase.table("users")
        .select("id")
        .eq("id", str(teacher_id))
        .eq("role", "formateur")
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Teacher not found")

    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=422, detail="No fields to update")

    result = supabase.table("users").update(updates).eq("id", str(teacher_id)).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Teacher not found")
    return result.data[0]


@router.get("/{teacher_id}/assignments")
async def get_teacher_assignments(
    teacher_id: UUID,
    academic_session_id: UUID | None = Query(default=None),
    supabase: Client = Depends(get_supabase),
    _: dict = Depends(require_formateur_or_admin),
):
    """Get all course assignments for a teacher."""
    query = (
        supabase.table("teacher_assignments")
        .select("*, school_classes(*), sections(*), courses(*), semesters(*)")
        .eq("teacher_id", str(teacher_id))
    )
    if academic_session_id:
        query = query.eq("academic_session_id", str(academic_session_id))

    result = query.order("created_at", desc=True).execute()
    return result.data or []
