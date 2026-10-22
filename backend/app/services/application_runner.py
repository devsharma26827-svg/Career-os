import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.application import BatchApplicationSession, JobApplicationWorkspace
from app.models.job import JobListing
from app.models.user import User
from app.schemas.application import ApplyExecutionResult, BatchSessionResponse
from app.services.application_adapters.manager import ApplicationAdapterManager

logger = logging.getLogger(__name__)


class ApplicationRunnerService:
    """
    Manages background batch runs, cancellation controls, and progress tracking
    for consent-based applications.
    """

    @classmethod
    def create_batch_session(cls, db: Session, user_id: int, total_jobs: int) -> BatchApplicationSession:
        session = BatchApplicationSession(
            id=str(uuid.uuid4()),
            user_id=user_id,
            total_jobs=total_jobs,
            processed_jobs=0,
            successful_jobs=0,
            failed_jobs=0,
            requires_action_jobs=0,
            status="in_progress",
            cancelled=False,
            summary_log="[]",
            created_at=datetime.now(timezone.utc)
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    @classmethod
    def cancel_batch_session(cls, db: Session, session_id: str, user_id: int) -> bool:
        session = (
            db.query(BatchApplicationSession)
            .filter(BatchApplicationSession.id == session_id, BatchApplicationSession.user_id == user_id)
            .first()
        )
        if not session:
            return False

        session.cancelled = True
        session.status = "cancelled"
        session.updated_at = datetime.now(timezone.utc)
        db.commit()
        return True

    @classmethod
    def get_batch_session(cls, db: Session, session_id: str, user_id: int) -> Optional[BatchSessionResponse]:
        session = (
            db.query(BatchApplicationSession)
            .filter(BatchApplicationSession.id == session_id, BatchApplicationSession.user_id == user_id)
            .first()
        )
        if not session:
            return None

        summary_list = []
        try:
            raw_summary = json.loads(session.summary_log or "[]")
            summary_list = [ApplyExecutionResult(**item) for item in raw_summary]
        except Exception:
            pass

        return BatchSessionResponse(
            session_id=session.id,
            total_jobs=session.total_jobs,
            processed_jobs=session.processed_jobs,
            successful_jobs=session.successful_jobs,
            failed_jobs=session.failed_jobs,
            requires_action_jobs=session.requires_action_jobs,
            status=session.status,
            cancelled=session.cancelled,
            current_job_id=session.current_job_id,
            summary_log=summary_list
        )

    @classmethod
    async def run_batch_process(
        cls,
        session_id: str,
        user_id: int,
        job_ids: List[int],
        submit_portal: bool,
        send_email: bool,
        screening_answers: Dict[str, Any],
        idempotency_key: Optional[str],
        email_job_ids: Optional[List[int]] = None,
        db: Optional[Session] = None
    ):
        """
        Processes jobs in batch. Checks cancellation state before each job.
        Runs safely in background or inline with rate-limiting between jobs.
        """
        db_created = False
        if db is None:
            db = SessionLocal()
            db_created = True

        try:
            session = (
                db.query(BatchApplicationSession)
                .filter(BatchApplicationSession.id == session_id)
                .first()
            )
            user = db.query(User).filter(User.id == user_id).first()
            if not session or not user:
                return

            results: List[Dict[str, Any]] = []

            for idx, job_id in enumerate(job_ids):
                # Rate limiting delay between subsequent applications (except first)
                if idx > 0:
                    await asyncio.sleep(0.3)

                # Check for cancellation before executing each job
                db.refresh(session)
                if session.cancelled:
                    logger.info("Batch session %s cancelled by user. Halting remaining jobs.", session_id)
                    session.status = "cancelled"
                    db.commit()
                    break

                session.current_job_id = job_id
                db.commit()

                job = db.query(JobListing).filter(JobListing.id == job_id).first()
                if not job:
                    continue

                workspace = (
                    db.query(JobApplicationWorkspace)
                    .filter(
                        JobApplicationWorkspace.user_id == user.id,
                        JobApplicationWorkspace.job_id == job.id
                    )
                    .first()
                )
                if not workspace:
                    from app.services.contact_discovery import ContactDiscoveryService
                    contact = ContactDiscoveryService.discover_contact_for_job(job)
                    workspace = JobApplicationWorkspace(
                        user_id=user.id,
                        job_id=job.id,
                        status="ready_for_apply",
                        include_cover_letter=True,
                        cover_letter_tone="professional",
                        cover_letter_template="modern",
                        contact_name=contact.name,
                        contact_email=contact.email,
                        contact_role=contact.role,
                        contact_source_url=contact.source_url,
                        contact_verification_status=contact.verification_status,
                        contact_notes=contact.notes,
                        contact_discovered_at=contact.discovered_at,
                    )
                    db.add(workspace)
                    db.commit()
                    db.refresh(workspace)

                # Determine if email outreach should be sent for this specific job
                should_send_email = bool(
                    send_email and (email_job_ids is None or job_id in email_job_ids)
                )

                # Preserve workspace screening answers if none provided in batch request
                ws_screening = {}
                if workspace.screening_answers:
                    try:
                        ws_screening = json.loads(workspace.screening_answers)
                    except Exception:
                        pass
                effective_screening = screening_answers if screening_answers else ws_screening

                # Execute application safely
                exec_result = await ApplicationAdapterManager.execute_application(
                    db=db,
                    user=user,
                    job=job,
                    workspace=workspace,
                    submit_portal=submit_portal,
                    send_email=should_send_email,
                    screening_answers=effective_screening,
                    idempotency_key=f"{idempotency_key}_{job_id}" if idempotency_key else None
                )

                # Update counters
                session.processed_jobs += 1
                if exec_result.application_status == "submitted":
                    session.successful_jobs += 1
                elif exec_result.application_status == "requires_user_action":
                    session.requires_action_jobs += 1
                elif exec_result.application_status == "failed":
                    session.failed_jobs += 1

                results.append(exec_result.model_dump())
                session.summary_log = json.dumps(results)
                session.updated_at = datetime.now(timezone.utc)
                db.commit()

            # Mark completed if not cancelled
            db.refresh(session)
            if not session.cancelled:
                session.status = "completed"
                session.current_job_id = None
                session.updated_at = datetime.now(timezone.utc)
                db.commit()

                from app.services.notification_service import NotificationService
                NotificationService.create_notification(
                    db=db,
                    user_id=user.id,
                    title="Batch Applications Complete",
                    message=f"Processed {session.processed_jobs} applications: {session.successful_jobs} submitted, {session.requires_action_jobs} manual kits prepared, {session.failed_jobs} failed.",
                    notification_type="application_submitted" if session.successful_jobs > 0 else "status_updated",
                    link="/applications/tracker"
                )
            else:
                from app.services.notification_service import NotificationService
                NotificationService.create_notification(
                    db=db,
                    user_id=user.id,
                    title="Batch Execution Cancelled",
                    message=f"Batch execution cancelled by user after processing {session.processed_jobs} of {session.total_jobs} applications.",
                    notification_type="status_updated",
                    link="/applications/tracker"
                )

        finally:
            if db_created:
                db.close()
