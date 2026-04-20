"""Routes Examens"""
from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from supabase import Client
from app.database.connection import get_supabase
from app.services.auth_service import get_current_user, require_formateur_or_admin

router = APIRouter()


class ExamSubmission(BaseModel):
    reponses: dict  # {question_id: answer_id}


@router.post("")
async def create_exam(data: dict, supabase: Client = Depends(get_supabase),
                      _: dict = Depends(require_formateur_or_admin)):
    data["formation_id"] = str(data["formation_id"])
    result = supabase.table("exams").insert(data).execute()
    return result.data[0]


@router.get("/formation/{formation_id}")
async def get_exam(
    formation_id: UUID,
    supabase: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_user),
):
    """Récupère l'examen final d'une formation (sans révéler les bonnes réponses aux étudiants)"""
    result = supabase.table("exams").select("*, questions(*, answers(*))").eq(
        "formation_id", str(formation_id)).eq("is_published", True).execute()

    is_admin = current_user.get("role") in ("admin", "formateur")
    exams = result.data or []

    if not is_admin:
        # Masquer is_correct pour les étudiants
        for exam in exams:
            for question in exam.get("questions", []):
                for answer in question.get("answers", []):
                    answer.pop("is_correct", None)

    return exams


@router.post("/{exam_id}/submit")
async def submit_exam(
    exam_id: UUID,
    submission: ExamSubmission,
    supabase: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_user),
):
    """Soumettre un examen final avec correction automatique"""
    exam = supabase.table("exams").select("*").eq("id", str(exam_id)).single().execute()
    if not exam.data:
        raise HTTPException(status_code=404, detail="Examen introuvable")

    student = supabase.table("students").select("id").eq(
        "email", current_user["email"]).single().execute()
    if not student.data:
        raise HTTPException(status_code=404, detail="Profil étudiant introuvable")

    student_id = student.data["id"]

    # Récupérer toutes les questions avec les bonnes réponses
    questions = supabase.table("questions").select("*, answers(*)").eq(
        "quiz_id", str(exam_id)
    ).execute()

    # Si l'examen a ses propres questions (table questions liée via exam_id)
    # On tente avec exam_id directement
    if not questions.data:
        questions = supabase.table("questions").select("*, answers(*)").eq(
            "exam_id", str(exam_id)
        ).execute()

    # Correction automatique
    score = 0
    score_max = 0
    details = []

    for question in (questions.data or []):
        points = question.get("points", 1)
        score_max += points
        user_answer_id = submission.reponses.get(question["id"])
        correct_ids = [a["id"] for a in question.get("answers", []) if a.get("is_correct")]

        is_correct = user_answer_id in correct_ids if user_answer_id else False
        if is_correct:
            score += points

        details.append({
            "question_id": question["id"],
            "user_answer": user_answer_id,
            "correct_answers": correct_ids,
            "is_correct": is_correct,
        })

    score_max = score_max or 100
    pourcentage = round(score / score_max * 100, 2)
    reussi = pourcentage >= exam.data.get("score_passage", 60)

    result_data = {
        "student_id": student_id,
        "exam_id": str(exam_id),
        "score": score,
        "score_max": score_max,
        "pourcentage": pourcentage,
        "reussi": reussi,
        "completed_at": datetime.utcnow().isoformat(),
    }
    result = supabase.table("exam_results").insert(result_data).execute()

    return {
        **result.data[0],
        "details": details,
        "message": "Félicitations, examen réussi !" if reussi else "Examen non réussi. Vous pouvez réessayer.",
    }
