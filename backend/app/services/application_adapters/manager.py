import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.models.application import ApplicationAuditLog, JobApplicationWorkspace
from app.models.job import JobListing
from app.models.resume import Resume
from app.models.user import User
from app.schemas.application import ApplyExecutionResult
from app.services.application_adapters.base import ApplicationResult, BaseApplicationAdapter
from app.services.application_adapters.direct_api_adapter import DirectApiApplicationAdapter
from app.services.application_adapters.email_adapter import EmailApplicationAdapter
from app.services.application_adapters.manual_portal_adapter import ManualPortalRedirectAdapter
from app.services.email_service import EmailDeliveryService

logger = logging.getLogger(__name__)


class ApplicationAdapterManager:
    """
    Coordinates application submission across supported adapters.
    Ensures idempotency, audit trail recording, and reliable confirmation tracking.
    """
    _adapters: List[BaseApplicationAdapter] = [
        DirectApiApplicationAdapter(),
        EmailApplicationAdapter(),
        ManualPortalRedirectAdapter(),  # Fallback
    ]

    @classmethod
    def get_adapter(cls, job: JobListing, workspace: JobApplicationWorkspace) -> BaseApplicationAdapter:
        for adapter in cls._adapters:
            if adapter.can_handle(job, workspace):
                return adapter
        return cls._adapters[-1]

    @classmethod
    def determine_destination_type(cls, job: JobListing, workspace: JobApplicationWorkspace) -> str:
        adapter = cls.get_adapter(job, workspace)
        return adapter.name

    @classmethod
    async def execute_application(
        cls,
        db: Session,
        user: User,
        job: JobListing,
        workspace: JobApplicationWorkspace,
        submit_portal: bool,
        send_email: bool,
        screening_answers: Dict[str, Any],
        idempotency_key: Optional[str] = None
    ) -> ApplyExecutionResult:
        # Fetch active user resume
        resume = (
            db.query(Resume)
            .filter(Resume.user_id == user.id, Resume.is_active == True)
            .first()
        )

        app_result: Optional[ApplicationResult] = None
        email_status = "skipped"
        email_message: Optional[str] = None
        email_error: Optional[str] = None

        # 1. Idempotency Check: prevent duplicate submissions with same token
        if idempotency_key and workspace.idempotency_key == idempotency_key and workspace.application_status == "submitted":
            return ApplyExecutionResult(
                job_id=job.id,
                title=job.title,
                company=job.company,
                application_status="submitted",
                application_confirmation_id=workspace.application_confirmation_id,
                application_message="Idempotent replay: Application was already confirmed submitted.",
                manual_action_url=None,
                manual_action_guide=None,
                email_status=workspace.email_outreach_status,
                email_message="Email was already processed.",
                error_message=None
            )

        # 2. Duplicate Prevention: never duplicate already submitted applications
        if workspace.application_status == "submitted":
            submitted_date_str = workspace.application_submitted_at.strftime("%Y-%m-%d") if workspace.application_submitted_at else "earlier"
            return ApplyExecutionResult(
                job_id=job.id,
                title=job.title,
                company=job.company,
                application_status="submitted",
                application_confirmation_id=workspace.application_confirmation_id,
                application_message=f"Application already confirmed submitted ({submitted_date_str}). Skipped duplicate submission.",
                manual_action_url=None,
                manual_action_guide=None,
                email_status=workspace.email_outreach_status,
                email_message="Recruiter outreach already processed.",
                error_message=None
            )

        workspace.idempotency_key = idempotency_key
        workspace.user_consent_granted = True
        workspace.consent_timestamp = datetime.now(timezone.utc)
        workspace.screening_answers = json.dumps(screening_answers)

        # Log consent granted
        cls._log_audit(
            db=db,
            user_id=user.id,
            job_id=job.id,
            workspace_id=workspace.id,
            action="consent_granted",
            status="success",
            destination=cls.determine_destination_type(job, workspace),
            details=f"User authorized application: submit_portal={submit_portal}, send_email={send_email}",
            idempotency_key=idempotency_key
        )

        # 2. Portal / Destination Application
        if submit_portal:
            adapter = cls.get_adapter(job, workspace)
            workspace.application_destination = adapter.name
            workspace.application_status = "in_progress"
            db.commit()

            try:
                app_result = await adapter.submit(
                    job=job,
                    workspace=workspace,
                    user=user,
                    resume=resume,
                    screening_answers=screening_answers,
                    db=db
                )
            except Exception as e:
                logger.error("Adapter %s failed on job %s: %s", adapter.name, job.id, e)
                app_result = ApplicationResult(
                    status="failed",
                    confirmation_id=None,
                    confirmation_message="Unexpected system error during application execution.",
                    error_message=str(e)
                )

            # Update workspace
            workspace.application_status = app_result.status
            workspace.application_confirmation_id = app_result.confirmation_id
            workspace.application_confirmation_message = app_result.confirmation_message
            workspace.application_error = app_result.error_message
            if app_result.status == "submitted":
                workspace.application_submitted_at = datetime.now(timezone.utc)

            # Log audit
            cls._log_audit(
                db=db,
                user_id=user.id,
                job_id=job.id,
                workspace_id=workspace.id,
                action=f"apply_{app_result.status}",
                status=app_result.status,
                destination=adapter.name,
                details=app_result.confirmation_message,
                idempotency_key=idempotency_key
            )
        else:
            workspace.application_status = "skipped"

        # 3. Recruiter Outreach Email (Separately selectable action)
        if send_email and workspace.contact_email:
            workspace.email_outreach_status = "in_progress"
            db.commit()

            email_res = EmailDeliveryService.send_email(
                db=db,
                user_id=user.id,
                job_id=job.id,
                workspace_id=workspace.id,
                recipient_email=workspace.contact_email,
                subject=workspace.email_subject or f"Application: {job.title} - {user.full_name or user.email}",
                body=workspace.email_body or "",
                idempotency_key=idempotency_key
            )

            email_status = email_res["status"]
            email_message = email_res["message"]
            email_error = email_res.get("error")

            workspace.email_outreach_status = email_status
            workspace.email_error = email_error
            if email_status == "sent":
                workspace.email_sent_at = datetime.now(timezone.utc)
        elif send_email and not workspace.contact_email:
            email_status = "failed"
            email_message = "No recruiter contact email available."
            workspace.email_outreach_status = "failed"
            workspace.email_error = email_message

        # Commit final state
        db.commit()
        db.refresh(workspace)

        return ApplyExecutionResult(
            job_id=job.id,
            title=job.title,
            company=job.company,
            application_status=workspace.application_status,
            application_confirmation_id=workspace.application_confirmation_id,
            application_message=workspace.application_confirmation_message or (
                "Application skipped by user selection." if not submit_portal else "Processed."
            ),
            manual_action_url=app_result.manual_action_url if app_result else None,
            manual_action_guide=app_result.manual_action_guide if app_result else None,
            email_status=email_status,
            email_message=email_message,
            error_message=workspace.application_error or email_error
        )

    @classmethod
    def _log_audit(
        cls,
        db: Session,
        user_id: int,
        job_id: Optional[int],
        workspace_id: Optional[int],
        action: str,
        status: str,
        destination: Optional[str],
        details: Optional[str],
        idempotency_key: Optional[str]
    ):
        log = ApplicationAuditLog(
            user_id=user_id,
            job_id=job_id,
            workspace_id=workspace_id,
            action=action,
            status=status,
            destination=destination,
            details=details,
            idempotency_key=idempotency_key,
            created_at=datetime.now(timezone.utc)
        )
        db.add(log)
        db.commit()
