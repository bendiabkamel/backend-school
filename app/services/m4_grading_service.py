"""Business service for M4 exams, marks, grading rules, and final marks."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.repositories.m4_grading_repository import M4GradingRepository
from app.services.exceptions import NotFoundError, PermissionDeniedError, ValidationError
from app.services.session_isolation_service import SessionIsolationService


class M4GradingService:
    def __init__(self, repository: M4GradingRepository):
        self.repository = repository

    # Exams
    def create_exam(self, payload: dict[str, Any], current_user: dict) -> dict[str, Any]:
        self._ensure_staff(current_user)
        session = self.repository.get_academic_session(payload["academic_session_id"])
        if not session:
            raise NotFoundError("Academic session not found")
        SessionIsolationService.ensure_session_not_locked(session)

        self._ensure_teacher_assignment_for_context(payload, current_user)

        payload = payload.copy()
        payload["created_by_user_id"] = current_user["id"]
        payload["updated_by_user_id"] = current_user["id"]
        return self.repository.create_exam(payload)

    def list_exams(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        return self.repository.list_exams(**filters)

    def update_exam(self, exam_id: UUID | str, payload: dict[str, Any], current_user: dict) -> dict[str, Any]:
        self._ensure_staff(current_user)
        exam = self.repository.get_exam(exam_id)
        if not exam:
            raise NotFoundError("Exam not found")

        session = self.repository.get_academic_session(exam["academic_session_id"])
        if not session:
            raise NotFoundError("Academic session not found")
        SessionIsolationService.ensure_session_not_locked(session)

        self._ensure_teacher_assignment_for_context(exam, current_user)

        if exam.get("is_locked") and payload.get("is_locked") is not False:
            raise ValidationError("Exam is frozen and cannot be updated")

        payload = payload.copy()
        payload["updated_by_user_id"] = current_user["id"]
        return self.repository.update_exam(exam_id, payload)

    def lock_exam(self, exam_id: UUID | str, current_user: dict) -> dict[str, Any]:
        self._ensure_staff(current_user)
        exam = self.repository.get_exam(exam_id)
        if not exam:
            raise NotFoundError("Exam not found")

        return self.repository.update_exam(
            exam_id,
            {
                "is_locked": True,
                "updated_by_user_id": current_user["id"],
            },
        )

    # Exam rules
    def upsert_exam_rule(self, payload: dict[str, Any], current_user: dict) -> dict[str, Any]:
        self._ensure_staff(current_user)
        exam = self.repository.get_exam(payload["school_exam_id"])
        if not exam:
            raise NotFoundError("Exam not found")

        if Decimal(str(payload["pass_marks"])) > Decimal(str(payload["total_marks"])):
            raise ValidationError("pass_marks must be less than or equal to total_marks")

        payload = payload.copy()
        existing = self.repository.get_exam_rule_by_exam(payload["school_exam_id"])
        if existing:
            payload["updated_by_user_id"] = current_user["id"]
            payload["created_by_user_id"] = existing.get("created_by_user_id")
        else:
            payload["created_by_user_id"] = current_user["id"]
            payload["updated_by_user_id"] = current_user["id"]

        return self.repository.upsert_exam_rule(payload)

    # Grading systems and rules
    def create_grading_system(self, payload: dict[str, Any], current_user: dict) -> dict[str, Any]:
        self._ensure_staff(current_user)
        if Decimal(str(payload["max_score"])) < Decimal(str(payload["min_score"])):
            raise ValidationError("max_score must be greater than or equal to min_score")

        session = self.repository.get_academic_session(payload["academic_session_id"])
        if not session:
            raise NotFoundError("Academic session not found")
        SessionIsolationService.ensure_session_not_locked(session)

        payload = payload.copy()
        payload["created_by_user_id"] = current_user["id"]
        payload["updated_by_user_id"] = current_user["id"]
        return self.repository.create_grading_system(payload)

    def create_grade_rules(self, grading_system_id: UUID | str, rules: list[dict[str, Any]], current_user: dict) -> list[dict[str, Any]]:
        self._ensure_staff(current_user)
        grading_system = self.repository.get_grading_system(grading_system_id)
        if not grading_system:
            raise NotFoundError("Grading system not found")

        if not rules:
            raise ValidationError("At least one grade rule is required")

        normalized: list[dict[str, Any]] = []
        for row in rules:
            if str(row["grading_system_id"]) != str(grading_system_id):
                raise ValidationError("All rules must belong to the provided grading system")
            if Decimal(str(row["min_score"])) > Decimal(str(row["max_score"])):
                raise ValidationError("Each grade rule requires min_score <= max_score")
            normalized.append(
                {
                    **row,
                    "created_by_user_id": current_user["id"],
                    "updated_by_user_id": current_user["id"],
                }
            )

        sorted_rules = sorted(normalized, key=lambda x: (Decimal(str(x["min_score"])), Decimal(str(x["max_score"]))))
        previous_max: Decimal | None = None
        for row in sorted_rules:
            current_min = Decimal(str(row["min_score"]))
            current_max = Decimal(str(row["max_score"]))
            if previous_max is not None and current_min <= previous_max:
                raise ValidationError("Grade rule ranges overlap or touch")
            previous_max = current_max

        return self.repository.create_grade_rules(normalized)

    # Marks
    def upsert_marks(self, payload: dict[str, Any], current_user: dict) -> list[dict[str, Any]]:
        self._ensure_staff(current_user)

        exam = self.repository.get_exam(payload["school_exam_id"])
        if not exam:
            raise NotFoundError("Exam not found")

        if not exam.get("is_published"):
            raise ValidationError("Cannot submit marks for an unpublished exam")
        if exam.get("is_locked"):
            raise ValidationError("Exam is frozen and cannot accept new marks")

        session = self.repository.get_academic_session(exam["academic_session_id"])
        if not session:
            raise NotFoundError("Academic session not found")
        SessionIsolationService.ensure_session_not_locked(session)

        settings = self.repository.get_session_settings(exam["academic_session_id"]) or self.repository.get_global_settings()
        if settings and settings.get("marks_submission_status") != "on":
            raise ValidationError("Marks submission is currently locked by academic settings")

        self._ensure_teacher_assignment_for_context(exam, current_user)

        entries = payload["entries"]
        enrollment_ids = [str(item["enrollment_id"]) for item in entries]
        enrollment_map = {
            str(row["id"]): row
            for row in self.repository.list_enrollments(
                academic_session_id=exam["academic_session_id"],
                semester_id=exam["semester_id"],
                class_id=exam["class_id"],
                section_id=exam["section_id"],
                status=None,
            )
        }

        max_marks = Decimal(str(exam["max_marks"]))
        to_upsert = []
        for item in entries:
            enrollment_id = str(item["enrollment_id"])
            if enrollment_id not in enrollment_map:
                raise ValidationError(f"Enrollment {enrollment_id} is outside exam context")

            marks_obtained = Decimal(str(item["marks_obtained"]))
            if marks_obtained > max_marks:
                raise ValidationError("marks_obtained cannot exceed exam max_marks")

            if item.get("is_absent") and marks_obtained != Decimal("0"):
                raise ValidationError("marks_obtained must be 0 when is_absent is true")

            to_upsert.append(
                {
                    "enrollment_id": enrollment_id,
                    "owner_user_id": str(item["owner_user_id"]),
                    "school_exam_id": str(payload["school_exam_id"]),
                    "exam_rule_id": str(payload["exam_rule_id"]) if payload.get("exam_rule_id") else None,
                    "marks_obtained": str(marks_obtained),
                    "is_absent": bool(item.get("is_absent", False)),
                    "is_excused": bool(item.get("is_excused", False)),
                    "remarks": item.get("remarks"),
                    "entered_by_user_id": current_user["id"],
                    "updated_at": self.repository.now_iso(),
                }
            )

        return self.repository.upsert_marks(to_upsert)

    def compute_final_marks(self, payload: dict[str, Any], current_user: dict) -> list[dict[str, Any]]:
        self._ensure_staff(current_user)

        session = self.repository.get_academic_session(payload["academic_session_id"])
        if not session:
            raise NotFoundError("Academic session not found")
        SessionIsolationService.ensure_session_not_locked(session)

        settings = self.repository.get_session_settings(payload["academic_session_id"]) or self.repository.get_global_settings()
        if settings and settings.get("marks_submission_status") != "on":
            raise ValidationError("Final mark computation is locked by academic settings")

        grading_system = self.repository.get_grading_system(payload["grading_system_id"])
        if not grading_system:
            raise NotFoundError("Grading system not found")

        grade_rules = self.repository.list_grade_rules(payload["grading_system_id"])
        if not grade_rules:
            raise ValidationError("No grade rules configured for grading system")

        exams = self.repository.list_exams_by_context(
            academic_session_id=payload["academic_session_id"],
            semester_id=payload["semester_id"],
            class_id=payload["class_id"],
            section_id=payload["section_id"],
            course_id=payload["course_id"],
        )
        exams = [exam for exam in exams if exam.get("is_published")]
        if not exams:
            raise ValidationError("No published exams available for final mark computation")

        exam_map = {str(exam["id"]): exam for exam in exams}
        marks = self.repository.list_marks_by_context(
            academic_session_id=payload["academic_session_id"],
            semester_id=payload["semester_id"],
            class_id=payload["class_id"],
            section_id=payload["section_id"],
            course_id=payload["course_id"],
        )
        marks_by_enrollment: dict[str, list[dict[str, Any]]] = {}
        for row in marks:
            if str(row.get("school_exam_id")) not in exam_map:
                continue
            marks_by_enrollment.setdefault(str(row["enrollment_id"]), []).append(row)

        enrollments = self.repository.list_enrollments(
            academic_session_id=payload["academic_session_id"],
            semester_id=payload["semester_id"],
            class_id=payload["class_id"],
            section_id=payload["section_id"],
            status="active",
        )

        output_payloads = []
        for enrollment in enrollments:
            enrollment_id = str(enrollment["id"])
            enrollment_marks = marks_by_enrollment.get(enrollment_id, [])

            weighted_score = Decimal("0")
            snapshot_items: list[dict[str, Any]] = []
            for mark in enrollment_marks:
                exam = exam_map[str(mark["school_exam_id"])]
                max_marks = Decimal(str(exam["max_marks"]))
                weight = Decimal(str(exam["weight_percent"]))
                obtained = Decimal(str(mark["marks_obtained"]))

                contribution = Decimal("0")
                if max_marks > 0:
                    contribution = (obtained / max_marks) * weight
                weighted_score += contribution

                snapshot_items.append(
                    {
                        "school_exam_id": str(exam["id"]),
                        "exam_name": exam["exam_name"],
                        "weight_percent": str(weight),
                        "marks_obtained": str(obtained),
                        "max_marks": str(max_marks),
                        "contribution": str(contribution.quantize(Decimal("0.01"))),
                        "is_absent": bool(mark.get("is_absent", False)),
                    }
                )

            weighted_score = weighted_score.quantize(Decimal("0.01"))
            selected_rule = self._select_grade_rule(weighted_score, grade_rules)

            output_payloads.append(
                {
                    "enrollment_id": enrollment_id,
                    "owner_user_id": str(enrollment["owner_user_id"]),
                    "academic_session_id": str(payload["academic_session_id"]),
                    "semester_id": str(payload["semester_id"]),
                    "course_id": str(payload["course_id"]),
                    "grading_system_id": str(payload["grading_system_id"]),
                    "grade_rule_id": str(selected_rule["id"]) if selected_rule else None,
                    "calculated_marks": str(weighted_score),
                    "final_marks": str(weighted_score),
                    "grade_label": selected_rule.get("grade_label") if selected_rule else None,
                    "grade_point": str(selected_rule["grade_point"]) if selected_rule else None,
                    "note": "auto-computed",
                    "grade_snapshot": {
                        "computed_at": datetime.now(timezone.utc).isoformat(),
                        "items": snapshot_items,
                    },
                    "updated_at": self.repository.now_iso(),
                }
            )

        return self.repository.upsert_final_marks(output_payloads)

    def finalize_final_mark(self, final_mark_id: UUID | str, current_user: dict) -> dict[str, Any]:
        self._ensure_staff(current_user)
        final_mark = self.repository.get_final_mark(final_mark_id)
        if not final_mark:
            raise NotFoundError("Final mark not found")

        session = self.repository.get_academic_session(final_mark["academic_session_id"])
        if not session:
            raise NotFoundError("Academic session not found")
        SessionIsolationService.ensure_session_not_locked(session)

        settings = self.repository.get_session_settings(final_mark["academic_session_id"]) or self.repository.get_global_settings()
        if settings and settings.get("marks_submission_status") != "on":
            raise ValidationError("Final mark submission is locked by academic settings")

        return self.repository.update_final_mark(
            final_mark_id,
            {
                "finalized_by_user_id": current_user["id"],
                "finalized_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": self.repository.now_iso(),
            },
        )

    def list_final_marks(self, academic_session_id: UUID | str, semester_id: UUID | str, course_id: UUID | str) -> list[dict[str, Any]]:
        return self.repository.list_final_marks(
            academic_session_id=academic_session_id,
            semester_id=semester_id,
            course_id=course_id,
        )

    @staticmethod
    def _select_grade_rule(score: Decimal, rules: list[dict[str, Any]]) -> dict[str, Any] | None:
        for rule in sorted(rules, key=lambda x: Decimal(str(x["min_score"]))):
            min_score = Decimal(str(rule["min_score"]))
            max_score = Decimal(str(rule["max_score"]))
            if min_score <= score <= max_score:
                return rule
        return None

    @staticmethod
    def _ensure_staff(current_user: dict) -> None:
        if current_user.get("role") not in {"admin", "formateur"}:
            raise PermissionDeniedError("Operation requires teacher or admin role")

    def _ensure_teacher_assignment_for_context(self, context: dict[str, Any], current_user: dict) -> None:
        if current_user.get("role") == "admin":
            return
        assignments = self.repository.list_teacher_assignments(
            teacher_id=current_user["id"],
            academic_session_id=context["academic_session_id"],
            semester_id=context["semester_id"],
            class_id=context["class_id"],
            section_id=context["section_id"],
            course_id=context["course_id"],
        )
        if not assignments:
            raise PermissionDeniedError("Teacher is not assigned to this academic exam context")
