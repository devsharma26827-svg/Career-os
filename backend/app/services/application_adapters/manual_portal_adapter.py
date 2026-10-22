from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from app.models.application import JobApplicationWorkspace
from app.models.job import JobListing
from app.models.resume import Resume
from app.models.user import User
from app.services.application_adapters.base import ApplicationResult, BaseApplicationAdapter


class ManualPortalRedirectAdapter(BaseApplicationAdapter):
    """
    Adapter for employers whose destination is an external web portal,
    ATS (Workday, Greenhouse, Lever, etc.), or site requiring user login / CAPTCHA.
    
    Strictly complies with terms:
    - Never bypasses platform security, logins, or CAPTCHA restrictions.
    - Returns 'requires_user_action'.
    - Provides a comprehensive, pre-formatted Application Kit with pre-filled answers
      so the user can complete the submission manually in 60 seconds.
    """
    name = "manual_portal"

    def can_handle(self, job: JobListing, workspace: JobApplicationWorkspace) -> bool:
        # Default fallback for all web portal job listings
        return True

    async def submit(
        self,
        job: JobListing,
        workspace: JobApplicationWorkspace,
        user: User,
        resume: Optional[Resume],
        screening_answers: Dict[str, Any],
        db: Session
    ) -> ApplicationResult:
        portal_url = job.url or ""

        # Pre-package a 1-click Application Kit to assist the user
        kit = {
            "portal_url": portal_url,
            "company": job.company,
            "title": job.title,
            "candidate_name": user.full_name or user.email,
            "candidate_email": user.email,
            "work_authorization": screening_answers.get("work_authorization") or "Confirmed by candidate",
            "years_of_experience": screening_answers.get("years_of_experience") or "Listed in verified resume",
            "earliest_start_date": screening_answers.get("earliest_start_date") or "Immediately",
            "salary_expectation": screening_answers.get("salary_expectation") or "Negotiable / market rate",
            "cover_letter": workspace.cover_letter_content if workspace.include_cover_letter else None,
            "resume_filename": resume.original_filename if resume else None,
            "resume_download_url": "/api/v1/resume/download" if resume else None,
            "instructions": (
                f"{job.company} uses an external career portal that requires manual login or security verification. "
                "JobPulse AI does not bypass security or CAPTCHAs. "
                "Open the employer portal link, copy your prepared responses below, and click 'Mark as Submitted' once completed."
            )
        }

        return ApplicationResult(
            status="requires_user_action",
            confirmation_id=None,
            confirmation_message=(
                f"Portal requires user completion. Prepared Application Kit for {job.company}."
            ),
            manual_action_url=portal_url,
            manual_action_guide=kit,
            error_message=None
        )
