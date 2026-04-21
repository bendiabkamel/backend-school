"""
Schémas Pydantic — Validation des données
"""
from datetime import datetime, date
from typing import Optional, List, Literal
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, validator


# ─── AUTH ────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=2, max_length=200)


class CreateAdminRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=2, max_length=200)
    setup_secret: str  # Doit correspondre à ADMIN_SETUP_SECRET dans .env


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


# ─── CATÉGORIES ──────────────────────────────────────────────

class CategoryBase(BaseModel):
    name: str = Field(max_length=100)
    description: Optional[str] = None
    color: Optional[str] = "#1e3a5f"
    icon: Optional[str] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryResponse(CategoryBase):
    id: UUID
    slug: str
    created_at: datetime

    class Config:
        from_attributes = True


# ─── FORMATIONS ──────────────────────────────────────────────

class FormationBase(BaseModel):
    titre: str = Field(max_length=300)
    description: Optional[str] = None
    description_courte: Optional[str] = Field(None, max_length=500)
    duree_heures: Optional[int] = None
    duree_label: Optional[str] = None
    prix: Optional[float] = None
    niveau: Optional[str] = "Débutant"
    categorie_id: Optional[UUID] = None
    formateur_id: Optional[UUID] = None
    is_published: bool = False
    is_elearning: bool = False


class FormationCreate(FormationBase):
    pass


class FormationUpdate(FormationBase):
    pass


class FormationResponse(FormationBase):
    id: UUID
    slug: str
    image_url: Optional[str] = None
    nb_modules: int = 0
    created_at: datetime
    updated_at: datetime
    categorie: Optional[CategoryResponse] = None

    class Config:
        from_attributes = True


# ─── SESSIONS ────────────────────────────────────────────────

class SessionBase(BaseModel):
    formation_id: UUID
    date_debut: date
    date_fin: date
    heure_debut: Optional[str] = None
    heure_fin: Optional[str] = None
    lieu: Optional[str] = None
    nb_places: int = 20
    statut: str = "Planifiée"


class SessionCreate(SessionBase):
    pass


class SessionResponse(SessionBase):
    id: UUID
    nb_inscrits: int
    created_at: datetime

    class Config:
        from_attributes = True


# ─── INSCRIPTIONS ────────────────────────────────────────────

class InscriptionCreate(BaseModel):
    nom: str = Field(max_length=100)
    prenom: str = Field(max_length=100)
    email: EmailStr
    telephone: str = Field(max_length=20)
    formation_id: UUID
    session_id: Optional[UUID] = None

    @validator("telephone")
    def validate_phone(cls, v):
        cleaned = v.replace(" ", "").replace("-", "").replace("+", "")
        if not cleaned.isdigit() or len(cleaned) < 9:
            raise ValueError("Numéro de téléphone invalide")
        return v


class InscriptionStatusUpdate(BaseModel):
    statut: str = Field(pattern="^(En attente|Validé|Refusé)$")
    notes_admin: Optional[str] = None

class StudentStatusUpdate(BaseModel):
    statut: str = Field(pattern="^(Actif|Inactif|Suspendu)$")


class InscriptionResponse(BaseModel):
    id: UUID
    nom: Optional[str]
    prenom: Optional[str]
    email: Optional[str]
    telephone: Optional[str]
    formation_id: UUID
    statut: str
    photo_url: Optional[str]
    date_inscription: datetime
    created_at: datetime

    class Config:
        from_attributes = True


# ─── ÉTUDIANTS ───────────────────────────────────────────────

class StudentResponse(BaseModel):
    id: UUID
    nom: str
    prenom: str
    email: str
    telephone: Optional[str]
    wilaya: Optional[str]
    niveau_etudes: Optional[str]
    photo_url: Optional[str]
    numero_etudiant: Optional[str]
    statut: str
    created_at: datetime

    class Config:
        from_attributes = True


# ─── PRÉSENCE ────────────────────────────────────────────────

class AttendanceCreate(BaseModel):
    student_id: UUID
    session_id: UUID
    date_seance: date
    statut: str = Field(pattern="^(Présent|Absent|Retard|Excusé)$")
    notes: Optional[str] = None


class AttendanceRecord(BaseModel):
    student_id: UUID
    session_id: Optional[UUID] = None
    date_seance: Optional[date] = None
    statut: str = Field(default="Absent", pattern="^(Présent|Absent|Retard|Excusé)$")


class AttendanceBulkCreate(BaseModel):
    session_id: Optional[UUID] = None
    date_seance: Optional[date] = None
    records: List[AttendanceRecord]


# ─── E-LEARNING ──────────────────────────────────────────────

class ModuleBase(BaseModel):
    formation_id: UUID
    titre: str = Field(max_length=300)
    description: Optional[str] = None
    ordre: int = 1
    duree_minutes: Optional[int] = None
    is_published: bool = False


class ModuleCreate(ModuleBase):
    pass


class ModuleResponse(ModuleBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class LessonBase(BaseModel):
    module_id: UUID
    titre: str = Field(max_length=300)
    description: Optional[str] = None
    contenu_texte: Optional[str] = None
    type: str = "texte"
    ordre: int = 1
    duree_minutes: Optional[int] = None
    is_published: bool = False


class LessonCreate(LessonBase):
    pass


class LessonResponse(LessonBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# ─── QUIZ ────────────────────────────────────────────────────

class AnswerBase(BaseModel):
    texte: str
    is_correct: bool = False
    ordre: int = 1


class QuestionBase(BaseModel):
    texte: str
    type: str = "qcm"
    points: int = 1
    ordre: int = 1
    explication: Optional[str] = None
    answers: List[AnswerBase] = []


class QuizCreate(BaseModel):
    module_id: UUID
    titre: str = Field(max_length=300)
    description: Optional[str] = None
    duree_minutes: int = 30
    score_passage: int = 60
    nb_tentatives_max: int = 3
    questions: List[QuestionBase] = []


class QuizSubmission(BaseModel):
    quiz_id: UUID
    reponses: dict  # {question_id: answer_id}


class QuizResultResponse(BaseModel):
    score: float
    score_max: float
    pourcentage: float
    reussi: bool
    details: List[dict]


# ─── PROGRESSION ─────────────────────────────────────────────

class ProgressCompleteRequest(BaseModel):
    formation_id: UUID
    lesson_id: UUID
    completed: bool = True


class ProgressResponse(BaseModel):
    formation_id: UUID
    pourcentage_formation: float
    modules: List[dict]
    lessons_completed: int
    lessons_total: int


# ─── PAIEMENTS ──────────────────────────────────────────────

class PaiementCreate(BaseModel):
    student_id: UUID
    formation_id: UUID
    montant_verse: float = Field(gt=0)
    mode_paiement: Literal["especes", "virement", "cheque", "ccp"]
    reference_recu: Optional[str] = Field(default=None, max_length=100)
    notes: Optional[str] = None
    date_paiement: Optional[date] = None


class PaiementResponse(BaseModel):
    id: UUID
    student_id: UUID
    formation_id: UUID
    montant_du: float
    montant_verse: float
    mode_paiement: str
    reference_recu: Optional[str] = None
    notes: Optional[str] = None
    date_paiement: date
    created_by: Optional[UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PaiementSummaryResponse(BaseModel):
    total_encaisse_mois_courant: float
    total_en_attente: float
    taux_recouvrement: float
    nb_etudiants_solde: int
    nb_etudiants_impaye: int
