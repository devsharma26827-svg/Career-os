import pytest
import uuid
import json
import asyncio
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.application import JobApplicationWorkspace, BatchApplicationSession, ApplicationAuditLog
from app.models.job import JobListing, SavedJob, SearchPreference
from app.models.profile import UserProfile
from app.models.resume import Resume
from app.models.user import User
from app.services.application_runner import ApplicationRunnerService
from app.services.application_adapters.manager import ApplicationAdapterManager


def test_batch_select_and_deselect_jobs(client: TestClient, test_user: User, auth_headers: dict, db_session: Session):
    # Create 3 jobs
    jobs = []
    for i in range(3):
        job = JobListing(
            source_id=f"test_src_{uuid.uuid4().hex[:6]}",
            source_name="direct_partner",
            title=f"Engineer {i}",
            company="Acme Corp",
            location="New York, NY",
            country="US",
            url=f"https://api.partner.jobs/{i}",
            description="Software engineer role.",
            cached_at=datetime.now(timezone.utc)
        )
        db_session.add(job)
        jobs.append(job)
    db_session.commit()

    job_ids = [j.id for j in jobs]

    # Batch select
    resp = client.post(
        "/api/v1/jobs/batch-select",
        json={"job_ids": job_ids, "selected": True},
        headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["selected_count"] == 3
    assert data["selected"] is True

    # Verify database
    saved = db_session.query(SavedJob).filter(SavedJob.user_id == test_user.id, SavedJob.job_id.in_(job_ids)).all()
    assert len(saved) == 3
    for s in saved:
        assert s.is_selected_for_apply is True

    # Batch deselect
    resp2 = client.post(
        "/api/v1/jobs/batch-select",
        json={"job_ids": [job_ids[0]], "selected": False},
        headers=auth_headers
    )
    assert resp2.status_code == 200
    db_session.expire_all()
    s0 = db_session.query(SavedJob).filter(SavedJob.user_id == test_user.id, SavedJob.job_id == job_ids[0]).first()
    assert s0.is_selected_for_apply is False


def test_review_center_prepopulates_profile_screening(client: TestClient, test_user: User, auth_headers: dict, db_session: Session):
    # Ensure active resume exists
    resume = db_session.query(Resume).filter(Resume.user_id == test_user.id).first()
    if not resume:
        resume = Resume(
            user_id=test_user.id,
            original_filename="my_resume.pdf",
            stored_filename="my_resume_123.pdf",
            file_path="uploads/my_resume.pdf",
            file_size=1024,
            mime_type="application/pdf",
            is_active=True
        )
        db_session.add(resume)
        db_session.commit()

    # Create profile with experiences
    profile = db_session.query(UserProfile).filter(UserProfile.user_id == test_user.id).first()
    if not profile:
        profile = UserProfile(
            user_id=test_user.id,
            full_name="Alex Candidate",
            email=test_user.email,
            location="San Francisco, CA",
            experiences=json.dumps([{"title": "Dev", "company": "Tech", "duration": "2020 - 2024"}]),
            skills=json.dumps(["Python", "React"])
        )
        db_session.add(profile)
    else:
        profile.experiences = json.dumps([{"title": "Dev", "company": "Tech", "duration": "2020 - 2024"}])
    db_session.commit()

    # Create job and select for apply
    job = JobListing(
        source_id=f"test_rev_{uuid.uuid4().hex[:6]}",
        source_name="direct_partner",
        title="Backend Lead",
        company="GlobalTech",
        location="Remote, US",
        country="US",
        url="https://api.partner.jobs/lead",
        description="Lead backend developer.",
        cached_at=datetime.now(timezone.utc)
    )
    db_session.add(job)
    db_session.commit()

    saved = SavedJob(user_id=test_user.id, job_id=job.id, is_selected_for_apply=True)
    db_session.add(saved)
    db_session.commit()

    resp = client.get("/api/v1/applications/review", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_selected"] >= 1
    item = next(i for i in data["items"] if i["job_id"] == job.id)
    assert item["resume_attached"] is True
    assert item["screening_answers"]["work_authorization"] is not None
    assert item["screening_answers"]["years_of_experience"] is not None
    assert item["ready_to_submit"] is True


def test_batch_apply_workflow_and_duplicate_prevention(client: TestClient, test_user: User, auth_headers: dict, db_session: Session):
    # Ensure active resume exists
    resume = db_session.query(Resume).filter(Resume.user_id == test_user.id).first()
    if not resume:
        resume = Resume(
            user_id=test_user.id,
            original_filename="active_res.pdf",
            stored_filename="active_res_123.pdf",
            file_path="uploads/active_res.pdf",
            file_size=2048,
            mime_type="application/pdf",
            is_active=True
        )
        db_session.add(resume)
        db_session.commit()

    # Job 1: Direct Partner (should submit directly)
    job_direct = JobListing(
        source_id=f"direct_{uuid.uuid4().hex[:6]}",
        source_name="direct_partner",
        title="Direct API Role",
        company="Direct Partner Inc",
        location="Austin, TX",
        country="US",
        url="https://api.partner.jobs/v1/apply",
        description="Direct API role description.",
        cached_at=datetime.now(timezone.utc)
    )
    # Job 2: External ATS portal (should produce requires_user_action application kit)
    job_portal = JobListing(
        source_id=f"portal_{uuid.uuid4().hex[:6]}",
        source_name="web_portal",
        title="ATS Portal Role",
        company="BigCorp Enterprise",
        location="Chicago, IL",
        country="US",
        url="https://jobs.bigcorp.com/apply/123",
        description="Workday portal application.",
        cached_at=datetime.now(timezone.utc)
    )
    db_session.add_all([job_direct, job_portal])
    db_session.commit()

    # Batch Apply without consent should fail
    resp_no_consent = client.post(
        "/api/v1/applications/apply/batch",
        json={
            "job_ids": [job_direct.id, job_portal.id],
            "submit_portal": True,
            "send_email": False,
            "user_consent_granted": False
        },
        headers=auth_headers
    )
    assert resp_no_consent.status_code == 400

    # Batch Apply with explicit consent
    resp_consent = client.post(
        "/api/v1/applications/apply/batch",
        json={
            "job_ids": [job_direct.id, job_portal.id],
            "submit_portal": True,
            "send_email": False,
            "user_consent_granted": True,
            "screening_answers": {
                "work_authorization": "Authorized to work in US",
                "years_of_experience": 5,
                "earliest_start_date": "Immediately",
                "salary_expectation": "$130,000",
                "confirmed_by_user": True
            }
        },
        headers=auth_headers
    )
    assert resp_consent.status_code == 200
    session_data = resp_consent.json()
    assert session_data["session_id"] is not None
    assert session_data["total_jobs"] == 2

    # Execute inline for testing
    asyncio.run(
        ApplicationRunnerService.run_batch_process(
            session_id=session_data["session_id"],
            user_id=test_user.id,
            job_ids=[job_direct.id, job_portal.id],
            submit_portal=True,
            send_email=False,
            screening_answers={
                "work_authorization": "Authorized to work in US",
                "years_of_experience": 5,
                "earliest_start_date": "Immediately",
                "salary_expectation": "$130,000",
                "confirmed_by_user": True
            },
            idempotency_key="test_batch_key",
            db=db_session
        )
    )

    # Check batch session status
    status_resp = client.get(f"/api/v1/applications/batch/{session_data['session_id']}", headers=auth_headers)
    assert status_resp.status_code == 200
    batch_status = status_resp.json()
    assert batch_status["status"] == "completed"
    assert batch_status["successful_jobs"] == 1  # Direct API submitted
    assert batch_status["requires_action_jobs"] == 1  # Portal requires user action

    # Verify direct API workspace status
    db_session.expire_all()
    ws_direct = db_session.query(JobApplicationWorkspace).filter(
        JobApplicationWorkspace.user_id == test_user.id,
        JobApplicationWorkspace.job_id == job_direct.id
    ).first()
    assert ws_direct.application_status == "submitted"
    assert ws_direct.application_confirmation_id.startswith("JP-SUB-")

    # Verify portal workspace status
    ws_portal = db_session.query(JobApplicationWorkspace).filter(
        JobApplicationWorkspace.user_id == test_user.id,
        JobApplicationWorkspace.job_id == job_portal.id
    ).first()
    assert ws_portal.application_status == "requires_user_action"

    # Test Duplicate Prevention: Re-running on already submitted job should skip duplicate
    dup_res = asyncio.run(
        ApplicationAdapterManager.execute_application(
            db=db_session,
            user=test_user,
            job=job_direct,
            workspace=ws_direct,
            submit_portal=True,
            send_email=False,
            screening_answers={"confirmed_by_user": True},
            idempotency_key="fresh_key"
        )
    )
    assert dup_res.application_status == "submitted"
    assert "duplicate submission" in dup_res.application_message.lower()

    # Test Safe Retry on requires_user_action / failed
    retry_resp = client.post(f"/api/v1/applications/{job_portal.id}/retry", headers=auth_headers)
    assert retry_resp.status_code == 200
    db_session.refresh(ws_portal)
    assert ws_portal.application_status == "pending"
    assert ws_portal.status == "ready_for_apply"


def test_batch_cancellation(client: TestClient, test_user: User, auth_headers: dict, db_session: Session):
    jobs = []
    for i in range(4):
        job = JobListing(
            source_id=f"cancel_{uuid.uuid4().hex[:6]}",
            source_name="web_portal",
            title=f"Cancel Test Job {i}",
            company="CancelCorp",
            location="Remote",
            country="US",
            url="https://portal.cancelcorp.com/apply",
            description="Testing cancellation.",
            cached_at=datetime.now(timezone.utc)
        )
        db_session.add(job)
        jobs.append(job)
    db_session.commit()

    session = ApplicationRunnerService.create_batch_session(
        db=db_session,
        user_id=test_user.id,
        total_jobs=4
    )

    # Cancel session
    cancel_resp = client.post(f"/api/v1/applications/batch/{session.id}/cancel", headers=auth_headers)
    assert cancel_resp.status_code == 200
    db_session.refresh(session)
    assert session.cancelled is True
    assert session.status == "cancelled"

    # Running process on cancelled session should immediately halt
    asyncio.run(
        ApplicationRunnerService.run_batch_process(
            session_id=session.id,
            user_id=test_user.id,
            job_ids=[j.id for j in jobs],
            submit_portal=True,
            send_email=False,
            screening_answers={},
            idempotency_key=None,
            db=db_session
        )
    )
    db_session.refresh(session)
    assert session.processed_jobs == 0
    assert session.status == "cancelled"
