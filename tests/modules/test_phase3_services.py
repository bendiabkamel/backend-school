import unittest
from datetime import date, datetime, timezone
from decimal import Decimal

from app.services.exceptions import NotFoundError, PermissionDeniedError, ValidationError
from app.services.m1_sessions_service import M1SessionsService
from app.services.m2_structure_service import M2StructureService
from app.services.m3_attendance_service import M3AttendanceService
from app.services.m4_grading_service import M4GradingService
from app.services.m5_assignments_service import M5AssignmentsService
from app.services.m6_communications_service import M6CommunicationsService
from app.services.m7_promotions_service import M7PromotionsService


class _RepoBase:
    def now_iso(self):
        return datetime.now(timezone.utc).isoformat()


class M1Repo(_RepoBase):
    def __init__(self):
        self.sessions = []
        self.semesters = []
        self.settings = []

    def list_sessions(self, scope=None):
        return self.sessions

    def get_session(self, session_id):
        return next((row for row in self.sessions if row["id"] == str(session_id)), None)

    def get_current_session(self):
        return next((row for row in self.sessions if row.get("is_current")), None)

    def create_session(self, payload):
        row = {"id": payload.get("id", "s1"), **payload}
        self.sessions.append(row)
        return row

    def update_session(self, session_id, payload):
        row = self.get_session(session_id)
        if not row:
            raise ValueError("Academic session not found")
        row.update(payload)
        return row

    def unset_all_current_sessions(self):
        for row in self.sessions:
            row["is_current"] = False

    def set_current_session(self, session_id):
        row = self.get_session(session_id)
        if not row:
            raise ValueError("Academic session not found")
        row["is_current"] = True
        return row

    def list_semesters(self, academic_session_id=None):
        return [row for row in self.semesters if academic_session_id is None or row["academic_session_id"] == str(academic_session_id)]

    def get_semester(self, semester_id):
        return next((row for row in self.semesters if row["id"] == str(semester_id)), None)

    def create_semester(self, payload):
        row = {"id": payload.get("id", "sem1"), **payload}
        self.semesters.append(row)
        return row

    def update_semester(self, semester_id, payload):
        row = self.get_semester(semester_id)
        if not row:
            raise ValueError("Semester not found")
        row.update(payload)
        return row

    def get_settings(self, settings_scope, academic_session_id=None):
        for row in self.settings:
            if row["settings_scope"] == settings_scope and (settings_scope != "session" or row.get("academic_session_id") == str(academic_session_id)):
                return row
        return None

    def upsert_settings(self, payload):
        self.settings.append({"id": "set1", **payload})
        return self.settings[-1]


class M2Repo(_RepoBase):
    def __init__(self):
        self.classes = []
        self.sections = []
        self.courses = []
        self.enrollments = []
        self.teacher_assignments = []
        self.students = []
        self.sessions = []
        self.semesters = []

    def get_class(self, class_id):
        return next((row for row in self.classes if row["id"] == str(class_id)), None)

    def list_classes(self, academic_session_id=None):
        return self.classes

    def create_class(self, payload):
        row = {"id": payload.get("id", "class1"), **payload}
        self.classes.append(row)
        return row

    def update_class(self, class_id, payload):
        row = self.get_class(class_id)
        if not row:
            raise ValueError
        row.update(payload)
        return row

    def get_section(self, section_id):
        return next((row for row in self.sections if row["id"] == str(section_id)), None)

    def list_sections(self, academic_session_id=None, class_id=None):
        return self.sections

    def create_section(self, payload):
        row = {"id": payload.get("id", "sec1"), **payload}
        self.sections.append(row)
        return row

    def update_section(self, section_id, payload):
        row = self.get_section(section_id)
        if not row:
            raise ValueError
        row.update(payload)
        return row

    def get_course(self, course_id):
        return next((row for row in self.courses if row["id"] == str(course_id)), None)

    def list_courses(self, academic_session_id=None, semester_id=None, class_id=None):
        return self.courses

    def create_course(self, payload):
        row = {"id": payload.get("id", "course1"), **payload}
        self.courses.append(row)
        return row

    def update_course(self, course_id, payload):
        row = self.get_course(course_id)
        if not row:
            raise ValueError
        row.update(payload)
        return row

    def get_semester(self, semester_id):
        return next((row for row in self.semesters if row["id"] == str(semester_id)), None)

    def get_enrollment(self, enrollment_id):
        return next((row for row in self.enrollments if row["id"] == str(enrollment_id)), None)

    def list_enrollments(self, **filters):
        items = self.enrollments
        for key, value in filters.items():
            if value is None:
                continue
            items = [row for row in items if row.get(key) == (str(value) if isinstance(value, (str, int)) else value)]
        return items

    def create_enrollment(self, payload):
        row = {"id": payload.get("id", "enr1"), **payload}
        self.enrollments.append(row)
        return row

    def update_enrollment(self, enrollment_id, payload):
        row = self.get_enrollment(enrollment_id)
        if not row:
            raise ValueError
        row.update(payload)
        return row

    def list_teacher_assignments(self, **filters):
        return self.teacher_assignments

    def upsert_teacher_assignments(self, payloads):
        self.teacher_assignments.extend([{**row, "id": f"ta{idx}"} for idx, row in enumerate(payloads, start=1)])
        return self.teacher_assignments

    def list_courses_by_ids(self, course_ids):
        return [row for row in self.courses if row["id"] in course_ids]

    def list_students_by_user(self, user_id):
        return [{"id": "student-1", "user_id": str(user_id)}]


class M3Repo(_RepoBase):
    def __init__(self):
        self.session = {"id": "as1", "academic_session_id": "session-1", "semester_id": "sem-1", "class_id": "class-1", "section_id": "sec-1", "course_id": "course-1", "attendance_mode": "section"}
        self.enrollments = [{"id": "enr-1", "academic_session_id": "session-1", "semester_id": "sem-1", "class_id": "class-1", "section_id": "sec-1", "owner_user_id": "user-1"}]
        self.records = []

    def get_academic_session(self, academic_session_id):
        return {"id": academic_session_id, "status": "active"}

    def get_session_settings(self, academic_session_id):
        return {"attendance_mode": "section"}

    def get_global_settings(self):
        return None

    def list_teacher_assignments(self, **kwargs):
        return [{"id": "ta-1"}]

    def find_attendance_session_by_context(self, **kwargs):
        return self.session

    def create_attendance_session(self, payload):
        return self.session

    def get_attendance_session(self, attendance_session_id):
        return self.session

    def list_attendance_records(self, attendance_session_id):
        return self.records

    def create_attendance_records(self, records):
        self.records.extend([{**row, "id": f"ar-{idx}"} for idx, row in enumerate(records, start=1)])
        return self.records

    def upsert_attendance_records(self, records):
        return self.create_attendance_records(records)

    def list_enrollments_by_ids(self, enrollment_ids):
        return self.enrollments

    def list_student_attendance(self, owner_user_id, from_date=None, to_date=None):
        return [{"attendance_status": "present"}, {"attendance_status": "absent"}]

    def list_attendance_by_filters(self, **kwargs):
        return [{"attendance_status": "present", "attendance_session_id": "as1"}]


class M4Repo(_RepoBase):
    def __init__(self):
        self.exams = [{"id": "exam-1", "academic_session_id": "session-1", "semester_id": "sem-1", "class_id": "class-1", "section_id": "sec-1", "course_id": "course-1", "max_marks": 100, "weight_percent": 100, "is_published": True, "is_locked": False, "exam_name": "Midterm"}]
        self.grading_systems = [{"id": "gs-1"}]
        self.grade_rules = [{"id": "gr-1", "grading_system_id": "gs-1", "grade_label": "A", "grade_point": 4, "min_score": 80, "max_score": 100}]
        self.enrollments = [{"id": "enr-1", "owner_user_id": "user-1", "academic_session_id": "session-1", "semester_id": "sem-1", "class_id": "class-1", "section_id": "sec-1", "enrollment_status": "active"}]
        self.marks = [{"id": "m-1", "school_exam_id": "exam-1", "enrollment_id": "enr-1", "marks_obtained": 90}]
        self.final_marks = []

    def get_academic_session(self, academic_session_id):
        return {"id": academic_session_id, "status": "active"}

    def get_session_settings(self, academic_session_id):
        return {"marks_submission_status": "on"}

    def get_global_settings(self):
        return None

    def get_exam(self, exam_id):
        return next((row for row in self.exams if row["id"] == str(exam_id)), None)

    def list_teacher_assignments(self, **kwargs):
        return [{"id": "ta-1"}]

    def create_exam(self, payload):
        return {"id": "exam-2", **payload}

    def update_exam(self, exam_id, payload):
        row = self.get_exam(exam_id)
        row.update(payload)
        return row

    def get_exam_rule_by_exam(self, exam_id):
        return None

    def upsert_exam_rule(self, payload):
        return {"id": "rule-1", **payload}

    def create_grading_system(self, payload):
        return {"id": "gs-2", **payload}

    def get_grading_system(self, grading_system_id):
        return next((row for row in self.grading_systems if row["id"] == str(grading_system_id)), None)

    def create_grade_rules(self, payloads):
        return payloads

    def list_grade_rules(self, grading_system_id):
        return self.grade_rules

    def upsert_marks(self, payloads):
        return payloads

    def list_enrollments(self, **kwargs):
        return self.enrollments

    def list_marks_by_exam(self, school_exam_id):
        return self.marks

    def list_marks_by_context(self, **kwargs):
        return self.marks

    def list_exams_by_context(self, **kwargs):
        return self.exams

    def upsert_final_marks(self, payloads):
        self.final_marks = payloads
        return payloads

    def get_final_mark(self, final_mark_id):
        return {"id": str(final_mark_id), "academic_session_id": "session-1", "semester_id": "sem-1", "course_id": "course-1"}

    def update_final_mark(self, final_mark_id, payload):
        return {"id": str(final_mark_id), **payload}

    def list_final_marks(self, **kwargs):
        return self.final_marks


class M5Repo(_RepoBase):
    def __init__(self):
        self.assignment = {
            "id": "ass-1",
            "academic_session_id": "session-1",
            "semester_id": "sem-1",
            "class_id": "class-1",
            "section_id": "sec-1",
            "course_id": "course-1",
            "due_at": "2026-01-01T00:00:00+00:00",
            "allow_late_submission": False,
            "max_score": "20",
            "is_published": True,
        }
        self.enrollment = {
            "id": "enr-1",
            "owner_user_id": "user-1",
            "academic_session_id": "session-1",
            "semester_id": "sem-1",
            "class_id": "class-1",
            "section_id": "sec-1",
        }

    def get_academic_session(self, academic_session_id):
        return {"id": academic_session_id, "status": "active"}

    def get_assignment(self, assignment_id):
        return {**self.assignment, "id": str(assignment_id)}

    def list_assignments(self, **kwargs):
        return []

    def create_assignment(self, payload):
        return {"id": "ass-1", **payload}

    def update_assignment(self, assignment_id, payload):
        return {"id": str(assignment_id), **payload}

    def get_enrollment(self, enrollment_id):
        return {**self.enrollment, "id": str(enrollment_id)}

    def create_submission(self, payload):
        return {"id": "sub-1", **payload}

    def list_submissions(self, **kwargs):
        return []

    def get_submission(self, submission_id):
        return {"id": str(submission_id), "assignment_id": "ass-1"}

    def update_submission(self, submission_id, payload):
        return {"id": str(submission_id), **payload}

    def list_teacher_assignments(self, **kwargs):
        return [{"id": "ta-1"}]

    def create_syllabus(self, payload):
        return {"id": "syn-1", **payload}

    def list_syllabi(self, **kwargs):
        return []

    def get_syllabus(self, syllabus_id):
        return {"id": str(syllabus_id)}

    def update_syllabus(self, syllabus_id, payload):
        return {"id": str(syllabus_id), **payload}


class M6Repo(_RepoBase):
    def get_academic_session(self, academic_session_id):
        return {"id": academic_session_id, "status": "active"}

    def list_active_enrollments_for_owner(self, owner_user_id):
        return [{"academic_session_id": "session-1", "section_id": "sec-1", "class_id": "class-1"}]

    def create_notice(self, payload):
        return {"id": "n-1", **payload}

    def list_notices(self, **kwargs):
        return [{"id": "n-1", "audience_scope": "all"}]

    def create_event(self, payload):
        return {"id": "e-1", **payload}

    def list_events(self, **kwargs):
        return [{"id": "e-1", "audience_scope": "all"}]

    def create_routines(self, payloads):
        return payloads

    def list_routines(self, **kwargs):
        return [{"id": "r-1", "audience_scope": "all"}]

    def list_teacher_assignments(self, **kwargs):
        return [{"id": "ta-1"}]


class M7Repo(_RepoBase):
    def __init__(self):
        self.promotions = []
        self.audit = []

    def get_academic_session(self, academic_session_id):
        return {"id": academic_session_id, "status": "active"}

    def list_enrollments_by_ids(self, enrollment_ids):
        return [{"id": eid, "student_id": f"student-{eid}", "owner_user_id": "user-1", "class_id": "class-1", "section_id": "sec-1"} for eid in enrollment_ids]

    def create_promotions(self, payloads):
        self.promotions.extend([{**row, "id": f"p-{idx}"} for idx, row in enumerate(payloads, start=1)])
        return self.promotions

    def list_promotions(self, **kwargs):
        return self.promotions

    def get_promotion(self, promotion_id):
        return next((row for row in self.promotions if row["id"] == str(promotion_id)), {"id": str(promotion_id), "owner_user_id": "user-1", "to_academic_session_id": "session-2"})

    def update_promotion(self, promotion_id, payload):
        return {"id": str(promotion_id), **payload}

    def create_audit_event(self, payload):
        self.audit.append(payload)
        return payload

    def list_audit_events(self, promotion_id):
        return self.audit


class Phase3ServiceTests(unittest.TestCase):
    def test_m1_rejects_overlapping_semesters(self):
        repo = M1Repo()
        repo.sessions = [{"id": "session-1", "status": "active", "is_current": False}]
        repo.semesters = [{"id": "sem-1", "academic_session_id": "session-1", "start_date": date(2026, 1, 1), "end_date": date(2026, 3, 1)}]
        service = M1SessionsService(repo)
        with self.assertRaises(ValidationError):
            service.create_semester({"academic_session_id": "session-1", "semester_name": "S2", "start_date": date(2026, 2, 1), "end_date": date(2026, 4, 1)}, "user-1")

    def test_m1_activate_current_session_requires_active(self):
        repo = M1Repo()
        repo.sessions = [{"id": "session-1", "status": "closed", "is_current": False}]
        service = M1SessionsService(repo)
        with self.assertRaises(ValidationError):
            service.activate_current_session("session-1", "user-1")

    def test_m2_invalid_enrollment_transition(self):
        repo = M2Repo()
        repo.sessions = [{"id": "session-1", "status": "active"}]
        repo.semesters = [{"id": "sem-1", "academic_session_id": "session-1"}]
        repo.classes = [{"id": "class-1", "academic_session_id": "session-1"}]
        repo.sections = [{"id": "sec-1", "academic_session_id": "session-1", "class_id": "class-1"}]
        repo.enrollments = [{"id": "enr-1", "academic_session_id": "session-1", "semester_id": "sem-1", "class_id": "class-1", "section_id": "sec-1", "enrolled_on": date(2026, 1, 1), "enrollment_status": "active"}]
        session_repo = M1Repo()
        session_repo.sessions = [{"id": "session-1", "status": "active"}]
        service = M2StructureService(repo, session_repo)
        with self.assertRaises(ValidationError):
            service.update_enrollment_status("enr-1", {"enrollment_status": "graduated", "exited_on": date(2025, 12, 31)}, "user-1")

    def test_m3_duplicate_attendance_prevented(self):
        repo = M3Repo()
        repo.records = [{"attendance_session_id": "as1", "enrollment_id": "enr-1"}]
        service = M3AttendanceService(repo)
        payload = {"attendance_session_id": "as1", "records": [{"enrollment_id": "enr-1", "owner_user_id": "user-1", "attendance_status": "present"}]}
        with self.assertRaises(ValidationError):
            service.mark_bulk(payload, {"id": "teacher-1", "role": "formateur"})

    def test_m4_grade_rule_overlap_guard(self):
        repo = M4Repo()
        service = M4GradingService(repo)
        with self.assertRaises(ValidationError):
            service.create_grade_rules(
                "gs-1",
                [
                    {"grading_system_id": "gs-1", "grade_label": "A", "grade_point": Decimal("4"), "min_score": Decimal("80"), "max_score": Decimal("100")},
                    {"grading_system_id": "gs-1", "grade_label": "B", "grade_point": Decimal("3"), "min_score": Decimal("75"), "max_score": Decimal("85")},
                ],
                {"id": "teacher-1", "role": "formateur"},
            )

    def test_m4_compute_final_marks(self):
        repo = M4Repo()
        service = M4GradingService(repo)
        results = service.compute_final_marks(
            {"academic_session_id": "session-1", "semester_id": "sem-1", "class_id": "class-1", "section_id": "sec-1", "course_id": "course-1", "grading_system_id": "gs-1"},
            {"id": "teacher-1", "role": "formateur"},
        )
        self.assertTrue(results)
        self.assertEqual(results[0]["grade_label"], "A")

    def test_m5_late_submission_blocked(self):
        repo = M5Repo()
        service = M5AssignmentsService(repo)
        with self.assertRaises(ValidationError):
            service.create_submission(
                {"assignment_id": "ass-1", "enrollment_id": "enr-1", "owner_user_id": "user-1", "submitted_at": "2999-01-01T00:00:00+00:00"},
                {"id": "user-1", "role": "student"},
            )

    def test_m5_submission_context_mismatch_blocked(self):
        repo = M5Repo()
        repo.enrollment["section_id"] = "sec-999"
        service = M5AssignmentsService(repo)
        with self.assertRaises(ValidationError):
            service.create_submission(
                {"assignment_id": "ass-1", "enrollment_id": "enr-1", "owner_user_id": "user-1", "submitted_at": "2025-01-01T00:00:00+00:00"},
                {"id": "user-1", "role": "student"},
            )

    def test_m5_grade_score_over_max_rejected(self):
        repo = M5Repo()
        service = M5AssignmentsService(repo)
        with self.assertRaises(ValidationError):
            service.grade_submission(
                "sub-1",
                {"score": Decimal("25")},
                {"id": "teacher-1", "role": "formateur"},
            )

    def test_m6_notice_scope_validation(self):
        repo = M6Repo()
        service = M6CommunicationsService(repo)
        with self.assertRaises(ValidationError):
            service.create_notice(
                {"academic_session_id": "session-1", "title": "Hi", "body": "Body", "audience_scope": "section"},
                {"id": "teacher-1", "role": "formateur"},
            )

    def test_m7_bulk_promotion_and_audit(self):
        repo = M7Repo()
        service = M7PromotionsService(repo)
        rows = service.create_promotions(
            {
                "from_academic_session_id": "session-1",
                "to_academic_session_id": "session-2",
                "to_class_id": "class-2",
                "to_section_id": "sec-2",
                "enrollment_ids": ["enr-1"],
                "decision_status": "pending",
            },
            {"id": "admin-1", "role": "admin"},
        )
        self.assertEqual(len(rows), 1)
        self.assertTrue(repo.audit)


if __name__ == "__main__":
    unittest.main()
