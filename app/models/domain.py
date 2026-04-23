"""M0 domain models aligned with approved SQL migrations."""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import Field, model_validator

from app.models.base import DomainModel

AcademicSessionStatus = Literal["draft", "active", "closed", "archived"]
EnrollmentStatus = Literal[
    "active",
    "promoted",
    "repeated",
    "transferred",
    "withdrawn",
    "graduated",
    "inactive",
]
TeacherAssignmentRole = Literal["primary", "assistant", "substitute"]
SettingsScope = Literal["global", "session"]
AttendanceMode = Literal["section", "course"]
MarksSubmissionStatus = Literal["on", "off"]
ExamType = Literal[
    "quiz",
    "midterm",
    "final",
    "assignment",
    "practical",
    "oral",
    "continuous",
]
AttendanceStatus = Literal["present", "absent", "late", "excused"]
SubmissionStatus = Literal["draft", "submitted", "resubmitted", "graded", "late", "rejected"]
AudienceScope = Literal["all", "students", "teachers", "class", "section"]
EventType = Literal["academic", "exam", "holiday", "meeting", "general"]
PromotionStatus = Literal["pending", "promoted", "repeated", "transferred", "withdrawn", "rejected"]
PromotionAuditEventType = Literal[
    "created",
    "updated",
    "status_changed",
    "approved",
    "rejected",
    "reverted",
    "commented",
]


def utc_now() -> datetime:
    """Return a timezone-aware UTC datetime for timestamptz defaults."""

    return datetime.now(timezone.utc)


class AcademicSessionModel(DomainModel):
    id: UUID | None = None
    session_name: str = Field(min_length=1, max_length=120)
    starts_on: date | None = None
    ends_on: date | None = None
    is_current: bool = False
    status: AcademicSessionStatus = "active"
    created_by_user_id: UUID | None = None
    updated_by_user_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "AcademicSessionModel":
        if self.starts_on and self.ends_on and self.ends_on < self.starts_on:
            raise ValueError("ends_on must be greater than or equal to starts_on")
        return self


class SemesterModel(DomainModel):
    id: UUID | None = None
    academic_session_id: UUID
    semester_name: str = Field(min_length=1, max_length=80)
    start_date: date
    end_date: date
    is_active: bool = True
    created_by_user_id: UUID | None = None
    updated_by_user_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "SemesterModel":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be greater than or equal to start_date")
        return self


class SchoolClassModel(DomainModel):
    id: UUID | None = None
    academic_session_id: UUID
    class_name: str = Field(min_length=1, max_length=120)
    display_order: int = 0
    is_active: bool = True
    created_by_user_id: UUID | None = None
    updated_by_user_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SectionModel(DomainModel):
    id: UUID | None = None
    academic_session_id: UUID
    class_id: UUID
    section_name: str = Field(min_length=1, max_length=120)
    room_no: str | None = Field(default=None, max_length=60)
    capacity: int | None = Field(default=None, gt=0)
    is_active: bool = True
    created_by_user_id: UUID | None = None
    updated_by_user_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CourseModel(DomainModel):
    id: UUID | None = None
    academic_session_id: UUID
    semester_id: UUID
    class_id: UUID
    course_name: str = Field(min_length=1, max_length=200)
    course_code: str | None = Field(default=None, max_length=60)
    course_type: Literal["core", "elective", "lab", "activity"] = "core"
    credit_hours: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    is_active: bool = True
    created_by_user_id: UUID | None = None
    updated_by_user_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class StudentEnrollmentModel(DomainModel):
    id: UUID | None = None
    student_id: UUID
    owner_user_id: UUID
    academic_session_id: UUID
    semester_id: UUID
    class_id: UUID
    section_id: UUID
    enrollment_status: EnrollmentStatus = "active"
    enrolled_on: date = Field(default_factory=date.today)
    exited_on: date | None = None
    enrollment_no: str | None = Field(default=None, max_length=80)
    notes: str | None = None
    created_by_user_id: UUID | None = None
    updated_by_user_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @model_validator(mode="after")
    def validate_enrollment_dates(self) -> "StudentEnrollmentModel":
        if self.exited_on and self.exited_on < self.enrolled_on:
            raise ValueError("exited_on must be greater than or equal to enrolled_on")
        return self


class TeacherAssignmentModel(DomainModel):
    id: UUID | None = None
    teacher_id: UUID
    academic_session_id: UUID
    semester_id: UUID
    class_id: UUID
    section_id: UUID
    course_id: UUID
    assignment_role: TeacherAssignmentRole = "primary"
    assigned_from: date = Field(default_factory=date.today)
    assigned_to: date | None = None
    is_active: bool = True
    assigned_by_user_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @model_validator(mode="after")
    def validate_assignment_dates(self) -> "TeacherAssignmentModel":
        if self.assigned_to and self.assigned_to < self.assigned_from:
            raise ValueError("assigned_to must be greater than or equal to assigned_from")
        return self


class AcademicSettingsModel(DomainModel):
    id: UUID | None = None
    settings_scope: SettingsScope = "global"
    academic_session_id: UUID | None = None
    attendance_mode: AttendanceMode = "section"
    marks_submission_status: MarksSubmissionStatus = "off"
    grading_policy: str = Field(default="percentage", min_length=1, max_length=30)
    promotion_policy: str = Field(default="manual", min_length=1, max_length=30)
    created_by_user_id: UUID | None = None
    updated_by_user_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @model_validator(mode="after")
    def validate_scope(self) -> "AcademicSettingsModel":
        if self.settings_scope == "global" and self.academic_session_id is not None:
            raise ValueError("global scope must not define academic_session_id")
        if self.settings_scope == "session" and self.academic_session_id is None:
            raise ValueError("session scope requires academic_session_id")
        return self


class SchoolExamModel(DomainModel):
    id: UUID | None = None
    academic_session_id: UUID
    semester_id: UUID
    class_id: UUID
    section_id: UUID
    course_id: UUID
    exam_name: str = Field(min_length=1, max_length=160)
    exam_type: ExamType
    starts_at: datetime
    ends_at: datetime
    max_marks: Decimal = Field(default=Decimal("100"), gt=Decimal("0"))
    pass_marks: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    weight_percent: Decimal = Field(default=Decimal("100"), gt=Decimal("0"), le=Decimal("100"))
    is_published: bool = False
    is_locked: bool = False
    created_by_user_id: UUID | None = None
    updated_by_user_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @model_validator(mode="after")
    def validate_exam_limits(self) -> "SchoolExamModel":
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be greater than starts_at")
        if self.pass_marks > self.max_marks:
            raise ValueError("pass_marks must be less than or equal to max_marks")
        return self


class ExamRuleModel(DomainModel):
    id: UUID | None = None
    school_exam_id: UUID
    rule_name: str = Field(default="default", min_length=1, max_length=120)
    total_marks: Decimal = Field(gt=Decimal("0"))
    pass_marks: Decimal = Field(ge=Decimal("0"))
    marks_distribution_note: str | None = None
    allow_retake: bool = False
    max_attempts: int = Field(default=1, ge=1)
    created_by_user_id: UUID | None = None
    updated_by_user_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @model_validator(mode="after")
    def validate_marks(self) -> "ExamRuleModel":
        if self.pass_marks > self.total_marks:
            raise ValueError("pass_marks must be less than or equal to total_marks")
        return self


class GradingSystemModel(DomainModel):
    id: UUID | None = None
    academic_session_id: UUID
    semester_id: UUID
    class_id: UUID
    system_name: str = Field(min_length=1, max_length=120)
    min_score: Decimal = Field(default=Decimal("0"))
    max_score: Decimal = Field(default=Decimal("100"))
    is_active: bool = True
    created_by_user_id: UUID | None = None
    updated_by_user_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @model_validator(mode="after")
    def validate_bounds(self) -> "GradingSystemModel":
        if self.max_score < self.min_score:
            raise ValueError("max_score must be greater than or equal to min_score")
        return self


class GradeRuleModel(DomainModel):
    id: UUID | None = None
    grading_system_id: UUID
    grade_label: str = Field(min_length=1, max_length=20)
    grade_point: Decimal = Field(ge=Decimal("0"))
    min_score: Decimal
    max_score: Decimal
    is_passing: bool = True
    created_by_user_id: UUID | None = None
    updated_by_user_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @model_validator(mode="after")
    def validate_score_range(self) -> "GradeRuleModel":
        if self.min_score > self.max_score:
            raise ValueError("min_score must be less than or equal to max_score")
        return self


class GradeRuleSetModel(DomainModel):
    """Model-level anti-overlap validation for grade rules in one grading system."""

    grading_system_id: UUID
    rules: list[GradeRuleModel]

    @model_validator(mode="after")
    def validate_non_overlapping_ranges(self) -> "GradeRuleSetModel":
        if not self.rules:
            raise ValueError("rules cannot be empty")

        for rule in self.rules:
            if rule.grading_system_id != self.grading_system_id:
                raise ValueError("all rules must belong to the same grading_system_id")

        ordered_rules = sorted(self.rules, key=lambda rule: (rule.min_score, rule.max_score))

        previous_max: Decimal | None = None
        for rule in ordered_rules:
            if previous_max is not None and rule.min_score <= previous_max:
                raise ValueError(
                    "grade rule ranges overlap or touch; each range must start above the previous max_score"
                )
            previous_max = rule.max_score
        return self


class MarkModel(DomainModel):
    id: UUID | None = None
    enrollment_id: UUID
    owner_user_id: UUID
    school_exam_id: UUID
    exam_rule_id: UUID | None = None
    marks_obtained: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    is_absent: bool = False
    is_excused: bool = False
    remarks: str | None = None
    entered_by_user_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @model_validator(mode="after")
    def validate_absence_value(self) -> "MarkModel":
        if self.is_absent and self.marks_obtained != Decimal("0"):
            raise ValueError("marks_obtained must be 0 when is_absent is true")
        return self


class FinalMarkModel(DomainModel):
    id: UUID | None = None
    enrollment_id: UUID
    owner_user_id: UUID
    academic_session_id: UUID
    semester_id: UUID
    course_id: UUID
    grading_system_id: UUID | None = None
    grade_rule_id: UUID | None = None
    calculated_marks: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    final_marks: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    grade_label: str | None = Field(default=None, max_length=20)
    grade_point: Decimal | None = Field(default=None, ge=Decimal("0"))
    note: str | None = None
    grade_snapshot: dict[str, Any] = Field(default_factory=dict)
    finalized_by_user_id: UUID | None = None
    finalized_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @model_validator(mode="after")
    def validate_finalize_pair(self) -> "FinalMarkModel":
        has_actor = self.finalized_by_user_id is not None
        has_time = self.finalized_at is not None
        if has_actor != has_time:
            raise ValueError("finalized_by_user_id and finalized_at must be set together")
        return self


class AttendanceSessionModel(DomainModel):
    id: UUID | None = None
    academic_session_id: UUID
    semester_id: UUID
    class_id: UUID
    section_id: UUID
    course_id: UUID | None = None
    attendance_mode: AttendanceMode = "section"
    attendance_date: date
    slot_code: str = Field(default="default", min_length=1, max_length=60)
    notes: str | None = None
    marked_by_user_id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @model_validator(mode="after")
    def validate_mode_course_dependency(self) -> "AttendanceSessionModel":
        if self.attendance_mode == "course" and self.course_id is None:
            raise ValueError("course_id is required when attendance_mode is 'course'")
        return self


class AttendanceRecordModel(DomainModel):
    id: UUID | None = None
    attendance_session_id: UUID
    enrollment_id: UUID
    owner_user_id: UUID
    attendance_status: AttendanceStatus
    remarks: str | None = None
    recorded_by_user_id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AssignmentModel(DomainModel):
    id: UUID | None = None
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
    assigned_at: datetime = Field(default_factory=utc_now)
    due_at: datetime | None = None
    max_score: Decimal = Field(default=Decimal("100"), gt=Decimal("0"))
    allow_late_submission: bool = False
    is_published: bool = False
    created_by_user_id: UUID | None = None
    updated_by_user_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @model_validator(mode="after")
    def validate_due_date(self) -> "AssignmentModel":
        if self.due_at and self.due_at < self.assigned_at:
            raise ValueError("due_at must be greater than or equal to assigned_at")
        return self


class AssignmentSubmissionModel(DomainModel):
    id: UUID | None = None
    assignment_id: UUID
    enrollment_id: UUID
    owner_user_id: UUID
    attempt_no: int = Field(default=1, ge=1)
    submitted_at: datetime = Field(default_factory=utc_now)
    submission_path: str | None = None
    submission_text: str | None = None
    submission_status: SubmissionStatus = "submitted"
    score: Decimal | None = Field(default=None, ge=Decimal("0"))
    feedback: str | None = None
    graded_by_user_id: UUID | None = None
    graded_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @model_validator(mode="after")
    def validate_grading_pair(self) -> "AssignmentSubmissionModel":
        has_grader = self.graded_by_user_id is not None
        has_graded_at = self.graded_at is not None
        if has_grader != has_graded_at:
            raise ValueError("graded_by_user_id and graded_at must be set together")
        return self


class RoutineModel(DomainModel):
    id: UUID | None = None
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
    created_by_user_id: UUID | None = None
    updated_by_user_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @model_validator(mode="after")
    def validate_time_range(self) -> "RoutineModel":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be greater than start_time")
        return self


class EventModel(DomainModel):
    id: UUID | None = None
    academic_session_id: UUID
    event_title: str = Field(min_length=1, max_length=220)
    event_type: EventType = "general"
    starts_at: datetime
    ends_at: datetime
    location: str | None = Field(default=None, max_length=220)
    description: str | None = None
    audience_scope: AudienceScope = "all"
    class_id: UUID | None = None
    section_id: UUID | None = None
    created_by_user_id: UUID | None = None
    updated_by_user_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @model_validator(mode="after")
    def validate_time_range(self) -> "EventModel":
        if self.ends_at < self.starts_at:
            raise ValueError("ends_at must be greater than or equal to starts_at")
        return self


class NoticeModel(DomainModel):
    id: UUID | None = None
    academic_session_id: UUID
    title: str = Field(min_length=1, max_length=220)
    body: str = Field(min_length=1)
    audience_scope: AudienceScope = "all"
    class_id: UUID | None = None
    section_id: UUID | None = None
    published_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime | None = None
    is_pinned: bool = False
    created_by_user_id: UUID | None = None
    updated_by_user_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @model_validator(mode="after")
    def validate_expiry(self) -> "NoticeModel":
        if self.expires_at and self.expires_at < self.published_at:
            raise ValueError("expires_at must be greater than or equal to published_at")
        return self


class PromotionModel(DomainModel):
    id: UUID | None = None
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
    decision_status: PromotionStatus = "pending"
    decision_reason: str | None = None
    id_card_number: str | None = Field(default=None, max_length=80)
    promoted_by_user_id: UUID
    promoted_at: datetime = Field(default_factory=utc_now)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @model_validator(mode="after")
    def validate_session_transition(self) -> "PromotionModel":
        if self.from_academic_session_id == self.to_academic_session_id:
            raise ValueError("from_academic_session_id and to_academic_session_id must differ")
        return self


class PromotionAuditEventModel(DomainModel):
    id: UUID | None = None
    promotion_id: UUID
    event_type: PromotionAuditEventType
    actor_user_id: UUID
    event_payload: dict[str, Any] = Field(default_factory=dict)
    event_note: str | None = None
    created_at: datetime | None = None


class SyllabusModel(DomainModel):
    id: UUID | None = None
    academic_session_id: UUID
    semester_id: UUID
    class_id: UUID
    course_id: UUID
    title: str = Field(min_length=1, max_length=220)
    syllabus_path: str | None = None
    content: str | None = None
    is_published: bool = False
    created_by_user_id: UUID | None = None
    updated_by_user_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
