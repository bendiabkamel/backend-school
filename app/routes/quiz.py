"""
Routes Quiz — Création, soumission, correction automatique
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.database.connection import get_supabase
from app.schemas.schemas import QuizCreate, QuizSubmission
from app.services.auth_service import get_current_user, require_formateur_or_admin

router = APIRouter()


@router.get("/module/{module_id}")
async def get_quiz_by_module(
    module_id: UUID,
    supabase: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_user),
):
    """Récupére le quiz associé à un module (retourne null si aucun)"""
    result = supabase.table("quiz").select("id, titre, description, nb_tentatives_max, score_passage").eq(
        "module_id", str(module_id)
    ).limit(1).execute()
    return result.data[0] if result.data else None


@router.post("")
async def create_quiz(
    quiz: QuizCreate,
    supabase: Client = Depends(get_supabase),
    _: dict = Depends(require_formateur_or_admin),
):
    """Créer un quiz avec questions et réponses"""
    questions_data = quiz.questions
    quiz_dict = quiz.model_dump(exclude={"questions"})
    quiz_dict["module_id"] = str(quiz_dict["module_id"])

    # Créer le quiz
    quiz_result = supabase.table("quiz").insert(quiz_dict).execute()
    quiz_id = quiz_result.data[0]["id"]

    # Créer les questions et réponses
    for q in questions_data:
        answers = q.answers
        q_dict = q.model_dump(exclude={"answers"})
        q_dict["quiz_id"] = quiz_id

        q_result = supabase.table("questions").insert(q_dict).execute()
        question_id = q_result.data[0]["id"]

        for a in answers:
            supabase.table("answers").insert({
                **a.model_dump(),
                "question_id": question_id,
            }).execute()

    return {"quiz_id": quiz_id, "message": "Quiz créé avec succès"}


@router.get("/{quiz_id}")
async def get_quiz(
    quiz_id: UUID,
    supabase: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_user),
):
    """Récupérer un quiz (sans indiquer les bonnes réponses aux étudiants)"""
    quiz = supabase.table("quiz").select("*").eq("id", str(quiz_id)).single().execute()
    if not quiz.data:
        raise HTTPException(status_code=404, detail="Quiz introuvable")

    questions = supabase.table("questions").select("*, answers(*)").eq(
        "quiz_id", str(quiz_id)
    ).order("ordre").execute()

    is_admin = current_user.get("role") in ("admin", "formateur")

    # Pour les étudiants, ne pas envoyer is_correct
    questions_data = []
    for q in (questions.data or []):
        answers = []
        for a in q.get("answers", []):
            answer = {"id": a["id"], "texte": a["texte"], "ordre": a["ordre"]}
            if is_admin:
                answer["is_correct"] = a["is_correct"]
            answers.append(answer)
        questions_data.append({**q, "answers": answers})

    return {**quiz.data, "questions": questions_data}


@router.post("/{quiz_id}/submit")
async def submit_quiz(
    quiz_id: UUID,
    submission: QuizSubmission,
    supabase: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_user),
):
    """Soumettre un quiz — correction automatique"""
    # Récupérer le quiz
    quiz = supabase.table("quiz").select("*").eq("id", str(quiz_id)).single().execute()
    if not quiz.data:
        raise HTTPException(status_code=404, detail="Quiz introuvable")

    # Vérifier les tentatives
    student = supabase.table("students").select("id").eq(
        "email", current_user["email"]
    ).single().execute()

    if not student.data:
        raise HTTPException(status_code=404, detail="Profil étudiant introuvable")

    student_id = student.data["id"]

    existing_attempts = supabase.table("quiz_results").select("id").eq(
        "student_id", student_id
    ).eq("quiz_id", str(quiz_id)).execute()

    nb_attempts = len(existing_attempts.data or [])
    max_attempts = quiz.data.get("nb_tentatives_max", 3)

    if nb_attempts >= max_attempts:
        raise HTTPException(
            status_code=400,
            detail=f"Nombre maximum de tentatives atteint ({max_attempts})"
        )

    # Récupérer toutes les questions avec bonnes réponses
    questions = supabase.table("questions").select("*, answers(*)").eq(
        "quiz_id", str(quiz_id)
    ).execute()

    # Correction
    score = 0
    score_max = 0
    details = []

    for question in (questions.data or []):
        score_max += question["points"]
        user_answer_id = submission.reponses.get(question["id"])
        correct_answers = [a for a in question["answers"] if a["is_correct"]]
        correct_ids = [a["id"] for a in correct_answers]

        is_correct = user_answer_id in correct_ids if user_answer_id else False
        if is_correct:
            score += question["points"]

        details.append({
            "question_id": question["id"],
            "question": question["texte"],
            "user_answer": user_answer_id,
            "correct_answers": correct_ids,
            "is_correct": is_correct,
            "explication": question.get("explication"),
        })

    pourcentage = (score / score_max * 100) if score_max > 0 else 0
    reussi = pourcentage >= quiz.data.get("score_passage", 60)

    # Enregistrer le résultat
    from datetime import datetime
    result_data = {
        "student_id": student_id,
        "quiz_id": str(quiz_id),
        "score": score,
        "score_max": score_max,
        "pourcentage": round(pourcentage, 2),
        "reussi": reussi,
        "nb_tentative": nb_attempts + 1,
        "reponses": submission.reponses,
        "completed_at": datetime.utcnow().isoformat(),
    }

    supabase.table("quiz_results").insert(result_data).execute()

    return {
        "score": score,
        "score_max": score_max,
        "pourcentage": round(pourcentage, 2),
        "reussi": reussi,
        "details": details,
        "tentative": nb_attempts + 1,
    }
