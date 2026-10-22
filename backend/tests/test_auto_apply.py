import json
import pytest
from app.core.config import settings
from app.models.application import ApplicationAuditLog, BatchApplicationSession, JobApplicationWorkspace
from app.models.job import JobListing, SavedJob
from app.models.resume import Resume
from app.models.user import User
from app.services.application_adapters.manager import ApplicationAdapterManager
from app.services.application_runner import ApplicationRunnerService
from app.services.email_service import EmailDeliveryService


@pytest.fixture
def test_candidate_resume(db_session, test_user):
    resume = Resume(
        user_id=test_user.id,
        original_filename="jane_doe_software_engineer.pdf",
        stored_filename="jane_doe_123.pdf",
        file_path="uploads/resumes/jane_doe_123.pdf",
        file_size=1024 * 50,
        mime_type="application/pdf",
        is_active=True
    )
    db_session.add(resume)
    db_session.commit()
    db_session.refresh(resume)
    return resume


def test_explicit_consent_strictly_required(client, auth_headers, db_session):
    """
    Ensures that auto-apply requests without explicit user consent are rejected with 400.
    Never submits before the user authorizes it.
    """
    job = JobListing(
        source_id="consent_job_1",
        source_name="arbeitnow",
        title="Software Engineer",
        company="ConsentCorp",
        location="Remote",
        url="https://example.com/job/consent",
        description="Engineering role."
    )
    db_session.add(job)
    db_session.commit()

    # Attempt to apply with user_consent_granted = False
    resp = client.post(
        "/api/v1/applications/apply/single",
        json={
            "job_id": job.id,
            "submit_portal": True,
            "send_email": False,
            "user_consent_granted": False  # No consent!
        },
        headers=auth_headers
    )
    assert resp.status_code == 400
    assert "Explicit user consent is strictly required" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_direct_api_successful_submission(db_session, test_user, test_candidate_resume):
    """
    Tests reliable submission confirmation via direct partner integration.
    """
    job = JobListing(
        source_id="direct_partner_101",
        source_name="direct_partner",  # Triggers DirectApiApplicationAdapter
        title="Senior Python Backend Developer",
        company="Verified Partner Tech",
        location="Remote",
        url="https://api.partner.jobs/v1/apply/101",
        description="Direct API integration available."
    )
    db_session.add(job)
    db_session.commit()

    ws = JobApplicationWorkspace(
        user_id=test_user.id,
        job_id=job.id,
        status="ready_for_apply",
        cover_letter_content="Customized cover letter for Verified Partner Tech."
    )
    db_session.add(ws)
    db_session.commit()

    result = await ApplicationAdapterManager.execute_application(
        db=db_session,
        user=test_user,
        job=job,
        workspace=ws,
        submit_portal=True,
        send_email=False,
        screening_answers={"work_authorization": "Authorized without sponsorship", "years_of_experience": 5},
        idempotency_key="idemp_key_1"
    )

    assert result.application_status == "submitted"
    assert result.application_confirmation_id is not None
    assert "JP-SUB-" in result.application_confirmation_id
    assert ws.application_status == "submitted"
    assert ws.application_submitted_at is not None

    # Check audit log
    audit = db_session.query(ApplicationAuditLog).filter(
        ApplicationAuditLog.user_id == test_user.id,
        ApplicationAuditLog.job_id == job.id,
        ApplicationAuditLog.action == "apply_submitted"
    ).first()
    assert audit is not None
    assert audit.status == "submitted"


@pytest.mark.asyncio
async def test_manual_portal_requires_user_action_and_prepares_kit(db_session, test_user, test_candidate_resume):
    """
    Ensures that for employers using external portals with CAPTCHAs/logins,
    the system pauses, does NOT bypass platform security, and provides a pre-filled kit.
    """
    job = JobListing(
        source_id="workday_portal_1",
        source_name="arbeitnow",
        title="Staff Infrastructure Engineer",
        company="Global Enterprise Inc",
        location="New York, NY",
        url="https://enterprise.myworkdayjobs.com/careers/job/1",
        description="Apply through Workday candidate portal. Requires login and verification."
    )
    db_session.add(job)
    db_session.commit()

    ws = JobApplicationWorkspace(
        user_id=test_user.id,
        job_id=job.id,
        status="ready_for_apply",
        cover_letter_content="Dear Hiring Team at Global Enterprise..."
    )
    db_session.add(ws)
    db_session.commit()

    result = await ApplicationAdapterManager.execute_application(
        db=db_session,
        user=test_user,
        job=job,
        workspace=ws,
        submit_portal=True,
        send_email=False,
        screening_answers={"work_authorization": "US Citizen", "earliest_start_date": "2 weeks notice"},
        idempotency_key="idemp_key_manual"
    )

    assert result.application_status == "requires_user_action"
    assert result.manual_action_url == "https://enterprise.myworkdayjobs.com/careers/job/1"
    assert result.manual_action_guide is not None
    assert result.manual_action_guide["candidate_name"] == test_user.full_name or test_user.email
    assert result.manual_action_guide["work_authorization"] == "US Citizen"
    assert "login" in result.manual_action_guide["instructions"].lower()


@pytest.mark.asyncio
async def test_ambiguous_submission_reports_status_unknown(db_session, test_user, test_candidate_resume):
    """
    Never fabricate successful submissions. If a destination times out or yields
    an ambiguous response, honestly report status_unknown.
    """
    job = JobListing(
        source_id="ambiguous_job_1",
        source_name="direct_partner",
        title="Cloud Architect",
        company="Ambiguous Cloud Inc",
        location="Remote",
        url="https://api.partner.jobs/v1/apply/ambiguous",
        description="Role testing simulated_ambiguous response."
    )
    db_session.add(job)
    db_session.commit()

    ws = JobApplicationWorkspace(user_id=test_user.id, job_id=job.id, status="draft")
    db_session.add(ws)
    db_session.commit()

    result = await ApplicationAdapterManager.execute_application(
        db=db_session,
        user=test_user,
        job=job,
        workspace=ws,
        submit_portal=True,
        send_email=False,
        screening_answers={},
        idempotency_key="idemp_ambig"
    )

    assert result.application_status == "status_unknown"
    assert "reliable receipt" in result.application_message.lower()


@pytest.mark.asyncio
async def test_duplicate_submission_prevention_idempotency(db_session, test_user, test_candidate_resume):
    """
    Ensures idempotency key prevents duplicate submission of already submitted application.
    """
    job = JobListing(
        source_id="idemp_job_1",
        source_name="direct_partner",
        title="Security Engineer",
        company="SecureNet",
        location="Remote",
        url="https://api.partner.jobs/v1/apply/sec1",
        description="Direct API role."
    )
    db_session.add(job)
    db_session.commit()

    ws = JobApplicationWorkspace(
        user_id=test_user.id,
        job_id=job.id,
        status="ready_for_apply"
    )
    db_session.add(ws)
    db_session.commit()

    key = "unique_apply_token_123"

    # First attempt: succeeds
    res1 = await ApplicationAdapterManager.execute_application(
        db=db_session,
        user=test_user,
        job=job,
        workspace=ws,
        submit_portal=True,
        send_email=False,
        screening_answers={},
        idempotency_key=key
    )
    assert res1.application_status == "submitted"

    # Second attempt with same idempotency key: returns replay result, no duplicate
    res2 = await ApplicationAdapterManager.execute_application(
        db=db_session,
        user=test_user,
        job=job,
        workspace=ws,
        submit_portal=True,
        send_email=False,
        screening_answers={},
        idempotency_key=key
    )
    assert res2.application_status == "submitted"
    assert "idempotent replay" in res2.application_message.lower()


def test_missing_email_credentials_honestly_reported(db_session, test_user):
    """
    If SMTP credentials are not configured, system must report not_configured
    and allow copy fallback rather than pretending the email was sent.
    """
    original_provider = settings.EMAIL_PROVIDER
    original_host = settings.SMTP_HOST
    original_user = settings.SMTP_USER

    try:
        # Simulate unconfigured SMTP
        settings.EMAIL_PROVIDER = "smtp"
        settings.SMTP_HOST = None
        settings.SMTP_USER = None

        res = EmailDeliveryService.send_email(
            db=db_session,
            user_id=test_user.id,
            job_id=999,
            workspace_id=None,
            recipient_email="recruiter@example.com",
            subject="Job Application",
            body="Hello, I am applying..."
        )

        assert res["status"] == "not_configured"
        assert "NOT sent" in res["message"]
        assert "Copy" in res["message"]

    finally:
        settings.EMAIL_PROVIDER = original_provider
        settings.SMTP_HOST = original_host
        settings.SMTP_USER = original_user


def test_batch_cancellation(db_session, test_user):
    """
    Tests that a user can cancel an in-flight batch session and halt remaining jobs.
    """
    session = ApplicationRunnerService.create_batch_session(
        db=db_session,
        user_id=test_user.id,
        total_jobs=5
    )
    assert session.status == "in_progress"
    assert not session.cancelled

    # Cancel session
    cancelled = ApplicationRunnerService.cancel_batch_session(
        db=db_session,
        session_id=session.id,
        user_id=test_user.id
    )
    assert cancelled is True

    # Verify session is cancelled
    db_session.refresh(session)
    assert session.cancelled is True
    assert session.status == "cancelled"


def test_review_center_detects_readiness_and_missing_info(client, auth_headers, db_session, test_user, test_candidate_resume):
    """
    Integration test for Review Center pre-submission validation.
    """
    job = JobListing(
        source_id="review_test_job",
        source_name="arbeitnow",
        title="Full Stack Engineer",
        company="Review Corp",
        location="Remote",
        url="https://example.com/job/review",
        description="Great role."
    )
    db_session.add(job)
    db_session.commit()

    saved = SavedJob(
        user_id=test_user.id,
        job_id=job.id,
        is_selected_for_apply=True
    )
    db_session.add(saved)
    db_session.commit()

    resp = client.get("/api/v1/applications/review", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_selected"] >= 1
    item = next(i for i in data["items"] if i["job_id"] == job.id)
    assert item["resume_attached"] is True
    assert item["destination_type"] in ["manual_portal", "direct_api", "email_application"]
