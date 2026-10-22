from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class RecruiterContact(Base):
    """
    Stores discovered recruiter or hiring manager contact details for a company or job.
    Includes traceable source URL, discovery timestamp, and strict verification status.
    """
    __tablename__ = "recruiter_contacts"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("job_listings.id", ondelete="CASCADE"), nullable=True, index=True)
    company = Column(String, index=True, nullable=False)
    
    # Contact information
    name = Column(String, nullable=True)  # e.g., "Sarah Jenkins" or "Engineering Talent Team"
    email = Column(String, nullable=True)  # e.g., "sarah.j@company.com" or "careers@company.com"
    role = Column(String, nullable=True)  # e.g., "Technical Recruiter", "Talent Acquisition", "Careers Desk"
    
    # Source provenance & verification
    source_url = Column(String, nullable=False)  # Permitted public source URL where contact was found
    source_type = Column(String, default="job_posting")  # "job_posting", "careers_page", "inferred_domain"
    
    # Verification status:
    # - "VERIFIED": Explicitly listed in the official job posting or company contacts page
    # - "INFERRED": Derived from official company domain pattern (e.g. careers@company.com); requires user verification
    # - "NOT_FOUND": No direct public email discovered; user advised to apply through official portal
    # - "USER_VERIFIED": Manually reviewed and verified or updated by the user
    verification_status = Column(String, default="INFERRED", index=True)
    confidence_score = Column(Float, default=0.5)  # 1.0 for explicit posting email, 0.4 for domain inference
    notes = Column(Text, nullable=True)
    
    discovered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    job = relationship("JobListing", backref="discovered_contacts")


class JobApplicationWorkspace(Base):
    """
    User-specific workspace for a selected job application.
    Holds the personalized cover letter draft, recruiter outreach email,
    selected contact, and approval workflow status.
    """
    __tablename__ = "application_workspaces"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("job_listings.id", ondelete="CASCADE"), nullable=False, index=True)

    # Workflow status:
    # "draft" -> Initial draft generated or in progress
    # "reviewed" -> User reviewed and customized the draft
    # "ready_for_apply" -> Approved by user, ready for submission in Module 4
    # "skipped" -> User opted not to proceed with this application
    status = Column(String, default="draft", index=True)

    # 1. Cover letter draft details
    include_cover_letter = Column(Boolean, default=True)  # Optional if company doesn't request one
    cover_letter_content = Column(Text, nullable=True)
    cover_letter_tone = Column(String, default="professional")  # "professional", "enthusiastic", "concise", "technical"
    cover_letter_template = Column(String, default="modern")  # "modern", "standard", "minimal"
    cover_letter_updated_at = Column(DateTime, nullable=True)

    # 2. Recruiter contact information (active for this application)
    contact_name = Column(String, nullable=True)
    contact_email = Column(String, nullable=True)
    contact_role = Column(String, nullable=True)
    contact_source_url = Column(String, nullable=True)
    contact_verification_status = Column(String, default="INFERRED")  # "VERIFIED", "INFERRED", "NOT_FOUND", "USER_VERIFIED"
    contact_notes = Column(Text, nullable=True)
    contact_discovered_at = Column(DateTime, nullable=True)

    # 3. Recruiter email draft details
    email_subject = Column(String, nullable=True)
    email_body = Column(Text, nullable=True)
    email_tone = Column(String, default="concise")  # "concise", "formal", "warm"
    email_updated_at = Column(DateTime, nullable=True)

    # 4. Anti-spam & Duplicate outreach tracking
    is_duplicate_outreach = Column(Boolean, default=False)
    duplicate_warning = Column(Text, nullable=True)

    # 5. Module 4: Consent-Based Submission & Tracking
    application_destination = Column(String, default="manual_portal")  # "manual_portal", "email_recruiter", "direct_api"
    application_status = Column(String, default="not_started", index=True)  # "not_started", "pending", "in_progress", "submitted", "failed", "requires_user_action", "cancelled", "status_unknown"
    application_confirmation_id = Column(String, nullable=True)
    application_confirmation_message = Column(Text, nullable=True)
    application_submitted_at = Column(DateTime, nullable=True)
    application_error = Column(Text, nullable=True)

    email_outreach_status = Column(String, default="not_started", index=True)  # "not_started", "pending", "sent", "failed", "not_configured", "skipped", "cancelled"
    email_sent_at = Column(DateTime, nullable=True)
    email_error = Column(Text, nullable=True)

    screening_answers = Column(Text, default="{}")  # JSON dictionary of user-confirmed screening questions
    idempotency_key = Column(String, nullable=True, index=True)
    user_consent_granted = Column(Boolean, default=False)
    consent_timestamp = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_user_job_application_workspace"),
    )

    user = relationship("User", backref="application_workspaces")
    job = relationship("JobListing", backref="application_workspaces")


class ApplicationAuditLog(Base):
    """
    Append-only audit trail recording user consent, application attempts,
    email sends, and automated/manual outcomes.
    """
    __tablename__ = "application_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("job_listings.id", ondelete="CASCADE"), nullable=True, index=True)
    workspace_id = Column(Integer, ForeignKey("application_workspaces.id", ondelete="CASCADE"), nullable=True)
    
    action = Column(String, index=True, nullable=False)  # "consent_granted", "portal_apply_attempt", "portal_apply_success", "portal_apply_failed", "requires_user_action", "email_sent", "email_failed", "manual_redirect", "batch_cancelled"
    status = Column(String, nullable=False)  # "success", "failed", "requires_user_action", "cancelled", "not_configured"
    destination = Column(String, nullable=True)
    recipient = Column(String, nullable=True)
    details = Column(Text, nullable=True)
    idempotency_key = Column(String, index=True, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", backref="application_audit_logs")
    job = relationship("JobListing", backref="audit_logs")


class BatchApplicationSession(Base):
    """
    Tracks state and progress of an active or completed batch application run.
    Provides cancellation controls for in-flight tasks.
    """
    __tablename__ = "batch_application_sessions"

    id = Column(String, primary_key=True, index=True)  # UUID
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    total_jobs = Column(Integer, default=0)
    processed_jobs = Column(Integer, default=0)
    successful_jobs = Column(Integer, default=0)
    failed_jobs = Column(Integer, default=0)
    requires_action_jobs = Column(Integer, default=0)
    
    status = Column(String, default="in_progress", index=True)  # "in_progress", "completed", "cancelled"
    cancelled = Column(Boolean, default=False)
    current_job_id = Column(Integer, nullable=True)
    summary_log = Column(Text, default="[]")  # JSON list of outcomes

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", backref="batch_sessions")
