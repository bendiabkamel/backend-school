"""Routes Paiements"""
import logging

logger = logging.getLogger("albassir_api.paiements")
import csv
import io
from calendar import monthrange
from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from supabase import Client

from app.database.connection import get_supabase
from app.schemas.schemas import PaiementCreate, PaiementSummaryResponse
from app.services.auth_service import (
    get_current_user,
    require_admin,
    require_formateur_or_admin,
    verify_student_ownership,
)

router = APIRouter()


def _to_float(value) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _compute_statut(total_verse: float, montant_du: float) -> str:
    if total_verse >= montant_du and montant_du > 0:
        return "solde"
    if total_verse == 0:
        return "impaye"
    return "partiel"


def _build_date_range(mois: Optional[int], annee: Optional[int]) -> tuple[Optional[str], Optional[str]]:
    if mois is None and annee is None:
        return None, None

    today = date.today()

    if annee is not None and annee < 1900:
        raise HTTPException(status_code=400, detail="annee invalide")

    if mois is not None and (mois < 1 or mois > 12):
        raise HTTPException(status_code=400, detail="mois invalide")

    if annee is not None and mois is None:
        start = date(annee, 1, 1)
        end = date(annee, 12, 31)
        return start.isoformat(), end.isoformat()

    target_month = mois if mois is not None else today.month
    target_year = annee if annee is not None else today.year
    start = date(target_year, target_month, 1)
    end = date(target_year, target_month, monthrange(target_year, target_month)[1])
    return start.isoformat(), end.isoformat()


def _aggregate_by_student_formation(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str], dict] = {}

    for row in rows:
        student_id = row.get("student_id")
        formation_id = row.get("formation_id")
        if not student_id or not formation_id:
            continue

        key = (student_id, formation_id)
        if key not in grouped:
            grouped[key] = {
                "student_id": student_id,
                "formation_id": formation_id,
                "montant_du": _to_float(row.get("montant_du")),
                "total_verse": 0.0,
                "solde_restant": 0.0,
                "statut": "impaye",
                "nb_versements": 0,
                "last_payment_date": row.get("date_paiement"),
                "student": row.get("students"),
                "formation": row.get("formations"),
            }

        current = grouped[key]
        current["total_verse"] += _to_float(row.get("montant_verse"))
        current["montant_du"] = max(current["montant_du"], _to_float(row.get("montant_du")))
        current["nb_versements"] += 1

        payment_date = row.get("date_paiement")
        if payment_date and (
            not current["last_payment_date"]
            or str(payment_date) > str(current["last_payment_date"])
        ):
            current["last_payment_date"] = payment_date

    items = list(grouped.values())
    for item in items:
        item["total_verse"] = round(item["total_verse"], 2)
        item["montant_du"] = round(item["montant_du"], 2)
        item["solde_restant"] = round(max(item["montant_du"] - item["total_verse"], 0.0), 2)
        item["statut"] = _compute_statut(item["total_verse"], item["montant_du"])

    items.sort(
        key=lambda x: (
            x.get("last_payment_date") is None,
            str(x.get("last_payment_date") or ""),
        ),
        reverse=True,
    )
    return items


def _fetch_payments_with_filters(
    supabase: Client,
    formation_id: Optional[UUID],
    mois: Optional[int],
    annee: Optional[int],
) -> list[dict]:
    try:
        query = supabase.table("paiements").select(
            "*, students(id, nom, prenom, email, numero_etudiant), formations(id, titre)"
        )

        if formation_id:
            query = query.eq("formation_id", str(formation_id))

        start_date, end_date = _build_date_range(mois, annee)
        if start_date and end_date:
            query = query.gte("date_paiement", start_date).lte("date_paiement", end_date)

        result = query.order("date_paiement", desc=True).execute()
        return result.data or []
    except Exception as e:
        print(f"[PAIEMENTS ERROR] {type(e).__name__}: {e}")
        logger.error(f"[PAIEMENTS ERROR] {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_paiement(
    data: PaiementCreate,
    supabase: Client = Depends(get_supabase),
    current_user: dict = Depends(require_formateur_or_admin),
):
    """Créer un paiement (admin/formateur)."""
    student = supabase.table("students").select("id").eq("id", str(data.student_id)).single().execute()
    if not student.data:
        raise HTTPException(status_code=404, detail="Etudiant introuvable")

    formation = supabase.table("formations").select("id, prix").eq(
        "id", str(data.formation_id)
    ).single().execute()
    if not formation.data:
        raise HTTPException(status_code=404, detail="Formation introuvable")

    montant_du = _to_float(formation.data.get("prix"))
    if montant_du <= 0:
        raise HTTPException(status_code=400, detail="Prix de formation invalide pour calculer le montant_du")

    payload = data.model_dump(exclude_none=True)
    payload.update(
        {
            "student_id": str(data.student_id),
            "formation_id": str(data.formation_id),
            "montant_du": round(montant_du, 2),
            "montant_verse": round(_to_float(data.montant_verse), 2),
            "date_paiement": str(data.date_paiement or date.today()),
            "created_by": current_user["id"],
        }
    )

    result = supabase.table("paiements").insert(payload).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Echec creation paiement")

    return result.data[0]


@router.get("")
async def list_paiements(
    statut: Optional[str] = Query(default=None),
    formation_id: Optional[UUID] = Query(default=None),
    mois: Optional[int] = Query(default=None, ge=1, le=12),
    annee: Optional[int] = Query(default=None, ge=1900),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    supabase: Client = Depends(get_supabase),
    _: dict = Depends(require_admin),
):
    """Liste paginee des paiements agreges par etudiant/formation (admin)."""
    if statut and statut not in {"solde", "partiel", "impaye"}:
        raise HTTPException(status_code=400, detail="statut invalide (solde|partiel|impaye)")

    try:
        rows = _fetch_payments_with_filters(supabase, formation_id, mois, annee)
    except HTTPException:
        raise
    except Exception as e:
        print(f"[PAIEMENTS ERROR] {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    aggregated = _aggregate_by_student_formation(rows)

    if statut:
        aggregated = [item for item in aggregated if item["statut"] == statut]

    total = len(aggregated)
    start = (page - 1) * limit
    end = start + limit

    return {
        "page": page,
        "limit": limit,
        "total": total,
        "data": aggregated[start:end],
    }


@router.get("/summary", response_model=PaiementSummaryResponse)
async def get_paiements_summary(
    supabase: Client = Depends(get_supabase),
    _: dict = Depends(require_admin),
):
    """Resume financier global des paiements (admin)."""
    rows = _fetch_payments_with_filters(supabase, None, None, None)
    aggregated = _aggregate_by_student_formation(rows)

    now = date.today()
    total_encaisse_mois_courant = 0.0
    for row in rows:
        payment_date = row.get("date_paiement")
        if not payment_date:
            continue
        try:
            paid_at = date.fromisoformat(str(payment_date))
        except ValueError:
            continue
        if paid_at.month == now.month and paid_at.year == now.year:
            total_encaisse_mois_courant += _to_float(row.get("montant_verse"))

    total_du = sum(item["montant_du"] for item in aggregated)
    total_verse = sum(item["total_verse"] for item in aggregated)
    total_en_attente = sum(item["solde_restant"] for item in aggregated)

    student_ids_solde = {item["student_id"] for item in aggregated if item["statut"] == "solde"}
    student_ids_impaye = {item["student_id"] for item in aggregated if item["statut"] == "impaye"}

    taux_recouvrement = round((total_verse / total_du) * 100, 2) if total_du > 0 else 0.0

    return {
        "total_encaisse_mois_courant": round(total_encaisse_mois_courant, 2),
        "total_en_attente": round(total_en_attente, 2),
        "taux_recouvrement": taux_recouvrement,
        "nb_etudiants_solde": len(student_ids_solde),
        "nb_etudiants_impaye": len(student_ids_impaye),
    }


@router.get("/etudiant/{student_id}")
async def get_student_paiements(
    student_id: UUID,
    supabase: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_user),
):
    """Historique complet des paiements d'un etudiant (admin ou proprietaire)."""
    await verify_student_ownership(current_user, str(student_id), supabase)

    result = supabase.table("paiements").select(
        "*, formations(id, titre, prix)"
    ).eq("student_id", str(student_id)).order("date_paiement", desc=True).execute()
    historique = result.data or []

    inscriptions = supabase.table("inscriptions").select(
        "formation_id, formations(prix, titre)"
    ).eq("student_id", str(student_id)).eq("statut", "Validé").execute()

    montant_du_total = 0.0
    seen_formations: set[str] = set()
    for row in (inscriptions.data or []):
        formation_id = row.get("formation_id")
        if not formation_id or formation_id in seen_formations:
            continue
        seen_formations.add(formation_id)
        formation_data = row.get("formations") or {}
        montant_du_total += _to_float(formation_data.get("prix"))

    total_verse = sum(_to_float(row.get("montant_verse")) for row in historique)

    return {
        "student_id": str(student_id),
        "historique": historique,
        "recapitulatif": {
            "montant_du_total": round(montant_du_total, 2),
            "total_verse": round(total_verse, 2),
            "solde_restant": round(max(montant_du_total - total_verse, 0.0), 2),
        },
    }


@router.get("/export/csv")
async def export_paiements_csv(
    statut: Optional[str] = Query(default=None),
    formation_id: Optional[UUID] = Query(default=None),
    mois: Optional[int] = Query(default=None, ge=1, le=12),
    annee: Optional[int] = Query(default=None, ge=1900),
    supabase: Client = Depends(get_supabase),
    _: dict = Depends(require_admin),
):
    """Export CSV des paiements avec filtres optionnels (admin)."""
    if statut and statut not in {"solde", "partiel", "impaye"}:
        raise HTTPException(status_code=400, detail="statut invalide (solde|partiel|impaye)")

    rows = _fetch_payments_with_filters(supabase, formation_id, mois, annee)
    aggregated = _aggregate_by_student_formation(rows)
    status_map = {(item["student_id"], item["formation_id"]): item["statut"] for item in aggregated}

    filtered_rows = rows
    if statut:
        filtered_rows = [
            row
            for row in rows
            if status_map.get((row.get("student_id"), row.get("formation_id"))) == statut
        ]

    output = io.StringIO()
    fieldnames = [
        "id",
        "date_paiement",
        "student_id",
        "student_nom",
        "student_prenom",
        "student_email",
        "formation_id",
        "formation_titre",
        "montant_du",
        "montant_verse",
        "mode_paiement",
        "reference_recu",
        "notes",
        "created_by",
        "statut",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for row in filtered_rows:
        student = row.get("students") or {}
        formation = row.get("formations") or {}
        row_statut = status_map.get((row.get("student_id"), row.get("formation_id")), "impaye")
        writer.writerow(
            {
                "id": row.get("id"),
                "date_paiement": row.get("date_paiement"),
                "student_id": row.get("student_id"),
                "student_nom": student.get("nom"),
                "student_prenom": student.get("prenom"),
                "student_email": student.get("email"),
                "formation_id": row.get("formation_id"),
                "formation_titre": formation.get("titre"),
                "montant_du": row.get("montant_du"),
                "montant_verse": row.get("montant_verse"),
                "mode_paiement": row.get("mode_paiement"),
                "reference_recu": row.get("reference_recu"),
                "notes": row.get("notes"),
                "created_by": row.get("created_by"),
                "statut": row_statut,
            }
        )

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=paiements.csv"},
    )