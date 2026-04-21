"""Routes Admin"""
from datetime import datetime, timezone
from typing import Any
import logging

from fastapi import APIRouter, Depends
from supabase import Client

from app.database.connection import get_supabase
from app.services.auth_service import require_admin

logger = logging.getLogger("albassir_api.admin")
router = APIRouter()


def _last_n_month_keys(n: int = 6) -> list[str]:
    """Return month keys like ['2025-11', ..., '2026-04'] for the last n months."""
    now = datetime.now(timezone.utc)
    year = now.year
    month = now.month
    keys: list[str] = []

    for _ in range(n):
        keys.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            month = 12
            year -= 1

    keys.reverse()
    return keys


def _aggregate_statuses(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counters: dict[str, int] = {}
    for row in rows:
        status = row.get("statut") or "Inconnu"
        counters[status] = counters.get(status, 0) + 1

    return [
        {"statut": status, "total": total}
        for status, total in sorted(counters.items(), key=lambda item: item[1], reverse=True)
    ]


@router.get("/stats")
async def get_admin_stats(
    supabase: Client = Depends(get_supabase),
    _: dict = Depends(require_admin),
):
    """Admin dashboard stats with safe fallbacks (never 500 for data fetch errors)."""
    total_etudiants = 0
    formations_actives = 0
    inscriptions_en_attente = 0
    taux_validation = 0.0
    inscriptions_par_mois: list[dict[str, Any]] = []
    inscriptions_recentes: list[dict[str, Any]] = []
    statuts_inscriptions: list[dict[str, Any]] = []

    total_inscriptions = 0
    inscriptions_validees = 0

    try:
        result = supabase.table("students").select("id", count="exact").limit(0).execute()
        total_etudiants = result.count or 0
    except Exception as exc:
        logger.warning("[admin/stats] students count failed: %s", exc)

    try:
        result = (
            supabase.table("formations")
            .select("id", count="exact")
            .eq("is_published", True)
            .limit(0)
            .execute()
        )
        formations_actives = result.count or 0
    except Exception as exc:
        logger.warning("[admin/stats] formations count failed: %s", exc)

    try:
        result = (
            supabase.table("inscriptions")
            .select("id", count="exact")
            .eq("statut", "En attente")
            .limit(0)
            .execute()
        )
        inscriptions_en_attente = result.count or 0
    except Exception as exc:
        logger.warning("[admin/stats] waiting inscriptions count failed: %s", exc)

    try:
        result = supabase.table("inscriptions").select("id", count="exact").limit(0).execute()
        total_inscriptions = result.count or 0
    except Exception as exc:
        logger.warning("[admin/stats] total inscriptions count failed: %s", exc)

    try:
        result = (
            supabase.table("inscriptions")
            .select("id", count="exact")
            .eq("statut", "Validé")
            .limit(0)
            .execute()
        )
        inscriptions_validees = result.count or 0
    except Exception as exc:
        logger.warning("[admin/stats] validated inscriptions count failed: %s", exc)

    if total_inscriptions > 0:
        taux_validation = round((inscriptions_validees / total_inscriptions) * 100, 2)

    try:
        month_keys = _last_n_month_keys(6)
        month_counts = {key: 0 for key in month_keys}
        first_month = month_keys[0]
        start_iso = f"{first_month}-01T00:00:00+00:00"

        rows = (
            supabase.table("inscriptions")
            .select("created_at")
            .gte("created_at", start_iso)
            .execute()
        ).data or []

        for row in rows:
            created_at = row.get("created_at")
            if isinstance(created_at, str) and len(created_at) >= 7:
                key = created_at[:7]
                if key in month_counts:
                    month_counts[key] += 1

        inscriptions_par_mois = [{"mois": key, "total": month_counts[key]} for key in month_keys]
    except Exception as exc:
        logger.warning("[admin/stats] monthly inscriptions failed: %s", exc)
        inscriptions_par_mois = []

    try:
        recent_rows = (
            supabase.table("inscriptions")
            .select(
                "id,student_id,formation_id,nom,prenom,email,telephone,statut,created_at,"
                "formations(titre),students(id,nom,prenom,email,numero_etudiant)"
            )
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        ).data or []
        inscriptions_recentes = recent_rows
    except Exception as exc:
        logger.warning("[admin/stats] recent inscriptions joined query failed: %s", exc)
        try:
            recent_rows = (
                supabase.table("inscriptions")
                .select(
                    "id,student_id,formation_id,nom,prenom,email,telephone,statut,created_at,"
                    "formations(titre)"
                )
                .order("created_at", desc=True)
                .limit(10)
                .execute()
            ).data or []

            student_ids = list({row.get("student_id") for row in recent_rows if row.get("student_id")})
            students_by_id: dict[str, dict[str, Any]] = {}

            if student_ids:
                try:
                    students = (
                        supabase.table("students")
                        .select("id,nom,prenom,email,numero_etudiant")
                        .in_("id", student_ids)
                        .execute()
                    ).data or []
                    students_by_id = {row["id"]: row for row in students if row.get("id")}
                except Exception as inner_exc:
                    logger.warning("[admin/stats] students fallback query failed: %s", inner_exc)

            for row in recent_rows:
                row["students"] = students_by_id.get(row.get("student_id"))

            inscriptions_recentes = recent_rows
        except Exception as inner_exc:
            logger.warning("[admin/stats] recent inscriptions fallback failed: %s", inner_exc)
            inscriptions_recentes = []

    try:
        status_rows = supabase.table("inscriptions").select("statut").execute().data or []
        statuts_inscriptions = _aggregate_statuses(status_rows)
    except Exception as exc:
        logger.warning("[admin/stats] statuses aggregation failed: %s", exc)
        statuts_inscriptions = []

    return {
        "total_etudiants": total_etudiants,
        "formations_actives": formations_actives,
        "inscriptions_en_attente": inscriptions_en_attente,
        "taux_validation": taux_validation,
        "inscriptions_par_mois": inscriptions_par_mois,
        "inscriptions_recentes": inscriptions_recentes,
        "statuts_inscriptions": statuts_inscriptions,
    }
