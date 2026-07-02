from datetime import datetime
from typing import Any, Literal, Optional
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, EmailStr, Field, model_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class UserOut(ORMModel):
    id: int
    name: str
    email: EmailStr
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime


class UserProfileOut(UserOut):
    teaching_count: int
    learning_count: int


class UserProfileUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    bio: Optional[str] = Field(default=None, max_length=1000)
    avatar_url: Optional[AnyHttpUrl] = None

    @model_validator(mode="after")
    def name_must_contain_text(self):
        if len(self.name.strip()) < 2:
            raise ValueError("Name must contain at least 2 characters")
        return self


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def password_must_change(self):
        if self.current_password == self.new_password:
            raise ValueError("New password must be different from the current password")
        return self


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginInput(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str


class ForgotPasswordInput(BaseModel):
    email: str = Field(min_length=3, max_length=255)


class ResetPasswordInput(BaseModel):
    token: str = Field(min_length=20, max_length=500)
    new_password: str = Field(min_length=8, max_length=128)


class MessageOut(BaseModel):
    message: str


class ClassroomCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    subject: str = Field(min_length=2, max_length=160)
    description: str = ""


class ClassroomUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    subject: str = Field(min_length=2, max_length=160)
    description: str = ""


class ClassroomOut(ORMModel):
    id: int
    name: str
    subject: str
    description: str
    join_code: str
    created_by_user_id: int
    created_at: datetime
    archived: bool = False
    archived_at: Optional[datetime] = None
    role: Optional[Literal["teacher", "student"]] = None


class JoinClass(BaseModel):
    join_code: str


class MemberOut(BaseModel):
    id: int
    user_id: int
    name: str
    email: str
    role: Literal["teacher", "student"]
    joined_at: datetime


ActivityType = Literal[
    "dashboard",
    "class_view",
    "material_view",
    "assessment_view",
    "assessment_attempt",
    "codespace_view",
    "codespace_task",
    "idle",
]


class ClassActivityInput(BaseModel):
    activity_type: ActivityType
    activity_label: Optional[str] = Field(default=None, max_length=300)
    entity_type: Optional[str] = Field(default=None, max_length=80)
    entity_id: Optional[int] = None
    route_path: Optional[str] = Field(default=None, max_length=500)


class ActiveUserOut(BaseModel):
    user_id: int
    name: str
    email: str
    activity_type: ActivityType
    activity_label: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    route_path: Optional[str] = None
    last_active_at: datetime
    status: Literal["active", "recently_active", "offline"]


class UnitCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    order_number: int = Field(default=1, ge=1)


class UnitOut(ORMModel):
    id: int
    classroom_id: int
    title: str
    description: str
    order_number: int
    created_at: datetime


class MaterialInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    type: Literal["markdown", "link"]
    content_markdown: Optional[str] = None
    resource_url: Optional[str] = None

    @model_validator(mode="after")
    def validate_content(self):
        if self.type == "markdown" and not self.content_markdown:
            raise ValueError("Markdown content is required")
        if self.type == "link" and not self.resource_url:
            raise ValueError("Resource URL is required")
        return self


class MaterialAttachmentOut(ORMModel):
    id: int
    material_id: int
    file_name: str
    file_type: str
    mime_type: str
    file_size: int
    uploaded_at: datetime


class MaterialOut(ORMModel):
    id: int
    unit_id: int
    title: str
    type: str
    content_markdown: Optional[str]
    resource_url: Optional[str]
    created_by_user_id: int
    created_at: datetime
    updated_at: datetime
    attachments: list[MaterialAttachmentOut] = Field(default_factory=list)


class TestInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    duration_minutes: int = Field(default=30, ge=1, le=600)
    is_published: bool = False


class QuestionInput(BaseModel):
    question: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_option: Literal["A", "B", "C", "D"]
    explanation: str = ""
    marks: float = Field(default=1, gt=0)


class QuestionOut(ORMModel):
    id: int
    test_id: int
    question: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_option: Optional[str] = None
    explanation: Optional[str] = None
    marks: float


class TestOut(ORMModel):
    id: int
    unit_id: int
    title: str
    description: str
    duration_minutes: int
    is_published: bool
    created_by_user_id: int
    created_at: datetime
    questions: list[QuestionOut] = Field(default_factory=list)


class AnswerInput(BaseModel):
    question_id: int
    selected_option: Optional[Literal["A", "B", "C", "D"]] = None


class AttemptInput(BaseModel):
    answers: list[AnswerInput]

    @model_validator(mode="after")
    def reject_duplicate_questions(self):
        question_ids = [answer.question_id for answer in self.answers]
        if len(question_ids) != len(set(question_ids)):
            raise ValueError("Each question may only be answered once")
        return self


class AnswerReview(BaseModel):
    question_id: int
    question: str
    selected_option: Optional[str]
    correct_option: str
    is_correct: bool
    explanation: str


class AttemptOut(BaseModel):
    id: int
    test_id: int
    test_title: str
    student_id: int
    student_name: str
    score: float
    total_marks: float
    submitted_at: datetime
    answers: list[AnswerReview] = Field(default_factory=list)


class AssessmentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    timing_mode: Literal["untimed", "timed", "deadline", "timed_deadline"] = "untimed"
    duration_minutes: Optional[int] = Field(default=None, ge=1, le=600)
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None

    @model_validator(mode="after")
    def validate_timing(self):
        timed = self.timing_mode in {"timed", "timed_deadline"}
        deadline = self.timing_mode in {"deadline", "timed_deadline"}
        if timed and not self.duration_minutes:
            raise ValueError("Duration minutes is required for timed assessments")
        if not timed:
            self.duration_minutes = None
        if deadline and not self.ends_at:
            raise ValueError("End deadline is required for deadline assessments")
        if not deadline:
            self.starts_at = None
            self.ends_at = None
        if self.starts_at and self.ends_at and self.starts_at >= self.ends_at:
            raise ValueError("Start time must be before end deadline")
        return self


class AssessmentStatusUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    timing_mode: Optional[Literal["untimed", "timed", "deadline", "timed_deadline"]] = None
    duration_minutes: Optional[int] = Field(default=None, ge=1, le=600)
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    is_published: Optional[bool] = None
    is_accepting_responses: Optional[bool] = None


class AssessmentQuestionOut(ORMModel):
    id: int
    question_id_from_excel: str
    question_type: Literal["MCQ", "FILLUP", "CODING"]
    question_text: str
    option_a: Optional[str]
    option_b: Optional[str]
    option_c: Optional[str]
    option_d: Optional[str]
    marks: float
    difficulty: Optional[str]
    starter_code: Optional[str]
    visible_test_cases: Optional[str]
    expected_output: Optional[str]
    tags: Optional[str]
    order_number: int


class AssessmentAnswerKeyOut(ORMModel):
    correct_answer: Optional[str]
    accepted_answers: Optional[str]
    explanation: Optional[str]
    hidden_test_cases: Optional[str]


class AssessmentTeacherQuestionOut(AssessmentQuestionOut):
    case_sensitive: bool
    answer_key: Optional[AssessmentAnswerKeyOut] = None


class AssessmentOut(BaseModel):
    id: int
    unit_id: int
    title: str
    description: str
    timing_mode: Literal["untimed", "timed", "deadline", "timed_deadline"] = "untimed"
    duration_minutes: Optional[int]
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    is_published: bool
    is_accepting_responses: bool
    results_published: bool
    archived: bool
    question_count: int
    created_at: datetime


class AssessmentStudentOut(AssessmentOut):
    questions: list[AssessmentQuestionOut]
    attempt_id: Optional[int] = None
    attempt_status: Optional[str] = None
    attempt_started_at: Optional[datetime] = None
    attempt_expires_at: Optional[datetime] = None


class AssessmentPreviewOut(AssessmentOut):
    questions: list[AssessmentQuestionOut]


class AssessmentDashboardStats(BaseModel):
    total_students: int
    submitted_count: int
    pending_count: int
    evaluated_count: int
    published_count: int


class AssessmentTeacherOut(AssessmentOut):
    source_excel_file: Optional[str]
    questions: list[AssessmentTeacherQuestionOut]
    stats: AssessmentDashboardStats


class AssessmentResponseInput(BaseModel):
    question_id: int
    selected_option: Optional[Literal["A", "B", "C", "D"]] = None
    text_answer: Optional[str] = None
    code_answer: Optional[str] = None


class AssessmentSubmitInput(BaseModel):
    responses: list[AssessmentResponseInput]

    @model_validator(mode="after")
    def reject_duplicate_questions(self):
        question_ids = [response.question_id for response in self.responses]
        if len(question_ids) != len(set(question_ids)):
            raise ValueError("Each question may only be answered once")
        return self


class AssessmentAutoSubmitInput(AssessmentSubmitInput):
    auto_submit_reason: Literal["browser_back", "refresh", "tab_close", "route_leave"] = "route_leave"


class CodingRunInput(BaseModel):
    question_id: int
    code: str = Field(min_length=1, max_length=50000)
    language: Literal["python"] = "python"


class CodingTaskRunInput(BaseModel):
    code: str = Field(min_length=1, max_length=50000)
    language: Literal["python"] = "python"


class CodeRunInput(BaseModel):
    code: str = Field(min_length=1, max_length=50000)
    language: Literal["python"] = "python"


class CodeRunOut(BaseModel):
    status: Literal["completed", "error", "timeout"]
    stdout: str = ""
    stderr: str = ""
    execution_time_ms: int


class CodeRunTestsInput(CodeRunInput):
    visible_test_cases: Optional[str] = None
    hidden_test_cases: Optional[str] = None


class CodingTestCaseResult(BaseModel):
    index: int
    input: str
    expected: str
    actual: Optional[str] = None
    passed: bool
    stdout: str = ""
    error: Optional[str] = None


class CodingRunOut(BaseModel):
    success: bool
    stdout: str
    stderr: str
    error_type: Optional[str] = None
    test_case_results: list[CodingTestCaseResult] = Field(default_factory=list)
    execution_time_ms: int


class AssessmentSubmissionOut(BaseModel):
    attempt_id: int
    status: str
    message: str


class AssessmentAttemptStartOut(BaseModel):
    can_start: bool
    attempt_id: Optional[int] = None
    status: Optional[str] = None
    message: str
    assessment: Optional[AssessmentStudentOut] = None


AssessmentAttemptEventType = Literal[
    "assessment_started",
    "assessment_submitted",
    "auto_submitted_on_leave",
    "left_assessment_page",
    "fullscreen_enabled",
    "fullscreen_failed",
    "fullscreen_exit",
    "tab_hidden",
    "window_blur",
    "returned_to_assessment",
    "copy_attempt",
    "paste_attempt",
    "cut_attempt",
    "right_click",
    "blocked_shortcut",
    "before_unload",
    "auto_submit_on_leave",
]


class AssessmentAttemptEventCreate(BaseModel):
    event_type: AssessmentAttemptEventType
    event_message: str = Field(min_length=1, max_length=500)
    metadata: Optional[dict[str, Any]] = None


class AssessmentAttemptEventOut(BaseModel):
    id: int
    attempt_id: int
    student_id: int
    assessment_id: int
    event_type: str
    event_message: str
    metadata: Optional[dict[str, Any]] = None
    created_at: datetime


class AssessmentTeacherResponseOut(BaseModel):
    id: int
    question_id: int
    question_type: str
    question_text: str
    selected_option: Optional[str]
    text_answer: Optional[str]
    code_answer: Optional[str]
    awarded_marks: float
    max_marks: float
    is_correct: Optional[bool]
    response_status: Literal[
        "correct",
        "incorrect",
        "needs_review",
        "not_answered",
        "answer_key_missing",
    ]
    feedback: Optional[str]
    correct_answer: Optional[str] = None
    accepted_answers: Optional[str] = None
    explanation: Optional[str] = None
    hidden_test_cases: Optional[str] = None


class AssessmentAttemptOut(BaseModel):
    id: int
    student_id: int
    student_name: str
    student_email: str
    status: str
    can_publish_result: bool = False
    evaluation_remaining_count: int = 0
    score: float
    total_marks: float
    started_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    submitted_at: Optional[datetime]
    evaluated_at: Optional[datetime]
    published_at: Optional[datetime]
    auto_submit_reason: Optional[str] = None
    warning_count: int = 0
    last_warning_at: Optional[datetime] = None
    focus_status: Literal["clean", "warnings", "suspicious"] = "clean"
    responses: list[AssessmentTeacherResponseOut]


class AssessmentPublishSkippedAttempt(BaseModel):
    attempt_id: int
    student_name: str
    reason: str


class AssessmentBulkPublishSummary(BaseModel):
    published: int
    skipped: int
    skipped_attempts: list[AssessmentPublishSkippedAttempt] = Field(default_factory=list)


class AssessmentMarksUpdate(BaseModel):
    awarded_marks: float = Field(ge=0)
    feedback: Optional[str] = None
    is_correct: Optional[bool] = None


class AssessmentResponseMarksUpdate(AssessmentMarksUpdate):
    response_id: int


class AssessmentMarksBatchUpdate(BaseModel):
    responses: list[AssessmentResponseMarksUpdate] = Field(min_length=1)


class AnswerKeyImportSummary(BaseModel):
    imported: int
    updated: int
    marks_updated: int
    skipped: int
    missing_questions: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    total_answer_keys: int
    total_questions: int
    missing_answer_keys: int


class AssessmentResultResponse(BaseModel):
    question_id: int
    question_type: str
    question_text: str
    selected_option: Optional[str]
    text_answer: Optional[str]
    code_answer: Optional[str]
    correct_answer: Optional[str]
    accepted_answers: Optional[str]
    explanation: Optional[str]
    awarded_marks: float
    max_marks: float
    is_correct: Optional[bool]
    feedback: Optional[str]


class AssessmentResultOut(BaseModel):
    attempt_id: int
    assessment_id: int
    assessment_title: str
    status: str
    score: float
    total_marks: float
    submitted_at: datetime
    published_at: datetime
    responses: list[AssessmentResultResponse]


EmailRecipientMode = Literal[
    "all_students", "selected_students", "not_attempted_assessment",
    "pending_evaluation", "result_published", "below_score_threshold",
]


class EmailNotificationRequest(BaseModel):
    recipient_mode: EmailRecipientMode
    selected_student_ids: list[int] = Field(default_factory=list, max_length=100)
    assessment_id: Optional[int] = None
    below_score_threshold: Optional[float] = Field(default=None, ge=0, le=100)
    subject: str = Field(min_length=1, max_length=200)
    message_body: str = Field(min_length=1, max_length=20000)


class EmailNotificationRecipientPreview(BaseModel):
    user_id: int
    name: str
    email: str
    subject: str
    message_body: str


class EmailNotificationPreview(BaseModel):
    recipient_count: int
    recipients: list[EmailNotificationRecipientPreview]
    subject: str
    message_body: str


class EmailNotificationSendResult(BaseModel):
    notification_id: int
    recipient_count: int
    sent: int
    failed: int
    status: str
    error_message: Optional[str] = None


class ClassCodespaceOut(ORMModel):
    id: int
    classroom_id: int
    name: str
    description: Optional[str] = None
    created_at: datetime
    classroom_name: Optional[str] = None
    role: Optional[Literal["teacher", "student"]] = None


class CodespaceTeachingSummary(BaseModel):
    codespace_id: int
    classroom_id: int
    class_name: str
    codespace_name: str
    role: Literal["teacher"] = "teacher"
    total_tasks: int
    published_tasks: int
    pending_submissions: int


class CodespaceLearningSummary(BaseModel):
    codespace_id: int
    classroom_id: int
    class_name: str
    codespace_name: str
    role: Literal["student"] = "student"
    available_tasks: int
    submitted_tasks: int
    pending_feedback: int


class CodespacesIndexOut(BaseModel):
    teaching: list[CodespaceTeachingSummary] = Field(default_factory=list)
    learning: list[CodespaceLearningSummary] = Field(default_factory=list)


class CodingTaskInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    task_type: Literal["python", "web"] = "python"
    starter_code: Optional[str] = None
    starter_html: Optional[str] = None
    starter_css: Optional[str] = None
    starter_js: Optional[str] = None
    preview_enabled: bool = False
    expected_output: Optional[str] = None
    language: str = Field(default="python", max_length=40)
    question_id: Optional[str] = Field(default=None, max_length=100)
    unit_no: Optional[int] = None
    unit_title: Optional[str] = None
    assessment_title: Optional[str] = None
    difficulty: Optional[str] = Field(default=None, max_length=30)
    explanation: Optional[str] = None
    visible_test_cases: Optional[str] = None
    hidden_test_cases: Optional[str] = None
    tags: Optional[str] = None
    marks: int = Field(default=10, ge=0, le=1000)
    due_at: Optional[datetime] = None
    is_published: bool = False
    answer_key: Optional["CodingTaskAnswerKeyInput"] = None


class CodingTaskAnswerKeyInput(BaseModel):
    question_id: str
    correct_answer: Optional[str] = None
    accepted_answers: Optional[str] = None
    expected_output: Optional[str] = None
    evaluation_mode: str = Field(default="MANUAL", max_length=30)
    case_sensitive: bool = False
    visible_test_cases: Optional[str] = None
    hidden_test_cases: Optional[str] = None
    explanation: Optional[str] = None


class CodingTaskOut(ORMModel):
    id: int
    codespace_id: int
    title: str
    description: str
    task_type: str = "python"
    starter_code: Optional[str] = None
    starter_html: Optional[str] = None
    starter_css: Optional[str] = None
    starter_js: Optional[str] = None
    preview_enabled: bool = False
    expected_output: Optional[str] = None
    language: str = "python"
    question_id: Optional[str] = None
    unit_no: Optional[int] = None
    unit_title: Optional[str] = None
    assessment_title: Optional[str] = None
    difficulty: Optional[str] = None
    explanation: Optional[str] = None
    visible_test_cases: Optional[str] = None
    hidden_test_cases: Optional[str] = None
    tags: Optional[str] = None
    marks: int
    due_at: Optional[datetime] = None
    is_published: bool
    created_at: datetime
    submission_count: int = 0
    my_submission_status: Optional[str] = None
    my_submission_id: Optional[int] = None
    my_marks_awarded: Optional[int] = None
    my_feedback: Optional[str] = None
    my_code: Optional[str] = None
    my_html_code: Optional[str] = None
    my_css_code: Optional[str] = None
    my_js_code: Optional[str] = None
    my_evaluation_status: Optional[str] = None
    my_evaluation_feedback: Optional[str] = None
    answer_key_exists: bool = False


class CodingSubmissionInput(BaseModel):
    code: Optional[str] = Field(default=None, max_length=50000)
    html_code: Optional[str] = Field(default=None, max_length=50000)
    css_code: Optional[str] = Field(default=None, max_length=50000)
    js_code: Optional[str] = Field(default=None, max_length=50000)
    preview_snapshot: Optional[str] = Field(default=None, max_length=200000)
    output: Optional[str] = None


class CodingSubmissionEvaluate(BaseModel):
    marks_awarded: int = Field(ge=0, le=1000)
    feedback: Optional[str] = None


class CodingSubmissionOut(ORMModel):
    id: int
    task_id: int
    student_id: int
    code: str = ""
    html_code: Optional[str] = None
    css_code: Optional[str] = None
    js_code: Optional[str] = None
    preview_snapshot: Optional[str] = None
    output: Optional[str] = None
    status: str
    marks_awarded: Optional[int] = None
    auto_marks: Optional[int] = None
    final_marks: Optional[int] = None
    is_correct: Optional[bool] = None
    evaluation_status: str = "pending"
    evaluation_feedback: Optional[str] = None
    feedback: Optional[str] = None
    submitted_at: datetime
    evaluated_at: Optional[datetime] = None
    student_name: Optional[str] = None
    student_email: Optional[str] = None


class CodingSubmissionListOut(ORMModel):
    id: int
    task_id: int
    student_id: int
    status: str
    marks_awarded: Optional[int] = None
    auto_marks: Optional[int] = None
    final_marks: Optional[int] = None
    is_correct: Optional[bool] = None
    evaluation_status: str = "pending"
    evaluation_feedback: Optional[str] = None
    feedback: Optional[str] = None
    submitted_at: datetime
    evaluated_at: Optional[datetime] = None
    student_name: Optional[str] = None
    student_email: Optional[str] = None


class CodespaceImportSummary(BaseModel):
    imported_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    errors: list[str] = Field(default_factory=list)


class CodingAssessmentQuestionInput(BaseModel):
    question_id: Optional[str] = None
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1)
    starter_code: Optional[str] = None
    starter_html: Optional[str] = None
    starter_css: Optional[str] = None
    starter_js: Optional[str] = None
    expected_output: Optional[str] = None
    visible_test_cases: Optional[str] = None
    hidden_test_cases: Optional[str] = None
    marks: int = Field(default=10, ge=0, le=1000)


class CodingAssessmentInput(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = ""
    task_type: Literal["python", "web"] = "python"
    due_at: Optional[datetime] = None
    is_published: bool = False
    questions: list[CodingAssessmentQuestionInput] = Field(min_length=1)
    answer_keys: list[CodingTaskAnswerKeyInput] = Field(default_factory=list)


class CodingAssessmentQuestionOut(ORMModel):
    id: int
    assessment_id: int
    question_id: Optional[str] = None
    title: str
    description: str
    starter_code: Optional[str] = None
    starter_html: Optional[str] = None
    starter_css: Optional[str] = None
    starter_js: Optional[str] = None
    expected_output: Optional[str] = None
    visible_test_cases: Optional[str] = None
    hidden_test_cases: Optional[str] = None
    marks: int
    sort_order: int


class CodingAssessmentOut(ORMModel):
    id: int
    codespace_id: int
    title: str
    description: Optional[str] = None
    task_type: str = "python"
    total_marks: int
    due_at: Optional[datetime] = None
    is_published: bool
    created_at: datetime
    question_count: int = 0
    submission_count: int = 0
    my_submission_status: Optional[str] = None
    my_submission_id: Optional[int] = None
    my_marks_awarded: Optional[int] = None
    questions: list[CodingAssessmentQuestionOut] = Field(default_factory=list)


class CodingAssessmentAnswerInput(BaseModel):
    question_id: int
    code: Optional[str] = Field(default=None, max_length=50000)
    html_code: Optional[str] = Field(default=None, max_length=50000)
    css_code: Optional[str] = Field(default=None, max_length=50000)
    js_code: Optional[str] = Field(default=None, max_length=50000)
    output: Optional[str] = None


class CodingAssessmentSubmitInput(BaseModel):
    answers: list[CodingAssessmentAnswerInput] = Field(min_length=1)

    @model_validator(mode="after")
    def reject_duplicate_questions(self):
        question_ids = [answer.question_id for answer in self.answers]
        if len(question_ids) != len(set(question_ids)):
            raise ValueError("Each question may only be answered once")
        return self


class CodingAssessmentAnswerOut(ORMModel):
    id: int
    submission_id: int
    question_id: int
    code: Optional[str] = None
    html_code: Optional[str] = None
    css_code: Optional[str] = None
    js_code: Optional[str] = None
    output: Optional[str] = None
    marks_awarded: int = 0
    feedback: Optional[str] = None
    evaluation_status: str = "needs_review"
    question: Optional[CodingAssessmentQuestionOut] = None


class CodingAssessmentSubmissionOut(ORMModel):
    id: int
    assessment_id: int
    student_id: int
    status: str
    total_marks_awarded: int = 0
    feedback: Optional[str] = None
    submitted_at: datetime
    evaluated_at: Optional[datetime] = None
    student_name: Optional[str] = None
    student_email: Optional[str] = None
    answers: list[CodingAssessmentAnswerOut] = Field(default_factory=list)


class CodingAssessmentAnswerEvaluate(BaseModel):
    marks_awarded: int = Field(ge=0, le=1000)
    feedback: Optional[str] = None


class CodingAssessmentFinalizeInput(BaseModel):
    feedback: Optional[str] = None
