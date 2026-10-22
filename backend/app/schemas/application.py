from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class RecruiterContactBase(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    source_url: str
    source_type: str = "job_posting"
    verification_status: str = "INFERRED"
    confidence_score: float = 0.5
    notes: Optional[str] = None


class RecruiterContactResponse(RecruiterContactBase):
    id: int
    job_id: Optional[int] = None
    company: str
    discovered_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CoverLetterGenerateRequest(BaseModel):
    tone: str = Field(default="professional", description="'professional', 'enthusiastic', 'concise', or 'technical'")
    template_style: str = Field(default="modern", description="'modern', 'standard', or 'minimal'")


class CoverLetterUpdateRequest(BaseModel):
    content: str
    tone: Optional[str] = None
    template_style: Optional[str] = None
    include_cover_letter: Optional[bool] = None


class RecruiterEmailGenerateRequest(BaseModel):
    tone: str = Field(default="concise", description="'concise', 'formal', or 'warm'")


class RecruiterEmailUpdateRequest(BaseModel):
    subject: str
    body: str
    tone: Optional[str] = None


class ContactUpdateRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    verification_status: Optional[str] = None
    notes: Optional[str] = None


class ApplicationStatusUpdateRequest(BaseModel):
    status: str = Field(description="'draft', 'reviewed', 'ready_for_apply', or 'skipped'")


class ApplicationWorkspaceResponse(BaseModel):
    id: int
    job_id: int
    job_title: str
    job_company: str
    job_location: str
    job_url: str
    job_source: str
    job_description: str
    status: str  # 'draft', 'reviewed', 'ready_for_apply', 'skipped'

    # Cover letter
    include_cover_letter: bool = True
    cover_letter_content: Optional[str] = None
    cover_letter_tone: str = "professional"
    cover_letter_template: str = "modern"
    cover_letter_updated_at: Optional[datetime] = None

    # Recruiter contact
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_role: Optional[str] = None
    contact_source_url: Optional[str] = None
    contact_verification_status: str = "INFERRED"
    contact_discovered_at: Optional[datetime] = None
    contact_notes: Optional[str] = None

    # Recruiter email draft
    email_subject: Optional[str] = None
    email_body: Optional[str] = None
    email_tone: str = "concise"
    email_updated_at: Optional[datetime] = None

    # Anti-spam & duplicate outreach tracking
    is_duplicate_outreach: bool = False
    duplicate_warning: Optional[str] = None

    # Module 4 Submission & Email Tracking
    application_destination: str = "manual_portal"
    application_status: str = "not_started"
    application_confirmation_id: Optional[str] = None
    application_confirmation_message: Optional[str] = None
    application_submitted_at: Optional[datetime] = None
    application_error: Optional[str] = None

    email_outreach_status: str = "not_started"
    email_sent_at: Optional[datetime] = None
    email_error: Optional[str] = None

    screening_answers: Optional[dict] = None
    user_consent_granted: bool = False
    consent_timestamp: Optional[datetime] = None

    # Honest heuristic disclaimer
    disclaimer: str = (
        "Personalized application content is generated from your verified resume profile to highlight your genuine qualifications. "
        "A customized cover letter or outreach note does not guarantee hiring selection. "
        "Always review contact information before reaching out."
    )

    model_config = ConfigDict(from_attributes=True)


class ApplicationQueueItem(BaseModel):
    job_id: int
    workspace_id: Optional[int] = None
    title: str
    company: str
    location: str
    source_name: str
    url: str
    status: str = "draft"  # 'draft', 'reviewed', 'ready_for_apply', 'skipped'
    has_cover_letter: bool = False
    has_email_draft: bool = False
    contact_verification_status: str = "NOT_FOUND"
    contact_email: Optional[str] = None
    application_status: str = "not_started"
    email_outreach_status: str = "not_started"
    saved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ApplicationQueueResponse(BaseModel):
    total_queued: int
    draft_count: int
    reviewed_count: int
    ready_for_apply_count: int
    submitted_count: int = 0
    items: List[ApplicationQueueItem]


# Module 4: Screening Answers & Explicit Consent Schemas
class ScreeningAnswers(BaseModel):
    work_authorization: Optional[str] = Field(
        default=None,
        description="e.g. 'Authorized to work in US/country without sponsorship' or 'Requires visa sponsorship'"
    )
    years_of_experience: Optional[int] = Field(
        default=None,
        description="Total relevant years of experience"
    )
    earliest_start_date: Optional[str] = Field(
        default="Immediately",
        description="e.g. 'Immediately', '2 weeks notice', or specific date"
    )
    salary_expectation: Optional[str] = Field(
        default=None,
        description="e.g. '$120,000 / year' or 'Negotiable'"
    )
    willing_to_relocate: Optional[bool] = Field(
        default=None,
        description="Whether candidate is willing to relocate"
    )
    confirmed_by_user: bool = Field(
        default=False,
        description="Must be explicitly confirmed by user. Never invent personal facts."
    )


class SingleApplyRequest(BaseModel):
    job_id: int
    submit_portal: bool = Field(default=True, description="Whether to submit application to portal / destination")
    send_email: bool = Field(default=False, description="Whether to send recruiter email outreach")
    screening_answers: Optional[ScreeningAnswers] = None
    idempotency_key: Optional[str] = None
    user_consent_granted: bool = Field(..., description="Must explicitly be True. Applications will not run without authorization.")


class BatchApplyRequest(BaseModel):
    job_ids: List[int] = Field(..., min_length=1, description="List of job IDs to apply to")
    submit_portal: bool = Field(default=True, description="Whether to submit applications to portal / destinations")
    send_email: bool = Field(default=False, description="Whether to send recruiter email outreach")
    email_job_ids: Optional[List[int]] = Field(default=None, description="Specific job IDs to send recruiter email outreach to")
    screening_answers: Optional[ScreeningAnswers] = None
    idempotency_key: Optional[str] = None
    user_consent_granted: bool = Field(..., description="Must explicitly be True. Batch will not run without authorization.")


class ApplicationReviewItem(BaseModel):
    job_id: int
    workspace_id: int
    title: str
    company: str
    location: str
    source_name: str
    url: str
    destination_type: str  # "email_recruiter", "direct_api", "manual_portal"

    # Documents & Prepared Content
    resume_name: Optional[str] = None
    resume_id: Optional[int] = None
    resume_attached: bool = False

    cover_letter_included: bool = True
    cover_letter_preview: Optional[str] = None
    cover_letter_word_count: int = 0

    recruiter_name: Optional[str] = None
    recruiter_email: Optional[str] = None
    recruiter_email_preview: Optional[str] = None
    email_verification_status: str = "NOT_FOUND"

    screening_answers: ScreeningAnswers
    missing_required_info: List[str] = []
    ready_to_submit: bool = False

    application_status: str = "not_started"
    email_outreach_status: str = "not_started"
    application_confirmation_id: Optional[str] = None
    application_message: Optional[str] = None


class ApplicationReviewCenterResponse(BaseModel):
    total_selected: int
    ready_count: int
    missing_info_count: int
    items: List[ApplicationReviewItem]
    global_missing_info: List[str] = []


class ApplyExecutionResult(BaseModel):
    job_id: int
    title: str
    company: str
    application_status: str  # "submitted", "requires_user_action", "failed", "status_unknown", "skipped"
    application_confirmation_id: Optional[str] = None
    application_message: str
    manual_action_url: Optional[str] = None
    manual_action_guide: Optional[dict] = None

    email_status: str  # "sent", "not_configured", "failed", "skipped", "duplicate_prevented"
    email_message: Optional[str] = None
    error_message: Optional[str] = None


class BatchSessionResponse(BaseModel):
    session_id: str
    total_jobs: int
    processed_jobs: int
    successful_jobs: int
    failed_jobs: int
    requires_action_jobs: int
    status: str  # "in_progress", "completed", "cancelled"
    cancelled: bool = False
    current_job_id: Optional[int] = None
    summary_log: List[ApplyExecutionResult] = []


class AuditLogResponseItem(BaseModel):
    id: int
    job_id: Optional[int] = None
    job_title: Optional[str] = None
    job_company: Optional[str] = None
    action: str
    status: str
    destination: Optional[str] = None
    recipient: Optional[str] = None
    details: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

