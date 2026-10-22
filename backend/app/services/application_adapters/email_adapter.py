import uuid
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from app.models.application import JobApplicationWorkspace
from app.models.job import JobListing
from app.models.resume import Resume
from app.models.user import User
from app.services.application_adapters.base import ApplicationResult, BaseApplicationAdapter
from app.services.email_service import EmailDeliveryService


class EmailApplicationAdapter(BaseApplicationAdapter):
    """
    Adapter for employers whose official application method is email
    (e.g., job postings requesting resumes sent directly to careers@company.com).
    """
    name = "email_application"

    def can_handle(self, job: JobListing, workspace: JobApplicationWorkspace) -> bool:
        # Applies when contact email is explicitly VERIFIED from posting
        # and job description indicates an email application destination
        desc = (job.description or "").lower()
        has_email_phrase = any(
            phrase in desc for phrase in [
                "send your resume", "send resume to", "email your resume",
                "apply by emailing", "send cv to", "submit your application to"
            ]
        )
        has_verified_email = (
            workspace.contact_email
            and workspace.contact_verification_status in ["VERIFIED", "USER_VERIFIED"]
        )
        return bool(has_email_phrase and has_verified_email)

    async def submit(
        self,
        job: JobListing,
        workspace: JobApplicationWorkspace,
        user: User,
        resume: Optional[Resume],
        screening_answers: Dict[str, Any],
        db: Session
    ) -> ApplicationResult:
        if not workspace.contact_email:
            return ApplicationResult(
                status="failed",
                confirmation_id=None,
                confirmation_message="Missing recipient email address.",
                error_message="Official application email was not found."
            )

        subject = (
            workspace.email_subject
            or f"Application: {job.title} - {user.full_name or user.email}"
        )
        
        # Build comprehensive application body
        body = workspace.email_body or ""
        if workspace.include_cover_letter and workspace.cover_letter_content:
            body += f"\n\n--- COVER LETTER ---\n\n{workspace.cover_letter_content}"

        if screening_answers:
            answers_summary = "\n\n--- APPLICATION SCREENING DETAILS ---"
            if screening_answers.get("work_authorization"):
                answers_summary += f"\n• Work Authorization: {screening_answers['work_authorization']}"
            if screening_answers.get("years_of_experience"):
                answers_summary += f"\n• Years of Experience: {screening_answers['years_of_experience']}"
            if screening_answers.get("earliest_start_date"):
                answers_summary += f"\n• Earliest Start Date: {screening_answers['earliest_start_date']}"
            if screening_answers.get("salary_expectation"):
                answers_summary += f"\n• Salary Expectation: {screening_answers['salary_expectation']}"
            body += answers_summary

        if resume:
            body += f"\n\n[Resume Document: {resume.original_filename} attached on profile]"

        # Send via email delivery service
        res = EmailDeliveryService.send_email(
            db=db,
            user_id=user.id,
            job_id=job.id,
            workspace_id=workspace.id,
            recipient_email=workspace.contact_email,
            subject=subject,
            body=body,
            idempotency_key=workspace.idempotency_key
        )

        if res["status"] == "sent":
            conf_code = f"EMAIL-APP-{uuid.uuid4().hex[:6].upper()}"
            return ApplicationResult(
                status="submitted",
                confirmation_id=conf_code,
                confirmation_message=f"Application successfully delivered to {workspace.contact_email}.",
                error_message=None
            )
        elif res["status"] == "not_configured":
            return ApplicationResult(
                status="requires_user_action",
                confirmation_id=None,
                confirmation_message="SMTP sending not configured. Copy application email manually.",
                manual_action_url=f"mailto:{workspace.contact_email}?subject={subject}",
                manual_action_guide={
                    "recipient": workspace.contact_email,
                    "subject": subject,
                    "body": body,
                    "instructions": "Open your email client and paste the prepared application."
                },
                error_message="SMTP not configured on server."
            )
        else:
            return ApplicationResult(
                status="failed",
                confirmation_id=None,
                confirmation_message=res["message"],
                error_message=res.get("error")
            )
