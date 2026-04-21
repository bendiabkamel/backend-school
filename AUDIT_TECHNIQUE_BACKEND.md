# Audit technique backend - AL BASSIR Pro

Date: 2026-04-20

## 0. Perimetre et methode

Perimetre analyse:
- Configuration runtime: `Procfile`, `render.yaml`, `.env.example`, `requirements.txt`
- Application FastAPI: `app/main.py`
- Couches core/db/services/schemas
- Toutes les routes sous `app/routes/`

Methode:
- Revue statique complete du code backend
- Cartographie de tous les endpoints exposes
- Analyse des flux fonctionnels de bout en bout
- Qualification des risques par criticite (Critique, Elevee, Moyenne, Faible)

Contexte architecture detecte:
- Backend FastAPI monolithique
- Data access principal via Supabase client (REST + Auth + Storage)
- SQLAlchemy async configure mais tres peu utilise dans les routes
- Controle d'acces base sur role (`admin`, `formateur`, `student`) via dependances FastAPI

## 1. Vue d'ensemble architecture

Composants majeurs:
- Entree API: `app/main.py`
- AuthN/AuthZ: `app/services/auth_service.py`, `app/routes/auth.py`
- Donnees et connexion: `app/database/connection.py`
- Validation de payloads: `app/schemas/schemas.py`
- Domaines metier:
- Formations/Categories/Sessions
- Inscriptions/Students
- E-learning (modules, lessons, medias)
- Quiz/Exams/Progress
- Attendance

Points forts techniques:
- Middleware de securite HTTP present (HSTS, X-Frame-Options, etc.)
- CORS configurable via env (`ALLOWED_ORIGINS`)
- Limitation de debit active sur endpoints sensibles (`/auth/login`, `/auth/register`, `/auth/reset-password`, `/inscriptions`)
- Validation d'URL de redirection pour reset password, avec blocage des hosts locaux en production
- Verification du statut etudiant actif au moment de l'authentification (regle metier explicite)

## 2. Cartographie des flux fonctionnels et fonctionnalites

### 2.1 Flux Authentification et autorisation

Fonctionnalites:
- `POST /auth/register`: volontairement desactive (inscription libre interdite)
- `POST /auth/login`: login Supabase, creation auto du profil `users` si absent
- `GET /auth/me`: retourne profil auth + profil metier `users`
- `POST /auth/logout`: logout logique (cote front)
- `POST /auth/create-admin`: bootstrap admin via secret setup
- `POST /auth/reset-password`: declenche email Supabase de recuperation

Flux:
1. Le client soumet email/mot de passe a `/auth/login`.
2. Auth reussie via Supabase Auth.
3. Le backend recupere ou cree la ligne dans `users`.
4. Le role est determine (`admin` force si email == `ADMIN_EMAIL`).
5. Si role `student`, verification du statut dans table `students`.
6. Retour du JWT et du profil simplifie.

### 2.2 Flux Inscriptions publiques -> activation etudiant

Fonctionnalites:
- `POST /inscriptions`: inscription publique avec upload photo/carte nationale
- `GET /inscriptions`: listing admin avec filtres
- `PUT /inscriptions/{inscription_id}/status`: validation/refus admin

Flux principal de validation:
1. Un candidat soumet le formulaire `POST /inscriptions`.
2. Le backend verifie existence formation publiee + doublon d'inscription en attente.
3. Les pieces jointes sont uploadees dans Supabase Storage bucket `documents`.
4. Une ligne `inscriptions` est creee au statut `En attente`.
5. Un admin valide via `PUT /inscriptions/{id}/status`.
6. Le backend cree (ou rattache) le compte Auth Supabase, cree profil `users`, cree profil `students`, genere un numero etudiant, puis envoie un reset password.

### 2.3 Flux catalogue formation

Fonctionnalites:
- `GET /formations`: catalogue public (filtres category/search/published)
- `GET /formations/{id}`: detail formation + modules publies + sessions a venir
- `POST /formations`: creation admin
- `PUT /formations/{id}`: edition admin
- `DELETE /formations/{id}`: suppression admin
- `POST /formations/{id}/image`: upload image dans bucket `formations`

### 2.4 Flux categories et sessions

Fonctionnalites categories:
- `GET /categories`: liste publique
- `POST /categories`: creation admin

Fonctionnalites sessions:
- `GET /sessions`: liste sessions (option filtrage formation)
- `POST /sessions`: creation admin
- `PUT /sessions/{id}`: mise a jour admin

### 2.5 Flux E-learning (modules, lessons, medias)

Fonctionnalites:
- `GET /elearning/formations/{formation_id}/modules`
- `POST /elearning/modules`
- `PUT /elearning/modules/{module_id}`
- `DELETE /elearning/modules/{module_id}`
- `GET /elearning/modules/{module_id}/lessons`
- `POST /elearning/lessons`
- `GET /elearning/lessons/{lesson_id}` (declare mais enregistrement defectueux, voir risques)
- `POST /elearning/lessons/{lesson_id}/video`
- `POST /elearning/lessons/{lesson_id}/document`

Flux:
1. Admin/formateur cree modules et lessons.
2. Uploads video/pdf dans bucket `elearning`.
3. Etudiant voit uniquement contenu `is_published=True`.

### 2.6 Flux Quiz

Fonctionnalites:
- `GET /quiz/module/{module_id}`
- `POST /quiz`
- `GET /quiz/{quiz_id}`
- `POST /quiz/{quiz_id}/submit`

Flux de soumission:
1. Recuperation quiz et questions/reponses.
2. Verification nb tentatives max pour l'etudiant.
3. Correction automatique.
4. Persistance du resultat dans `quiz_results`.
5. Retour score/detail/tentative.

### 2.7 Flux Examens finaux

Fonctionnalites:
- `POST /exams`
- `GET /exams/formation/{formation_id}`
- `POST /exams/{exam_id}/submit`

Flux:
1. Recuperation examen final de formation.
2. Soumission des reponses.
3. Correction automatique.
4. Persistance dans `exam_results`.

### 2.8 Flux Progression

Fonctionnalites:
- `POST /progress/lesson/complete`
- `GET /progress/student/{student_id}/formation/{formation_id}`

Flux:
1. Marquage lesson complete via upsert dans `progress`.
2. Recalcul du pourcentage formation.
3. Consultation progression detaillee par module/lesson.

### 2.9 Flux Attendance

Fonctionnalites:
- `POST /attendance/bulk`
- `GET /attendance/student/{student_id}`

Flux:
1. Formateur/admin envoie liste de presences d'une seance.
2. Upsert en masse sur cle composite `(student_id, session_id, date_seance)`.
3. Consultation historique et calcul taux de presence.

## 3. Inventaire des endpoints exposes

Endpoints globaux:
- `GET /`
- `GET /health`

Auth (`/auth`):
- `POST /register`
- `POST /login`
- `POST /create-admin`
- `POST /logout`
- `GET /me`
- `POST /reset-password`

Formations (`/formations`):
- `GET /`
- `GET /{formation_id}`
- `POST /`
- `PUT /{formation_id}`
- `DELETE /{formation_id}`
- `POST /{formation_id}/image`

Categories (`/categories`):
- `GET /`
- `POST /`

Sessions (`/sessions`):
- `GET /`
- `POST /`
- `PUT /{session_id}`

Inscriptions (`/inscriptions`):
- `POST /`
- `GET /`
- `PUT /{inscription_id}/status`

Students (`/students`):
- `PUT /{student_id}/status`
- `GET /`
- `GET /export/csv`
- `GET /{student_id}`
- `GET /{student_id}/formations`

Attendance (`/attendance`):
- `POST /bulk`
- `GET /student/{student_id}`

E-learning (`/elearning`):
- `GET /formations/{formation_id}/modules`
- `POST /modules`
- `PUT /modules/{module_id}`
- `DELETE /modules/{module_id}`
- `GET /modules/{module_id}/lessons`
- `POST /lessons`
- `GET /lessons/{lesson_id}` (declaration anormale dans une fonction)
- `POST /lessons/{lesson_id}/video`
- `POST /lessons/{lesson_id}/document`

Quiz (`/quiz`):
- `GET /module/{module_id}`
- `POST /`
- `GET /{quiz_id}`
- `POST /{quiz_id}/submit`

Exams (`/exams`):
- `POST /`
- `GET /formation/{formation_id}`
- `POST /{exam_id}/submit`

Progress (`/progress`):
- `POST /lesson/complete`
- `GET /student/{student_id}/formation/{formation_id}`

## 4. Constats techniques, risques et priorites

### 4.1 Critique

C1 - Endpoint e-learning mal enregistre (risque de route indisponible)
- Observation: `@router.get("/lessons/{lesson_id}")` est defini a l'interieur de `create_lesson`.
- Reference: `app/routes/elearning.py:108`, `app/routes/elearning.py:119`
- Impact: la route peut ne pas exister au demarrage et etre enregistree seulement apres un appel a `POST /elearning/lessons`.
- Risque metier: indisponibilite intermittente de la lecture detail d'une lesson.

C2 - Echec probable du bulk attendance (TypeError)
- Observation: boucle sur objets Pydantic puis acces indexe `record["student_id"]`.
- Reference: `app/routes/attendance.py:20`, `app/routes/attendance.py:22`
- Impact: crash runtime lors de marquage de presence.
- Risque metier: blocage de l'emargement.

C3 - Risque IDOR/autorisation sur donnees etudiant/progression
- Observation: certaines routes acceptent `student_id` en path/body sans verifier que l'utilisateur courant est proprietaire ou admin.
- Reference: `app/routes/students.py:92`, `app/routes/students.py:104`, `app/routes/progress.py:13`, `app/routes/progress.py:20`, `app/routes/progress.py:76`, `app/routes/progress.py:85`
- Impact: un etudiant authentifie pourrait lire/modifier des donnees d'un autre etudiant.
- Risque metier: fuite de donnees personnelles et corruption de progression.

### 4.2 Elevee

E1 - Exposition potentielle de documents personnels via URL publiques
- Observation: stockage photo/carte nationale avec `get_public_url`.
- Reference: `app/routes/inscriptions.py:95`, `app/routes/inscriptions.py:100`, `app/routes/inscriptions.py:110`, `app/routes/inscriptions.py:115`
- Impact: acces potentiellement public a des documents sensibles.
- Risque metier: non-conformite RGPD / atteinte a la confidentialite.

E2 - Bootstrap admin base uniquement sur secret partage
- Observation: `/auth/create-admin` non protege par authentification forte, uniquement `ADMIN_SETUP_SECRET`.
- Reference: `app/routes/auth.py:131`, `app/routes/auth.py:141`, `app/routes/auth.py:142`
- Impact: surface d'attaque si secret divulgue ou faible.
- Risque metier: elevation de privilege majeure.

E3 - Fuite de mot de passe temporaire
- Observation: mot de passe temporaire inclus dans reponse API et logs en cas d'echec email.
- Reference: `app/routes/inscriptions.py:208`, `app/routes/inscriptions.py:310`, `app/routes/inscriptions.py:315`
- Impact: exposition de credentiel.
- Risque metier: compromission de comptes etudiants.

### 4.3 Moyenne

M1 - Ambiguite de modele de donnees examens/questions
- Observation: correction examen cherche d'abord `questions.quiz_id = exam_id` puis fallback `questions.exam_id`.
- Reference: `app/routes/exams.py:69`, `app/routes/exams.py:76`
- Impact: correction potentiellement sur le mauvais jeu de questions.

M2 - Durcissement securite incomplet sur host policy
- Observation: `ALLOWED_HOSTS` default `*`.
- Reference: `app/main.py:75`
- Impact: protection host header faible par defaut.

M3 - Donnees techniques sensibles dans messages d'erreur auth
- Observation: details techniques renvoyes au client (`Erreur technique: ...`).
- Reference: `app/services/auth_service.py:91`
- Impact: fuite d'information utile a un attaquant.

M4 - Gestion des users Supabase possiblement incorrecte
- Observation: iteration directe sur retour `list_users()` sans passer par `users`/pagination selon SDK.
- Reference: `app/routes/auth.py:161`, `app/routes/auth.py:162`, `app/routes/inscriptions.py:254`, `app/routes/inscriptions.py:255`
- Impact: logique de recuperation d'utilisateur existant fragile.

M5 - Initialisation Supabase non defensive
- Observation: creation client globale sans validation de `SUPABASE_URL` et `SUPABASE_SERVICE_ROLE_KEY`.
- Reference: `app/database/connection.py:15`, `app/database/connection.py:17`
- Impact: crash au demarrage si env incomplet.

M6 - Defaults mutables dans schemas
- Observation: listes par defaut `[]` sur modeles Pydantic.
- Reference: `app/schemas/schemas.py:263`, `app/schemas/schemas.py:273`
- Impact: comportement partage non desire selon usage.

M7 - Horodatage `last_accessed` stocke comme chaine litterale
- Observation: valeur `"NOW()"` envoyee telle quelle.
- Reference: `app/routes/progress.py:24`
- Impact: champ date incoherent si DB ne l'interprete pas comme fonction.

### 4.4 Faible

F1 - Dette technique import/main
- Observation: imports dupliques dans `main.py`.
- Reference: `app/main.py:5`, `app/main.py:15`, `app/main.py:17`, `app/main.py:19`
- Impact: lisibilite et maintenance.

F2 - Artefact de scaffold atypique
- Observation: fichier residuel `app/{routes,models,schemas,services,database}/__init__.py`.
- Impact: confusion outillage et maintenance.

F3 - Couverture tests absente
- Observation: aucun test detecte.
- Impact: risque de regressions eleve lors des evolutions.

## 5. Plan de remediation recommande

Priorite P0 (immediat, 24-72h):
- Corriger la route `GET /elearning/lessons/{lesson_id}` en la sortant de `create_lesson`.
- Corriger `attendance/bulk` en acces attribut (`record.student_id`) ou `record.model_dump()`.
- Fermer les failles IDOR sur `students` et `progress` (controle ownership ou role admin/formateur).
- Retirer toute fuite de mot de passe temporaire des reponses/logs.
- Passer documents d'identite en acces prive (signed URLs temporaires).

Priorite P1 (1 semaine):
- Refactoriser `exams` pour un modele unique (`questions.exam_id` ou table dediee).
- Durcir `/auth/create-admin` (usage one-shot, whitelisting IP, rate limit, desactivation post-bootstrap).
- Standardiser gestion erreurs: pas de details techniques cote client.
- Valider env avant creation client Supabase et fail-fast explicite.

Priorite P2 (2-4 semaines):
- Ajouter tests automatises (unitaires + integration API).
- Ajouter observabilite (logs structures JSON, correlation-id, metriques latence/taux erreur).
- Nettoyer dette technique (`main.py`, fichier scaffold residuel, schemas Pydantic v2).

## 6. Recommandations d'architecture et qualite

Securite:
- Appliquer principe du moindre privilege pour toutes les routes liees a un `student_id`.
- Eviter toute URL publique pour documents sensibles.
- Supprimer les details techniques dans erreurs API.
- Verifier que `SUPABASE_SERVICE_ROLE_KEY` n'est jamais expose au frontend.

Robustesse:
- Definir contrats de schema stricts pour tous les `data: dict` en entree (`sessions`, `exams`, etc.).
- Harmoniser types UUID/string avant persist.
- Ajouter retries/timeouts et gestion d'erreur explicite pour appels Supabase critiques.

Performance:
- Revisiter requetes potentiellement N+1 dans les enrichissements (quiz/questions/answers).
- Ajouter pagination sur endpoints potentiellement volumineux.

Operabilite:
- Mettre en place tests smoke au demarrage (connectivite Supabase + buckets + auth admin API).
- Ajouter checklist de deploiement (env obligatoires, redirects, buckets, policies RLS).

## 7. Conclusion

Le backend couvre un spectre fonctionnel riche et coherent pour une plateforme de formation (catalogue, inscriptions, e-learning, quiz, examens, progression, presence), avec une base de securite deja presente (headers, role checks, rate limit).

Les risques les plus importants sont toutefois centraux et doivent etre traites en priorite: enregistrement defectueux d'une route e-learning, bug runtime attendance, controles d'acces incomplets sur donnees etudiants/progression, et gestion de documents/credentials sensibles.

Apres correction des points P0 et ajout d'une base de tests, la plateforme pourra monter significativement en fiabilite, securite et maintenabilite.