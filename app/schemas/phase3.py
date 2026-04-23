"""Pydantic schemas for Phase 3 school-domain modules (M1-M7)."""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Phase3BaseSchema(BaseModel):
    """Strict input/output schema baseline."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# M1 ───────────────────────────────────────────────────────────────────────────


class SchoolSessionCreate(Phase3BaseSchema):
    session_name: str = Field(min_length=1, max_length=120)
    starts_on: date | None = None
    ends_on: date | None = None
    is_current: bool = False
    status: Literal["draft", "active", "closed", "archived"] = "draft"

    @model_validator(mode="after")
    def validate_dates(self) -> "SchoolSessionCreate":
        if self.starts_on and self.ends_on and self.ends_on < self.starts_on:
            raise ValueError("ends_on must be greater than or equal to starts_on")
        return self


class SchoolSessionUpdate(Phase3BaseSchema):
    session_name: str | None = Field(default=None, min_length=1, max_length=120)
    starts_on: date | None = None
    ends_on: date | None = None
    status: Literal["draft", "active", "closed", "archived"] | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "SchoolSessionUpdate":
        if self.starts_on and self.ends_on and self.ends_on < self.starts_on:
            raise ValueError("ends_on must be greater than or equal to starts_on")
        return self


class SemesterCreate(Phase3BaseSchema):
    academic_session_id: UUID
    semester_name: str = Field(min_length=1, max_length=80)
    start_date: date
    end_date: date
    is_active: bool = True

    @model_validator(mode="after")
    def validate_dates(self) -> "SemesterCreate":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be greater than or equal to start_date")
        return self


class SemesterUpdate(Phase3BaseSchema):
    semester_name: str | None = Field(default=None, min_length=1, max_length=80)
    start_date: date | None = None
    end_date: date | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "SemesterUpdate":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be greater than or equal to start_date")
        return self


class AcademicSettingsUpsert(Phase3BaseSchema):
    settings_scope: Literal["global", "session"] = "session"
    academic_session_id: UUID | None = None
    attendance_mode: Literal["section", "course"] = "section"
    marks_submission_status: Literal["on", "off"] = "off"
    grading_policy: str = Field(default="percentage", min_length=1, max_length=30)
    promotion_policy: str = Field(default="manual", min_length=1, max_length=30)

    @model_validator(mode="after")
    def validate_scope(self) -> "AcademicSettingsUpsert":
        if self.settings_scope == "global" and self.academic_session_id is not None:
            raise ValueError("global scope cannot include academic_session_id")
        if self.settings_scope == "session" and self.academic_session_id is None:
            raise ValueError("session scope requires academic_session_id")
        return self


# M2 ───────────────────────────────────────────────────────────────────────────


class SchoolClassCreate(Phase3BaseSchema):
    academic_session_id: UUID
    class_name: str = Field(min_length=1, max_length=120)
    display_order: int = 0
    is_active: bool = True


class SchoolClassUpdate(Phase3BaseSchema):
    class_name: str | None = Field(default=None, min_length=1, max_length=120)
    display_order: int | None = None
    is_active: bool | None = None


class SectionCreate(Phase3BaseSchema):
    academic_session_id: UUID
    class_id: UUID
    section_name: str = Field(min_length=1, max_length=120)
    room_no: str | None = Field(default=None, max_length=60)
    capacity: int | None = Field(default=None, gt=0)
    is_active: bool = True


class SectionUpdate(Phase3BaseSchema):
    section_name: str | None = Field(default=None, min_length=1, max_length=120)
    room_no: str | None = Field(default=None, max_length=60)
    capacity: int | None = Field(default=None, gt=0)
    is_active: bool | None = None


class CourseCreate(Phase3BaseSchema):
    academic_session_id: UUID
    semester_id: UUID
    class_id: UUID
    course_name: str = Field(min_length=1, max_length=200)
    course_code: str | None = Field(default=None, max_length=60)
    course_type: Literal["core", "elective", "lab", "activity"] = "core"
    credit_hours: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    is_active: bool = True


class CourseUpdate(Phase3BaseSchema):
    course_name: str | None = Field(default=None, min_length=1, max_length=200)
    course_code: str | None = Field(default=None, max_length=60)
    course_type: Literal["core", "elective", "lab", "activity"] | None = None
    credit_hours: Decimal | None = Field(default=None, ge=Decimal("0"))
    is_active: bool | None = None


class StudentEnrollmentCreate(Phase3BaseSchema):
    student_id: UUID
    owner_user_id: UUID
    academic_session_id: UUID
    semester_id: UUID
    class_id: UUID
    section_id: UUID
    enrollment_status: Literal[
        "active",
        "promoted",
        "repeated",
        "transferred",
        "withdrawn",
        "graduated",
        "inactive",
    ] = "active"
    enrolled_on: date = Field(default_factory=date.today)
    exited_on: date | None = None
    enrollment_no: str | None = Field(default=None, max_length=80)
    notes: str | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "StudentEnrollmentCreate":
        if self.exited_on and self.exited_on < self.enrolled_on:
            raise ValueError("exited_on must be greater than or equal to enrolled_on")
        return self


class StudentEnrollmentStatusUpdate(Phase3BaseSchema):
    enrollment_status: Literal[
        "active",
        "promoted",
        "repeated",
        "transferred",
        "withdrawn",
        "graduated",
        "inactive",
    ]
    exited_on: date | None = None
    notes: str | None = None


class TeacherAssignmentCreate(Phase3BaseSchema):
    teacher_id: UUID
    academic_session_id: UUID
    semester_id: UUID
    class_id: UUID
    section_id: UUID
    course_id: UUID
    assignment_role: Literal["primary", "assistant", "substitute"] = "primary"
    assigned_from: date = Field(default_factory=date.today)
    assigned_to: date | None = None
    is_active: bool = True

    @model_validator(mode="after")
    def validate_dates(self) -> "TeacherAssignmentCreate":
        if self.assigned_to and self.assigned_to < self.assigned_from:
            raise ValueError("assigned_to must be greater than or equal to assigned_from")
        return self


class TeacherAssignmentBulkCreate(Phase3BaseSchema):
    assignments: list[TeacherAssignmentCreate] = Field(min_length=1)


# M3 ───────────────────────────────────────────────────────────────────────────


class AttendanceSessionCreate(Phase3BaseSchema):
    academic_session_id: UUID
    semester_id: UUID
    class_id: UUID
    section_id: UUID
    course_id: UUID | None = None
    attendance_mode: Literal["section", "course"] = "section"
    attendance_date: date
    slot_code: str = Field(default="default", min_length=1, max_length=60)
    notes: str | None = None

    @model_validator(mode="after")
    def validate_mode(self) -> "AttendanceSessionCreate":
        if self.attendance_mode == "course" and self.course_id is None:
            raise ValueError("course_id is required when attendance_mode is 'course'")
        return self


class AttendanceRecordCreate(Phase3BaseSchema):
    enrollment_id: UUID
    owner_user_id: UUID
    attendance_status: Literal["present", "absent", "late", "excused"]
    remarks: str | None = None


class AttendanceBulkCreate(Phase3BaseSchema):
    attendance_session_id: UUID | None = None
    attendance_session: AttendanceSessionCreate | None = None
    prevent_duplicates: bool = True
    records: list[AttendanceRecordCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_context(self) -> "AttendanceBulkCreate":
        if self.attendance_session_id is None and self.attendance_session is None:
            raise ValueError("attendance_session_id or attendance_session must be provided")
        return self


# M4 ───────────────────────────────────────────────────────────────────────────


class SchoolExamCreate(Phase3BaseSchema):
    academic_session_id: UUID
    semester_id: UUID
    class_id: UUID
    section_id: UUID
    course_id: UUID
    exam_name: str = Field(min_length=1, max_length=160)
    exam_type: Literal["quiz", "midterm", "final", "assignment", "practical", "oral", "continuous"]
    starts_at: datetime
    ends_at: datetime
    max_marks: Decimal = Field(default=Decimal("100"), gt=Decimal("0"))
    pass_marks: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    weight_percent: Decimal = Field(default=Decimal("100"), gt=Decimal("0"), le=Decimal("100"))
    is_published: bool = False

    @model_validator(mode="after")
    def validate_fields(self) -> "SchoolExamCreate":
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be greater than starts_at")
        if self.pass_marks > self.max_marks:
            raise ValueError("pass_marks must be less than or equal to max_marks")
        return self


class SchoolExamUpdate(Phase3BaseSchema):
    exam_name: str | None = Field(default=None, min_length=1, max_length=160)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    max_marks: Decimal | None = Field(default=None, gt=Decimal("0"))
    pass_marks: Decimal | None = Field(default=None, ge=Decimal("0"))
    weight_percent: Decimal | None = Field(default=None, gt=Decimal("0"), le=Decimal("100"))
    is_published: bool | None = None
    is_locked: bool | None = None


class ExamRuleUpsert(Phase3BaseSchema):
    school_exam_id: UUID
    rule_name: str = Field(default="default", min_length=1, max_length=120)
    total_marks: Decimal = Field(gt=Decimal("0"))
    pass_marks: Decimal = Field(ge=Decimal("0"))
    marks_distribution_note: str | None = None
    allow_retake: bool = False
    max_attempts: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def validate_marks(self) -> "ExamRuleUpsert":
        if self.pass_marks > self.total_marks:
            raise ValueError("pass_marks must be less than or equal to total_marks")
        return self


class GradingSystemCreate(Phase3BaseSchema):
    academic_session_id: UUID
    semester_id: UUID
    class_id: UUID
    system_name: str = Field(min_length=1, max_length=120)
    min_score: Decimal = Field(default=Decimal("0"))
    max_score: Decimal = Field(default=Decimal("100"))
    is_active: bool = True

    @model_validator(mode="after")
    def validate_bounds(self) -> "GradingSystemCreate":
        if self.max_score < self.min_score:
            raise ValueError("max_score must be greater than or equal to min_score")
        return self


class GradeRuleCreate(Phase3BaseSchema):
    grading_system_id: UUID
    grade_label: str = Field(min_length=1, max_length=20)
    grade_point: Decimal = Field(ge=Decimal("0"))
    min_score: Decimal
    max_score: Decimal
    is_passing: bool = True

    @model_validator(mode="after")
    def validate_bounds(self) -> "GradeRuleCreate":
        if self.min_score > self.max_score:
            raise ValueError("min_score must be less than or equal to max_score")
        return self


class GradeRuleSetCreate(Phase3BaseSchema):
    grading_system_id: UUID
    rules: list[GradeRuleCreate] = Field(min_length=1)


class MarkEntry(Phase3BaseSchema):
    enrollment_id: UUID
    owner_user_id: UUID
    marks_obtained: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    is_absent: bool = False
    is_excused: bool = False
    remarks: str | None = None

    @model_validator(mode="after")
    def validate_absent(self) -> "MarkEntry":
        if self.is_absent and self.marks_obtained != Decimal("0"):
            raise ValueError("marks_obtained must be 0 when is_absent is true")
        return self


class MarksBulkUpsert(Phase3BaseSchema):
    school_exam_id: UUID
    exam_rule_id: UUID | None = None
    entries: list[MarkEntry] = Field(min_length=1)


class FinalMarksComputeRequest(Phase3BaseSchema):
    academic_session_id: UUID
    semester_id: UUID
    class_id: UUID
    section_id: UUID
    course_id: UUID
    grading_system_id: UUID


class FinalMarkFinalizeRequest(Phase3BaseSchema):
    final_mark_id: UUID


# M5 ───────────────────────────────────────────────────────────────────────────


class AssignmentCreate(Phase3BaseSchema):
    academic_session_id: UUID
    semester_id: UUID
    class_id: UUID
    section_id: UUID
    course_id: UUID
    teacher_assignment_id: UUID | None = None
    assignment_name: str = Field(min_length=1, max_length=220)
    description: str | None = None
    instructions: str | None = None
    attachment_path: str | None = None
    assigned_at: datetime | None = None
    due_at: datetime | None = None
    max_score: Decimal = Field(default=Decimal("100"), gt=Decimal("0"))
    allow_late_submission: bool = False
    is_published: bool = False

    @model_validator(mode="after")
    def validate_due_date(self) -> "AssignmentCreate":
        if self.assigned_at and self.due_at and self.due_at < self.assigned_at:
            raise ValueError("due_at must be greater than or equal to assigned_at")
        return self


class AssignmentUpdate(Phase3BaseSchema):
    assignment_name: str | None = Field(default=None, min_length=1, max_length=220)
    description: str | None = None
    instructions: str | None = None
    attachment_path: str | None = None
    assigned_at: datetime | None = None
    due_at: datetime | None = None
    max_score: Decimal | None = Field(default=None, gt=Decimal("0"))
    allow_late_submission: bool | None = None
    is_published: bool | None = None

    @model_validator(mode="after")
    def validate_due_date(self) -> "AssignmentUpdate":
        if self.assigned_at and self.due_at and self.due_at < self.assigned_at:
            raise ValueError("due_at must be greater than or equal to assigned_at")
        return self


class AssignmentSubmissionCreate(Phase3BaseSchema):
    assignment_id: UUID | None = None
    enrollment_id: UUID
    owner_user_id: UUID | None = None
    attempt_no: int = Field(default=1, ge=1)
    submission_path: str | None = None
    submission_text: str | None = None
    submission_metadata: dict = Field(default_factory=dict)


class AssignmentSubmissionGradeUpdate(Phase3BaseSchema):
    submission_status: Literal["graded", "rejected", "submitted", "resubmitted", "late"] = "graded"
    score: Decimal | None = Field(default=None, ge=Decimal("0"))
    feedback: str | None = None


class SyllabusCreate(Phase3BaseSchema):
    academic_session_id: UUID
    semester_id: UUID
    class_id: UUID
    course_id: UUID
    title: str = Field(min_length=1, max_length=220)
    syllabus_path: str | None = None
    content: str | None = None
    is_published: bool = False


class SyllabusUpdate(Phase3BaseSchema):
    title: str | None = Field(default=None, min_length=1, max_length=220)
    syllabus_path: str | None = None
    content: str | None = None
    is_published: bool | None = None


# M6 ───────────────────────────────────────────────────────────────────────────


class NoticeCreate(Phase3BaseSchema):
    academic_session_id: UUID
    title: str = Field(min_length=1, max_length=220)
    body: str = Field(min_length=1)
    audience_scope: Literal["all", "students", "teachers", "class", "section"] = "all"
    class_id: UUID | None = None
    section_id: UUID | None = None
    published_at: datetime | None = None
    expires_at: datetime | None = None
    is_pinned: bool = False

    @model_validator(mode="after")
    def validate_dates(self) -> "NoticeCreate":
        if self.published_at and self.expires_at and self.expires_at < self.published_at:
            raise ValueError("expires_at must be greater than or equal to published_at")
        return self


class EventCreate(Phase3BaseSchema):
    academic_session_id: UUID
    event_title: str = Field(min_length=1, max_length=220)
    event_type: Literal["academic", "exam", "holiday", "meeting", "general"] = "general"
    starts_at: datetime
    ends_at: datetime
    location: str | None = Field(default=None, max_length=220)
    description: str | None = None
    audience_scope: Literal["all", "students", "teachers", "class", "section"] = "all"
    class_id: UUID | None = None
    section_id: UUID | None = None

    @model_validator(mode="after")
    def validate_range(self) -> "EventCreate":
        if self.ends_at < self.starts_at:
            raise ValueError("ends_at must be greater than or equal to starts_at")
        return self


class RoutineCreate(Phase3BaseSchema):
    academic_session_id: UUID
    semester_id: UUID
    class_id: UUID
    section_id: UUID
    course_id: UUID
    teacher_assignment_id: UUID | None = None
    weekday: int = Field(ge=1, le=7)
    start_time: time
    end_time: time
    room_no: str | None = Field(default=None, max_length=60)
    is_recurring: bool = True

    @model_validator(mode="after")
    def validate_time(self) -> "RoutineCreate":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be greater than start_time")
        return self


class RoutineBulkCreate(Phase3BaseSchema):
    routines: list[RoutineCreate] = Field(min_length=1)


# M7 ───────────────────────────────────────────────────────────────────────────


class PromotionCreate(Phase3BaseSchema):
    student_id: UUID
    owner_user_id: UUID
    from_enrollment_id: UUID | None = None
    to_enrollment_id: UUID | None = None
    from_academic_session_id: UUID
    to_academic_session_id: UUID
    from_class_id: UUID | None = None
    from_section_id: UUID | None = None
    to_class_id: UUID
    to_section_id: UUID
    decision_status: Literal["pending", "promoted", "repeated", "transferred", "withdrawn", "rejected"] = "pending"
    decision_reason: str | None = None
    id_card_number: str | None = Field(default=None, max_length=80)

    @model_validator(mode="after")
    def validate_sessions(self) -> "PromotionCreate":
        if self.from_academic_session_id == self.to_academic_session_id:
            raise ValueError("from_academic_session_id and to_academic_session_id must differ")
        return self


class PromotionBulkCreate(Phase3BaseSchema):
    from_academic_session_id: UUID
    to_academic_session_id: UUID
    from_semester_id: UUID
    to_semester_id: UUID
    to_class_id: UUID
    to_section_id: UUID
    enrollment_ids: list[UUID] = Field(min_length=1)
    passing_score: Decimal = Field(default=Decimal("50"), ge=Decimal("0"), le=Decimal("100"))
    force_promote: bool = False


class PromotionStatusUpdate(Phase3BaseSchema):
    decision_status: Literal["pending", "promoted", "repeated", "transferred", "withdrawn", "rejected"]
    decision_reason: str | None = None


class PromotionAuditEventCreate(Phase3BaseSchema):
    promotion_id: UUID
    event_type: Literal["created", "updated", "status_changed", "approved", "rejected", "reverted", "commented"]
    event_payload: dict = Field(default_factory=dict)
    event_note: str | None = None
