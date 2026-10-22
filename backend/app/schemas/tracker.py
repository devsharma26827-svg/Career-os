from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from app.schemas.application import AuditLogResponseItem, BatchSessionResponse


class TrackedApplicationItem(BaseModel):
    id: int
    job_id: int
    job_title: str
    company: str
    location: str
    source_name: str
    job_url: str
    destination_type: str
    application_status: str
    application_confirmation_id: Optional[str] = None
    application_message: Optional[str] = None
    has_cover_letter: bool = False
    cover_letter_preview: Optional[str] = None
    has_email_draft: bool = False
    email_outreach_status: str = "not_started"
    recruiter_email: Optional[str] = None
    screening_confirmed: bool = False
    can_retry: bool = False
    applied_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class TrackerResponse(BaseModel):
    total: int
    submitted_count: int
    requires_action_count: int
    failed_count: int
    items: List[TrackedApplicationItem]


class FirstTimeProgress(BaseModel):
    has_resume: bool
    has_location_pref: bool
    has_found_jobs: bool
    has_prepared_content: bool
    has_applied: bool
    current_step: int  # 1 to 5
    percentage: int  # 0 to 100


class DashboardSummaryResponse(BaseModel):
    jobs_discovered: int
    saved_jobs_count: int
    queued_jobs_count: int
    submitted_count: int
    action_required_count: int
    failed_count: int
    emails_sent_count: int
    recent_activity: List[AuditLogResponseItem]
    latest_updates: List[TrackedApplicationItem]
    first_time_progress: FirstTimeProgress
    active_batch_session: Optional[BatchSessionResponse] = None
