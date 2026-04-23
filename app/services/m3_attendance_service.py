"""Business service for M3 attendance workflows."""

from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Any
from uuid import UUID

from app.repositories.m3_attendance_repository import M3AttendanceRepository
from app.services.exceptions import NotFoundError, PermissionDeniedError, ValidationError
from app.services.session_isolation_service import SessionIsolationService


class M3AttendanceService:
    def __init__(self, repository: M3AttendanceRepository):
        self.repository = repository

    def mark_bulk(self, payload: dict[str, Any], current_user: dict) -> dict[str, Any]:
        attendance_session_id = payload.get("attendance_session_id")
        attendance_session_payload = payload.get("attendance_session")

        if attendance_session_id:
            attendance_session = self.repository.get_attendance_session(attendance_session_id)
            if not attendance_session:
                raise NotFoundError("Attendance session not found")
        else:
            attendance_session = self.repository.find_attendance_session_by_context(
                academic_session_id=attendance_session_payload["academic_session_id"],
                semester_id=attendance_session_payload["semester_id"],
                class_id=attendance_session_payload["class_id"],
                section_id=attendance_session_payload["section_id"],
                course_id=attendance_session_payload.get("course_id"),
                attendance_date=attendance_session_payload["attendance_date"],
                slot_code=attendance_session_payload["slot_code"],
            )
            if not attendance_session:
                attendance_session = self.repository.create_attendance_session(
                    {
                        **attendance_session_payload,
                        "marked_by_user_id": current_user["id"],
                    }
                )

        session = self.repository.get_academic_session(attendance_session["academic_session_id"])
        if not session:
            raise NotFoundError("Academic session not found")
        SessionIsolationService.ensure_session_not_locked(session)

        settings = self.repository.get_session_settings(attendance_session["academic_session_id"]) or self.repository.get_global_settings()
        if settings and settings.get("attendance_mode") != attendance_session["attendance_mode"]:
            raise ValidationError("Attendance mode does not match academic settings")

        self._ensure_teacher_ownership(current_user=current_user, attendance_session=attendance_session)

        enrollment_ids = [str(item["enrollment_id"]) for item in payload["records"]]
        enrollments = self.repository.list_enrollments_by_ids(enrollment_ids)
        enrollments_by_id = {str(row["id"]): row for row in enrollments}

        missing = [eid for eid in enrollment_ids if eid not in enrollments_by_id]
        if missing:
            raise ValidationError(f"Enrollment IDs not found: {', '.join(missing)}")

        for item in payload["records"]:
            enrollment = enrollments_by_id[str(item["enrollment_id"])]
            if str(enrollment["academic_session_id"]) != str(attendance_session["academic_session_id"]):
                raise ValidationError("Enrollment does not belong to the attendance session academic session")
            if str(enrollment["semester_id"]) != str(attendance_session["semester_id"]):
                raise ValidationError("Enrollment does not belong to the attendance session semester")
            if str(enrollment["class_id"]) != str(attendance_session["class_id"]):
                raise ValidationError("Enrollment does not belong to the attendance session class")
            if str(enrollment["section_id"]) != str(attendance_session["section_id"]):
                raise ValidationError("Enrollment does not belong to the attendance session section")

        existing_records = self.repository.list_attendance_records(attendance_session["id"])
        existing_enrollment_ids = {str(row["enrollment_id"]) for row in existing_records}
        duplicates = [eid for eid in enrollment_ids if eid in existing_enrollment_ids]
        if duplicates and payload.get("prevent_duplicates", True):
            raise ValidationError(
                f"Duplicate attendance records detected for enrollment_ids: {', '.join(sorted(set(duplicates)))}"
            )

        records_payload = []
        for item in payload["records"]:
            records_payload.append(
                {
                    "attendance_session_id": attendance_session["id"],
                    "enrollment_id": str(item["enrollment_id"]),
                    "owner_user_id": str(item["owner_user_id"]),
                    "attendance_status": item["attendance_status"],
                    "remarks": item.get("remarks"),
                    "recorded_by_user_id": current_user["id"],
                }
            )

        if payload.get("prevent_duplicates", True):
            inserted = self.repository.create_attendance_records(records_payload)
        else:
            inserted = self.repository.upsert_attendance_records(records_payload)

        return {
            "attendance_session": attendance_session,
            "records": inserted,
            "count": len(inserted),
        }

    def get_student_attendance(
        self,
        owner_user_id: UUID | str,
        current_user: dict,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> dict[str, Any]:
        if current_user.get("role") == "student" and str(current_user["id"]) != str(owner_user_id):
            raise PermissionDeniedError("Students can only read their own attendance")

        records = self.repository.list_student_attendance(owner_user_id=owner_user_id, from_date=from_date, to_date=to_date)
        status_counter = Counter(str(item.get("attendance_status")) for item in records)
        total = len(records)
        present = status_counter.get("present", 0)
        rate = round((present / total) * 100, 2) if total else 0.0

        return {
            "records": records,
            "stats": {
                "total": total,
                "status_counts": dict(status_counter),
                "present_rate": rate,
            },
        }

    def report(
        self,
        current_user: dict,
        academic_session_id: UUID | str,
        semester_id: UUID | str | None = None,
        class_id: UUID | str | None = None,
        section_id: UUID | str | None = None,
        course_id: UUID | str | None = None,
        attendance_date: date | None = None,
    ) -> dict[str, Any]:
        if current_user.get("role") not in {"admin", "formateur"}:
            raise PermissionDeniedError("Only staff can access attendance reports")

        records = self.repository.list_attendance_by_filters(
            academic_session_id=academic_session_id,
            semester_id=semester_id,
            class_id=class_id,
            section_id=section_id,
            course_id=course_id,
            attendance_date=attendance_date,
        )

        status_counter = Counter(str(item.get("attendance_status")) for item in records)
        grouped_by_session: dict[str, int] = {}
        for item in records:
            key = str(item.get("attendance_session_id"))
            grouped_by_session[key] = grouped_by_session.get(key, 0) + 1

        return {
            "records": records,
            "summary": {
                "total_records": len(records),
                "status_counts": dict(status_counter),
                "records_per_attendance_session": grouped_by_session,
            },
        }

    def _ensure_teacher_ownership(self, current_user: dict, attendance_session: dict[str, Any]) -> None:
        role = current_user.get("role")
        if role == "admin":
            return
        if role != "formateur":
            raise PermissionDeniedError("Only teachers or admins can mark attendance")

        assignments = self.repository.list_teacher_assignments(
            teacher_id=current_user["id"],
            academic_session_id=attendance_session["academic_session_id"],
            semester_id=attendance_session["semester_id"],
            class_id=attendance_session["class_id"],
            section_id=attendance_session["section_id"],
            course_id=attendance_session.get("course_id"),
        )
        if not assignments:
            raise PermissionDeniedError("Teacher is not assigned to this attendance context")
