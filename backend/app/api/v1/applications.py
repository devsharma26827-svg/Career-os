import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.application import (
    ApplicationAuditLog,
    BatchApplicationSession,
    JobApplicationWorkspace,
    RecruiterContact,
)
from app.models.job import JobListing, SavedJob, SearchPreference
from app.models.profile import UserProfile
from app.models.resume import Resume
from app.models.user import User
from app.schemas.application import (
    ApplicationQueueItem,
    ApplicationQueueResponse,
    ApplicationReviewCenterResponse,
    ApplicationReviewItem,
    ApplicationStatusUpdateRequest,
    ApplicationWorkspaceResponse,
    ApplyExecutionResult,
    AuditLogResponseItem,
    BatchApplyRequest,
    BatchSessionResponse,
    ContactUpdateRequest,
    CoverLetterGenerateRequest,
    CoverLetterUpdateRequest,
    RecruiterEmailGenerateRequest,
    RecruiterEmailUpdateRequest,
    ScreeningAnswers,
    SingleApplyRequest,
)
from app.schemas.tracker import (
    DashboardSummaryResponse,
    FirstTimeProgress,
    TrackedApplicationItem,
    TrackerResponse,
)
from app.services.application_adapters.manager import ApplicationAdapterManager
from app.services.application_runner import ApplicationRunnerService
from app.services.contact_discovery import ContactDiscoveryService
from app.services.content_generator import (
    ApplicationContentService,
    DuplicateOutreachDetector,
)
from app.services.notification_service import NotificationService

router = APIRouter()


def _get_or_create_workspace(db: Session, user: User, job: JobListing) -> JobApplicationWorkspace:
    workspace = (
        db.query(JobApplicationWorkspace)
        .filter(
            JobApplicationWorkspace.user_id == user.id,
            JobApplicationWorkspace.job_id == job.id
        )
        .first()
    )

    if not workspace:
        # Auto-discover contact on first workspace creation
        contact = ContactDiscoveryService.discover_contact_for_job(job)
        
        workspace = JobApplicationWorkspace(
            user_id=user.id,
            job_id=job.id,
            status="draft",
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
            email_tone="concise",
        )
        db.add(workspace)
        db.commit()
        db.refresh(workspace)

    return workspace


def _build_workspace_response(workspace: JobApplicationWorkspace, db: Session) -> ApplicationWorkspaceResponse:
    job = workspace.job
    # Check duplicate outreach dynamically
    is_dup, warning = DuplicateOutreachDetector.check_duplicate(
        db=db,
        user_id=workspace.user_id,
        current_job=job,
        contact_email=workspace.contact_email
    )
    workspace.is_duplicate_outreach = is_dup
    workspace.duplicate_warning = warning

    answers_dict = None
    if workspace.screening_answers:
        try:
            answers_dict = json.loads(workspace.screening_answers)
        except Exception:
            answers_dict = None

    return ApplicationWorkspaceResponse(
        id=workspace.id,
        job_id=job.id,
        job_title=job.title,
        job_company=job.company,
        job_location=job.location,
        job_url=job.url,
        job_source=job.source_name,
        job_description=job.description,
        status=workspace.status,
        include_cover_letter=workspace.include_cover_letter,
        cover_letter_content=workspace.cover_letter_content,
        cover_letter_tone=workspace.cover_letter_tone,
        cover_letter_template=workspace.cover_letter_template,
        cover_letter_updated_at=workspace.cover_letter_updated_at,
        contact_name=workspace.contact_name,
        contact_email=workspace.contact_email,
        contact_role=workspace.contact_role,
        contact_source_url=workspace.contact_source_url,
        contact_verification_status=workspace.contact_verification_status,
        contact_discovered_at=workspace.contact_discovered_at,
        contact_notes=workspace.contact_notes,
        email_subject=workspace.email_subject,
        email_body=workspace.email_body,
        email_tone=workspace.email_tone,
        email_updated_at=workspace.email_updated_at,
        is_duplicate_outreach=is_dup,
        duplicate_warning=warning,
        application_destination=workspace.application_destination or "manual_portal",
        application_status=workspace.application_status or "not_started",
        application_confirmation_id=workspace.application_confirmation_id,
        application_confirmation_message=workspace.application_confirmation_message,
        application_submitted_at=workspace.application_submitted_at,
        application_error=workspace.application_error,
        email_outreach_status=workspace.email_outreach_status or "not_started",
        email_sent_at=workspace.email_sent_at,
        email_error=workspace.email_error,
        screening_answers=answers_dict,
        user_consent_granted=workspace.user_consent_granted or False,
        consent_timestamp=workspace.consent_timestamp,
    )


@router.get("/queue", response_model=ApplicationQueueResponse)
def get_application_queue(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns all jobs selected by the user for the application queue (Module 3 workspace).
    """
    saved_items = (
        db.query(SavedJob)
        .filter(SavedJob.user_id == current_user.id, SavedJob.is_selected_for_apply.is_(True))
        .all()
    )

    items: List[ApplicationQueueItem] = []
    draft_count = 0
    reviewed_count = 0
    ready_count = 0
    submitted_count = 0

    for item in saved_items:
        job = item.job
        # Check if workspace exists
        ws = (
            db.query(JobApplicationWorkspace)
            .filter(
                JobApplicationWorkspace.user_id == current_user.id,
                JobApplicationWorkspace.job_id == job.id
            )
            .first()
        )

        ws_status = ws.status if ws else "draft"
        if ws_status == "draft":
            draft_count += 1
        elif ws_status == "reviewed":
            reviewed_count += 1
        elif ws_status == "ready_for_apply":
            ready_count += 1

        app_st = ws.application_status if (ws and ws.application_status) else "not_started"
        if app_st == "submitted":
            submitted_count += 1

        items.append(
            ApplicationQueueItem(
                job_id=job.id,
                workspace_id=ws.id if ws else None,
                title=job.title,
                company=job.company,
                location=job.location,
                source_name=job.source_name,
                url=job.url,
                status=ws_status,
                has_cover_letter=bool(ws and ws.cover_letter_content),
                has_email_draft=bool(ws and ws.email_body),
                contact_verification_status=ws.contact_verification_status if ws else "NOT_FOUND",
                contact_email=ws.contact_email if ws else None,
                application_status=app_st,
                email_outreach_status=ws.email_outreach_status if (ws and ws.email_outreach_status) else "not_started",
                saved_at=item.saved_at,
            )
        )

    return ApplicationQueueResponse(
        total_queued=len(items),
        draft_count=draft_count,
        reviewed_count=reviewed_count,
        ready_for_apply_count=ready_count,
        submitted_count=submitted_count,
        items=items,
    )


@router.get("/review", response_model=ApplicationReviewCenterResponse)
def get_application_review_center(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Module 4 Application Review Center:
    Presents an approval pre-check screen showing destination, attached resume,
    cover letter preview, screening answers, and any missing required fields.
    """
    saved_items = (
        db.query(SavedJob)
        .filter(SavedJob.user_id == current_user.id, SavedJob.is_selected_for_apply.is_(True))
        .all()
    )

    resume = (
        db.query(Resume)
        .filter(Resume.user_id == current_user.id, Resume.is_active == True)
        .first()
    )

    user_profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    search_pref = db.query(SearchPreference).filter(SearchPreference.user_id == current_user.id).first()

    default_exp_years = None
    if user_profile and user_profile.experiences:
        try:
            exps = json.loads(user_profile.experiences) if isinstance(user_profile.experiences, str) else user_profile.experiences
            if isinstance(exps, list) and len(exps) > 0:
                default_exp_years = len(exps)
        except Exception:
            pass

    country_code = (search_pref.country if search_pref and search_pref.country else "US").upper()
    default_work_auth = f"Authorized to work in {country_code} without sponsorship"
    default_salary = f"${search_pref.min_salary:,.0f} / year" if (search_pref and search_pref.min_salary) else "Market rate / Negotiable"

    items: List[ApplicationReviewItem] = []
    global_missing = set()
    if not resume:
        global_missing.add("Active resume document is missing. Please upload your resume.")

    ready_count = 0
    missing_info_count = 0

    for item in saved_items:
        job = item.job
        ws = _get_or_create_workspace(db, current_user, job)

        # Destination type
        dest_type = ApplicationAdapterManager.determine_destination_type(job, ws)

        # Parse screening answers with sensible profile defaults
        answers_dict = {}
        if ws.screening_answers:
            try:
                answers_dict = json.loads(ws.screening_answers)
            except Exception:
                pass

        if not answers_dict:
            answers_dict = {
                "work_authorization": default_work_auth,
                "years_of_experience": default_exp_years,
                "earliest_start_date": "Immediately",
                "salary_expectation": default_salary,
                "confirmed_by_user": False,
            }
        elif not answers_dict.get("work_authorization"):
            answers_dict["work_authorization"] = default_work_auth

        screening = ScreeningAnswers(**answers_dict)

        # Assess missing required fields
        job_missing: List[str] = []
        if not resume:
            job_missing.append("Resume file missing")
        if not screening.work_authorization:
            job_missing.append("Work authorization required")
        if dest_type == "email_application" and not ws.contact_email:
            job_missing.append("Recipient email missing for email application")

        is_ready = len(job_missing) == 0
        if is_ready:
            ready_count += 1
        else:
            missing_info_count += 1

        cl_word_count = len(ws.cover_letter_content.split()) if ws.cover_letter_content else 0

        items.append(
            ApplicationReviewItem(
                job_id=job.id,
                workspace_id=ws.id,
                title=job.title,
                company=job.company,
                location=job.location,
                source_name=job.source_name,
                url=job.url,
                destination_type=dest_type,
                resume_name=resume.original_filename if resume else None,
                resume_id=resume.id if resume else None,
                resume_attached=bool(resume),
                cover_letter_included=ws.include_cover_letter,
                cover_letter_preview=ws.cover_letter_content[:200] + "..." if ws.cover_letter_content else None,
                cover_letter_word_count=cl_word_count,
                recruiter_name=ws.contact_name,
                recruiter_email=ws.contact_email,
                recruiter_email_preview=ws.email_body[:200] + "..." if ws.email_body else None,
                email_verification_status=ws.contact_verification_status or "NOT_FOUND",
                screening_answers=screening,
                missing_required_info=job_missing,
                ready_to_submit=is_ready,
                application_status=ws.application_status or "not_started",
                email_outreach_status=ws.email_outreach_status or "not_started",
                application_confirmation_id=ws.application_confirmation_id,
                application_message=ws.application_confirmation_message,
            )
        )

    return ApplicationReviewCenterResponse(
        total_selected=len(items),
        ready_count=ready_count,
        missing_info_count=missing_info_count,
        items=items,
        global_missing_info=list(global_missing),
    )


@router.get("/audit-log", response_model=List[AuditLogResponseItem])
def get_application_audit_logs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns the audit trail of user approvals, application submissions,
    and recruiter outreach attempts.
    """
    logs = (
        db.query(ApplicationAuditLog)
        .filter(ApplicationAuditLog.user_id == current_user.id)
        .order_by(ApplicationAuditLog.created_at.desc())
        .limit(100)
        .all()
    )

    items: List[AuditLogResponseItem] = []
    for log in logs:
        job = log.job
        items.append(
            AuditLogResponseItem(
                id=log.id,
                job_id=log.job_id,
                job_title=job.title if job else None,
                job_company=job.company if job else None,
                action=log.action,
                status=log.status,
                destination=log.destination,
                recipient=log.recipient,
                details=log.details,
                created_at=log.created_at,
            )
        )
    return items


def _workspace_to_tracked_item(w: JobApplicationWorkspace, job: JobListing, contact: Optional[RecruiterContact]) -> TrackedApplicationItem:
    dest_type = "direct_api" if job.source_name in ["workable_api", "greenhouse_direct"] else (
        "email_application" if contact and contact.email else "manual_portal"
    )
    can_retry = w.application_status in ["failed", "requires_user_action"]

    screening_confirmed = False
    if w.screening_answers:
        try:
            parsed = json.loads(w.screening_answers)
            screening_confirmed = parsed.get("confirmed_by_user", False)
        except Exception:
            screening_confirmed = False

    return TrackedApplicationItem(
        id=w.id,
        job_id=w.job_id,
        job_title=job.title,
        company=job.company,
        location=job.location,
        source_name=job.source_name,
        job_url=job.url,
        destination_type=dest_type,
        application_status=w.application_status or "not_started",
        application_confirmation_id=w.application_confirmation_id,
        application_message=w.application_confirmation_message,
        has_cover_letter=bool(w.cover_letter_content and w.cover_letter_content.strip()),
        cover_letter_preview=w.cover_letter_content[:180] + "..." if w.cover_letter_content and len(w.cover_letter_content) > 180 else w.cover_letter_content,
        has_email_draft=bool(w.email_body and w.email_body.strip()),
        email_outreach_status=w.email_outreach_status or "not_started",
        recruiter_email=contact.email if contact else None,
        screening_confirmed=screening_confirmed,
        can_retry=can_retry,
        applied_at=w.application_submitted_at,
        updated_at=w.updated_at,
    )


@router.get("/tracker", response_model=TrackerResponse)
def get_application_tracker(
    query: Optional[str] = None,
    status: Optional[str] = None,
    destination: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Searchable, filterable tracker listing candidate's applications,
    submission destinations, verified status updates, and safe retry controls.
    """
    workspaces_query = (
        db.query(JobApplicationWorkspace, JobListing, RecruiterContact)
        .join(JobListing, JobApplicationWorkspace.job_id == JobListing.id)
        .outerjoin(
            RecruiterContact,
            RecruiterContact.job_id == JobApplicationWorkspace.job_id
        )
        .filter(JobApplicationWorkspace.user_id == current_user.id)
        .order_by(JobApplicationWorkspace.updated_at.desc())
    )

    if status and status != "all":
        workspaces_query = workspaces_query.filter(JobApplicationWorkspace.application_status == status)

    if query:
        q_wildcard = f"%{query.lower()}%"
        workspaces_query = workspaces_query.filter(
            (JobListing.title.ilike(q_wildcard)) |
            (JobListing.company.ilike(q_wildcard)) |
            (JobListing.location.ilike(q_wildcard))
        )

    records = workspaces_query.all()

    items: List[TrackedApplicationItem] = []
    submitted_count = 0
    requires_action_count = 0
    failed_count = 0

    for w, j, c in records:
        item = _workspace_to_tracked_item(w, j, c)

        if destination and destination != "all" and item.destination_type != destination:
            continue

        if item.application_status == "submitted":
            submitted_count += 1
        elif item.application_status == "requires_user_action":
            requires_action_count += 1
        elif item.application_status == "failed":
            failed_count += 1

        items.append(item)

    return TrackerResponse(
        total=len(items),
        submitted_count=submitted_count,
        requires_action_count=requires_action_count,
        failed_count=failed_count,
        items=items
    )


@router.get("/dashboard-summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Provides unified metrics for the main dashboard:
    Jobs discovered, saved jobs, queued applications, submissions,
    action items, safe retry counts, recruiter outreach, and recent activity.
    """
    from app.models.job import SearchPreference

    jobs_discovered = db.query(JobListing).count()
    saved_jobs_count = db.query(SavedJob).filter(SavedJob.user_id == current_user.id).count()
    queued_jobs_count = (
        db.query(SavedJob)
        .filter(SavedJob.user_id == current_user.id, SavedJob.is_selected_for_apply == True)
        .count()
    )

    workspaces = (
        db.query(JobApplicationWorkspace, JobListing, RecruiterContact)
        .join(JobListing, JobApplicationWorkspace.job_id == JobListing.id)
        .outerjoin(
            RecruiterContact,
            RecruiterContact.job_id == JobApplicationWorkspace.job_id
        )
        .filter(JobApplicationWorkspace.user_id == current_user.id)
        .order_by(JobApplicationWorkspace.updated_at.desc())
        .all()
    )

    submitted_count = sum(1 for w, _, _ in workspaces if w.application_status == "submitted")
    action_required_count = sum(1 for w, _, _ in workspaces if w.application_status == "requires_user_action")
    failed_count = sum(1 for w, _, _ in workspaces if w.application_status == "failed")
    emails_sent_count = sum(1 for w, _, _ in workspaces if w.email_outreach_status == "sent")

    latest_items = [_workspace_to_tracked_item(w, j, c) for w, j, c in workspaces[:5]]

    # Recent Audit Log Activity
    recent_logs = (
        db.query(ApplicationAuditLog)
        .filter(ApplicationAuditLog.user_id == current_user.id)
        .order_by(ApplicationAuditLog.created_at.desc())
        .limit(8)
        .all()
    )

    recent_activity: List[AuditLogResponseItem] = []
    for log in recent_logs:
        j = log.job
        recent_activity.append(
            AuditLogResponseItem(
                id=log.id,
                job_id=log.job_id,
                job_title=j.title if j else None,
                job_company=j.company if j else None,
                action=log.action,
                status=log.status,
                destination=log.destination,
                recipient=log.recipient,
                details=log.details,
                created_at=log.created_at,
            )
        )

    # First-time user onboarding progress
    has_resume = bool(db.query(Resume).filter(Resume.user_id == current_user.id).first())
    has_location_pref = bool(db.query(SearchPreference).filter(SearchPreference.user_id == current_user.id).first())
    has_found_jobs = saved_jobs_count > 0 or queued_jobs_count > 0
    has_prepared_content = any(bool(w.cover_letter_content or w.email_body) for w, _, _ in workspaces)
    has_applied = submitted_count > 0 or action_required_count > 0

    progress_steps = [has_resume, has_location_pref, has_found_jobs, has_prepared_content, has_applied]
    completed_steps_count = sum(1 for s in progress_steps if s)
    percentage = int((completed_steps_count / 5.0) * 100)
    current_step = completed_steps_count + 1 if completed_steps_count < 5 else 5

    first_time_progress = FirstTimeProgress(
        has_resume=has_resume,
        has_location_pref=has_location_pref,
        has_found_jobs=has_found_jobs,
        has_prepared_content=has_prepared_content,
        has_applied=has_applied,
        current_step=current_step,
        percentage=percentage,
    )

    # Active batch session check
    active_batch = (
        db.query(BatchApplicationSession)
        .filter(
            BatchApplicationSession.user_id == current_user.id,
            BatchApplicationSession.status == "in_progress"
        )
        .order_by(BatchApplicationSession.created_at.desc())
        .first()
    )
    active_batch_response = None
    if active_batch:
        active_batch_response = ApplicationRunnerService.get_batch_session(
            db, active_batch.id, current_user.id
        )

    return DashboardSummaryResponse(
        jobs_discovered=jobs_discovered,
        saved_jobs_count=saved_jobs_count,
        queued_jobs_count=queued_jobs_count,
        submitted_count=submitted_count,
        action_required_count=action_required_count,
        failed_count=failed_count,
        emails_sent_count=emails_sent_count,
        recent_activity=recent_activity,
        latest_updates=latest_items,
        first_time_progress=first_time_progress,
        active_batch_session=active_batch_response,
    )


@router.post("/apply/single", response_model=ApplyExecutionResult)
async def apply_single_job(
    req: SingleApplyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Executes an application for a single job with explicit user consent.
    Never submits without authorization.
    """
    if not req.user_consent_granted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Explicit user consent is strictly required before submitting an application or sending an email."
        )

    job = db.query(JobListing).filter(JobListing.id == req.job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job listing not found.")

    workspace = _get_or_create_workspace(db, current_user, job)

    screening_dict = req.screening_answers.model_dump() if req.screening_answers else {}

    result = await ApplicationAdapterManager.execute_application(
        db=db,
        user=current_user,
        job=job,
        workspace=workspace,
        submit_portal=req.submit_portal,
        send_email=req.send_email,
        screening_answers=screening_dict,
        idempotency_key=req.idempotency_key
    )

    # Notify candidate on submission event
    if result.application_status == "submitted":
        NotificationService.create_notification(
            db=db,
            user_id=current_user.id,
            title="Application Submitted",
            message=f"Application for '{job.title}' at {job.company} was submitted successfully.",
            notification_type="application_submitted",
            link="/applications/tracker"
        )
    elif result.application_status == "requires_user_action":
        NotificationService.create_notification(
            db=db,
            user_id=current_user.id,
            title="Manual Action Needed",
            message=f"Assisted application kit ready for '{job.title}' at {job.company}.",
            notification_type="action_required",
            link="/applications/review"
        )
    elif result.application_status == "failed":
        NotificationService.create_notification(
            db=db,
            user_id=current_user.id,
            title="Submission Failed",
            message=f"Submission to {job.company} failed: {result.application_message}. Safe retry available.",
            notification_type="submission_failed",
            link="/applications/tracker"
        )

    return result


@router.post("/apply/batch", response_model=BatchSessionResponse)
async def apply_batch_jobs(
    req: BatchApplyRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Starts an asynchronous batch application session with explicit user authorization.
    Tracks progress and allows cancellation of pending tasks.
    """
    if not req.user_consent_granted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Explicit user consent is strictly required before submitting application batches."
        )

    if not req.job_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No jobs selected for batch application.")

    session = ApplicationRunnerService.create_batch_session(
        db=db,
        user_id=current_user.id,
        total_jobs=len(req.job_ids)
    )

    screening_dict = req.screening_answers.model_dump() if req.screening_answers else {}

    # Launch background batch runner
    background_tasks.add_task(
        ApplicationRunnerService.run_batch_process,
        session_id=session.id,
        user_id=current_user.id,
        job_ids=req.job_ids,
        submit_portal=req.submit_portal,
        send_email=req.send_email,
        screening_answers=screening_dict,
        idempotency_key=req.idempotency_key,
        email_job_ids=req.email_job_ids
    )

    return BatchSessionResponse(
        session_id=session.id,
        total_jobs=session.total_jobs,
        processed_jobs=0,
        successful_jobs=0,
        failed_jobs=0,
        requires_action_jobs=0,
        status="in_progress",
        cancelled=False,
        current_job_id=None,
        summary_log=[]
    )


@router.get("/batch/{session_id}", response_model=BatchSessionResponse)
def get_batch_session_status(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves progress and results for an active or completed batch application session.
    """
    res = ApplicationRunnerService.get_batch_session(db, session_id, current_user.id)
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch session not found.")
    return res


@router.post("/batch/{session_id}/cancel")
def cancel_batch_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cancels an in-flight batch session. Prevents processing of any pending jobs.
    """
    cancelled = ApplicationRunnerService.cancel_batch_session(db, session_id, current_user.id)
    if not cancelled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch session not found.")

    # Record cancellation audit log
    log = ApplicationAuditLog(
        user_id=current_user.id,
        action="batch_cancelled",
        status="cancelled",
        details=f"User requested cancellation of batch session {session_id}.",
        created_at=datetime.now(timezone.utc)
    )
    db.add(log)
    db.commit()

    return {"message": "Batch cancellation requested successfully.", "session_id": session_id}


@router.get("/{job_id}", response_model=ApplicationWorkspaceResponse)
def get_job_application_workspace(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves or initializes the application workspace for a given job.
    Auto-discovers recruiter contact information if not already saved.
    """
    job = db.query(JobListing).filter(JobListing.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job listing not found."
        )

    workspace = _get_or_create_workspace(db, current_user, job)
    return _build_workspace_response(workspace, db)


@router.post("/{job_id}/cover-letter/generate", response_model=ApplicationWorkspaceResponse)
async def generate_cover_letter(
    job_id: int,
    req: CoverLetterGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generates a personalized, tailored cover letter using verified resume profile data.
    Does not invent unverified qualifications or make false claims.
    """
    job = db.query(JobListing).filter(JobListing.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job listing not found.")

    workspace = _get_or_create_workspace(db, current_user, job)
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()

    # Generate content
    letter_text = await ApplicationContentService.generate_cover_letter(
        profile=profile,
        job=job,
        tone=req.tone,
        template_style=req.template_style
    )

    workspace.cover_letter_content = letter_text
    workspace.cover_letter_tone = req.tone
    workspace.cover_letter_template = req.template_style
    workspace.cover_letter_updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(workspace)

    return _build_workspace_response(workspace, db)


@router.put("/{job_id}/cover-letter", response_model=ApplicationWorkspaceResponse)
def update_cover_letter(
    job_id: int,
    req: CoverLetterUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Saves user edits to the cover letter draft, including tone, template, and optional inclusion flag.
    """
    job = db.query(JobListing).filter(JobListing.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job listing not found.")

    workspace = _get_or_create_workspace(db, current_user, job)
    workspace.cover_letter_content = req.content
    if req.tone:
        workspace.cover_letter_tone = req.tone
    if req.template_style:
        workspace.cover_letter_template = req.template_style
    if req.include_cover_letter is not None:
        workspace.include_cover_letter = req.include_cover_letter

    workspace.cover_letter_updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(workspace)

    return _build_workspace_response(workspace, db)


@router.post("/{job_id}/email/generate", response_model=ApplicationWorkspaceResponse)
async def generate_recruiter_email(
    job_id: int,
    req: RecruiterEmailGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generates a concise, polite recruiter email draft tailored to the job and company.
    Checks for duplicate outreach warnings.
    """
    job = db.query(JobListing).filter(JobListing.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job listing not found.")

    workspace = _get_or_create_workspace(db, current_user, job)
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()

    # Create dummy contact object from workspace fields for generator
    contact = RecruiterContact(
        name=workspace.contact_name,
        email=workspace.contact_email,
        role=workspace.contact_role,
        source_url=workspace.contact_source_url or job.url,
        company=job.company
    )

    subject, body = await ApplicationContentService.generate_recruiter_email(
        profile=profile,
        job=job,
        contact=contact,
        tone=req.tone
    )

    workspace.email_subject = subject
    workspace.email_body = body
    workspace.email_tone = req.tone
    workspace.email_updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(workspace)

    return _build_workspace_response(workspace, db)


@router.put("/{job_id}/email", response_model=ApplicationWorkspaceResponse)
def update_recruiter_email(
    job_id: int,
    req: RecruiterEmailUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Saves user edits to the subject line, email body, and tone.
    """
    job = db.query(JobListing).filter(JobListing.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job listing not found.")

    workspace = _get_or_create_workspace(db, current_user, job)
    workspace.email_subject = req.subject
    workspace.email_body = req.body
    if req.tone:
        workspace.email_tone = req.tone

    workspace.email_updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(workspace)

    return _build_workspace_response(workspace, db)


@router.put("/{job_id}/contact", response_model=ApplicationWorkspaceResponse)
def update_contact_details(
    job_id: int,
    req: ContactUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Allows user to update recruiter contact name, email, role, or notes,
    marking the verification status as USER_VERIFIED.
    """
    job = db.query(JobListing).filter(JobListing.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job listing not found.")

    workspace = _get_or_create_workspace(db, current_user, job)
    if req.name is not None:
        workspace.contact_name = req.name.strip() or None
    if req.email is not None:
        workspace.contact_email = req.email.strip() or None
    if req.role is not None:
        workspace.contact_role = req.role.strip() or None
    if req.notes is not None:
        workspace.contact_notes = req.notes.strip() or None

    workspace.contact_verification_status = req.verification_status or "USER_VERIFIED"
    workspace.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(workspace)

    return _build_workspace_response(workspace, db)


@router.put("/{job_id}/status", response_model=ApplicationWorkspaceResponse)
def update_application_status(
    job_id: int,
    req: ApplicationStatusUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Updates the application workspace workflow status:
    'draft' -> 'reviewed' -> 'ready_for_apply' -> 'skipped'
    """
    valid_statuses = {"draft", "reviewed", "ready_for_apply", "skipped"}
    if req.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status '{req.status}'. Must be one of: {', '.join(valid_statuses)}"
        )

    job = db.query(JobListing).filter(JobListing.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job listing not found.")

    workspace = _get_or_create_workspace(db, current_user, job)
    workspace.status = req.status
    workspace.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(workspace)

    return _build_workspace_response(workspace, db)


@router.put("/{job_id}/screening-answers", response_model=ApplicationWorkspaceResponse)
def update_screening_answers(
    job_id: int,
    req: ScreeningAnswers,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Saves user-confirmed screening questions (work authorization, experience, availability, salary).
    Never invents personal facts.
    """
    job = db.query(JobListing).filter(JobListing.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job listing not found.")

    workspace = _get_or_create_workspace(db, current_user, job)
    workspace.screening_answers = json.dumps(req.model_dump())
    workspace.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(workspace)

    return _build_workspace_response(workspace, db)


@router.post("/screening/batch")
def batch_update_screening_answers(
    req: ScreeningAnswers,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Saves user-confirmed screening questions across all active application workspaces.
    Never invents personal facts.
    """
    workspaces = (
        db.query(JobApplicationWorkspace)
        .filter(JobApplicationWorkspace.user_id == current_user.id)
        .all()
    )
    req_dict = req.model_dump()
    req_dict["confirmed_by_user"] = True
    json_str = json.dumps(req_dict)

    for ws in workspaces:
        ws.screening_answers = json_str
        ws.updated_at = datetime.now(timezone.utc)

    db.commit()
    return {
        "message": f"Updated screening answers for {len(workspaces)} workspaces.",
        "screening_answers": req_dict
    }


@router.post("/{job_id}/mark-submitted", response_model=ApplicationWorkspaceResponse)
def mark_application_submitted(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Allows the user to mark a manual portal application as completed and submitted
    after finishing the application on the employer's official website.
    """
    job = db.query(JobListing).filter(JobListing.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job listing not found.")

    workspace = _get_or_create_workspace(db, current_user, job)
    workspace.application_status = "submitted"
    workspace.application_confirmation_message = "Application confirmed submitted on employer portal by user."
    workspace.application_submitted_at = datetime.now(timezone.utc)
    workspace.status = "ready_for_apply"
    workspace.updated_at = datetime.now(timezone.utc)

    # Log audit event
    log = ApplicationAuditLog(
        user_id=current_user.id,
        job_id=job.id,
        workspace_id=workspace.id,
        action="manual_portal_completed_by_user",
        status="success",
        destination="manual_portal",
        details="User verified manual submission on company website.",
        created_at=datetime.now(timezone.utc)
    )
    db.add(log)

    db.commit()
    db.refresh(workspace)

    NotificationService.create_notification(
        db=db,
        user_id=current_user.id,
        title="Application Confirmed",
        message=f"Application for '{job.title}' at {job.company} was confirmed submitted.",
        notification_type="application_submitted",
        link="/applications/tracker"
    )

    return _build_workspace_response(workspace, db)


@router.post("/{job_id}/retry", response_model=ApplicationWorkspaceResponse)
def retry_failed_application(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Safely resets a failed or action-required application to ready_for_apply,
    allowing candidate to re-review and re-authorize submission.
    """
    job = db.query(JobListing).filter(JobListing.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job listing not found.")

    workspace = _get_or_create_workspace(db, current_user, job)
    workspace.application_status = "pending"
    workspace.status = "ready_for_apply"
    workspace.application_confirmation_message = "Application reset for safe retry. Ready for authorization."
    workspace.updated_at = datetime.now(timezone.utc)

    # Log audit event
    log = ApplicationAuditLog(
        user_id=current_user.id,
        job_id=job.id,
        workspace_id=workspace.id,
        action="application_safe_retry_initiated",
        status="pending",
        destination="retry_queue",
        details="Candidate reset application state to allow fresh authorized submission attempt.",
        created_at=datetime.now(timezone.utc)
    )
    db.add(log)
    db.commit()
    db.refresh(workspace)

    NotificationService.create_notification(
        db=db,
        user_id=current_user.id,
        title="Application Ready to Retry",
        message=f"Application for '{job.title}' at {job.company} has been reset and is ready for re-submission in the Review Center.",
        notification_type="status_updated",
        link="/applications/review"
    )

    return _build_workspace_response(workspace, db)

