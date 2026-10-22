import json
import pytest
from app.models.application import JobApplicationWorkspace, RecruiterContact
from app.models.job import JobListing, SavedJob
from app.models.profile import UserProfile
from app.models.user import User
from app.services.contact_discovery import ContactDiscoveryService
from app.services.content_generator import (
    DuplicateOutreachDetector,
    LocalContentGenerator,
)


def test_contact_discovery_explicit_email_in_posting(db_session):
    """
    Ensures an email explicitly written in the job description is labeled VERIFIED.
    """
    job = JobListing(
        source_id="test_explicit_1",
        source_name="arbeitnow",
        title="Full Stack Engineer",
        company="Acme Corp",
        location="Remote",
        url="https://arbeitnow.com/jobs/acme-full-stack",
        description=(
            "We are looking for a Senior Full Stack Engineer. "
            "Please send your resume to jobs@acmecorp.io or contact our hiring manager John Doe."
        )
    )
    db_session.add(job)
    db_session.commit()

    contact = ContactDiscoveryService.discover_contact_for_job(job)
    assert contact.email == "jobs@acmecorp.io"
    assert contact.verification_status == "VERIFIED"
    assert contact.confidence_score == 1.0
    assert "John Doe" in (contact.name or "")


def test_contact_discovery_inferred_from_company_domain(db_session):
    """
    Ensures domain inference is labeled INFERRED (never presented as verified).
    """
    job = JobListing(
        source_id="test_inferred_1",
        source_name="jobicy",
        title="Frontend Developer",
        company="TechStartup",
        location="Remote",
        url="https://techstartup.io/jobs/frontend-dev",
        description="Join our team building modern web applications. Fast-paced environment."
    )
    db_session.add(job)
    db_session.commit()

    contact = ContactDiscoveryService.discover_contact_for_job(job)
    assert contact.email == "careers@techstartup.io"
    assert contact.verification_status == "INFERRED"
    assert contact.confidence_score < 1.0
    assert "verify" in contact.notes.lower()


def test_contact_discovery_aggregator_no_email_not_found(db_session):
    """
    Ensures that when only aggregator URL is available and no email is in text,
    it is honestly labeled NOT_FOUND rather than fabricating an address.
    """
    job = JobListing(
        source_id="test_none_1",
        source_name="remoteok",
        title="DevOps Engineer",
        company="CloudyDays",
        location="Remote",
        url="https://remoteok.com/remote-jobs/12345",
        description="Looking for an engineer to maintain Kubernetes clusters and CI/CD pipelines."
    )
    db_session.add(job)
    db_session.commit()

    contact = ContactDiscoveryService.discover_contact_for_job(job)
    assert contact.email is None
    assert contact.verification_status == "NOT_FOUND"
    assert contact.confidence_score == 0.0


def test_local_cover_letter_highlights_verified_skills_only(db_session):
    """
    Tests that generated cover letter includes actual skills from resume
    and does not invent unsupported claims.
    """
    profile = UserProfile(
        full_name="Alice Developer",
        headline="Senior Backend Engineer",
        email="alice@example.com",
        skills=json.dumps(["Python", "FastAPI", "PostgreSQL", "Docker"]),
        experiences=json.dumps([
            {"company": "Apex Labs", "title": "Lead Python Engineer", "description": "Scaled APIs"}
        ]),
        projects=json.dumps([
            {"name": "JobMatcher Pro", "description": "Built asynchronous matching pipeline in Python"}
        ])
    )

    job = JobListing(
        source_id="job_py_1",
        source_name="arbeitnow",
        title="Python Developer",
        company="Innovatech",
        location="Remote",
        url="https://example.com/job/1",
        description="We need a Python Developer proficient in FastAPI and Docker."
    )

    letter = LocalContentGenerator.generate_cover_letter(profile, job, tone="professional", template_style="modern")
    assert "Alice Developer" in letter
    assert "Innovatech" in letter
    assert "Python Developer" in letter
    assert "FastAPI" in letter
    assert "Docker" in letter
    assert "Apex Labs" in letter
    assert "JobMatcher Pro" in letter
    # Ensure unmentioned skills (e.g. Haskell, Swift) are NOT invented
    assert "Haskell" not in letter
    assert "Swift" not in letter


def test_cover_letter_handles_missing_resume_fields_gracefully():
    """
    Ensures that when resume profile has missing skills/experiences,
    the generator doesn't crash or hallucinate false credentials.
    """
    minimal_profile = UserProfile(
        full_name="Bob Starter",
        email="bob@example.com",
        skills="[]",
        experiences="[]",
        projects="[]"
    )

    job = JobListing(
        source_id="job_entry_1",
        source_name="remoteok",
        title="Junior Web Developer",
        company="PixelStudio",
        location="Remote",
        url="https://example.com/job/2",
        description="Great entry-level opportunity for a motivated web developer."
    )

    letter = LocalContentGenerator.generate_cover_letter(minimal_profile, job, tone="concise", template_style="minimal")
    assert "Bob Starter" in letter
    assert "PixelStudio" in letter
    assert "Junior Web Developer" in letter
    # No crashed empty string or hallucinated company
    assert len(letter) > 100


def test_recruiter_email_generator_and_duplicate_prevention(db_session):
    """
    Tests recruiter email generation and verifies the duplicate outreach detector.
    """
    # 1. Setup user
    user = User(email="charlie@test.com", hashed_password="pw", full_name="Charlie Test")
    db_session.add(user)
    db_session.commit()

    # 2. Setup two jobs at the same company
    job1 = JobListing(
        source_id="job_dup_1",
        source_name="arbeitnow",
        title="Backend Engineer",
        company="MegaCorp",
        location="Remote",
        url="https://example.com/job/3",
        description="Backend engineering role."
    )
    job2 = JobListing(
        source_id="job_dup_2",
        source_name="arbeitnow",
        title="Platform Engineer",
        company="MegaCorp",
        location="Remote",
        url="https://example.com/job/4",
        description="Platform infrastructure role."
    )
    db_session.add_all([job1, job2])
    db_session.commit()

    # 3. Create workspace with email draft for job 1
    ws1 = JobApplicationWorkspace(
        user_id=user.id,
        job_id=job1.id,
        email_subject="Application: Backend Engineer",
        email_body="Dear Hiring Team, I am writing to apply...",
        contact_email="recruiting@megacorp.com"
    )
    db_session.add(ws1)
    db_session.commit()

    # 4. Check duplicate for job 2 (same company MegaCorp)
    is_dup, warning = DuplicateOutreachDetector.check_duplicate(
        db=db_session,
        user_id=user.id,
        current_job=job2,
        contact_email="recruiting@megacorp.com"
    )
    assert is_dup is True
    assert "MegaCorp" in warning
    assert "duplicate" in warning.lower()


def test_applications_api_flow(client, auth_headers, db_session):
    """
    Integration test testing the complete applications API workflow:
    - Queue listing
    - Workspace retrieval & contact discovery
    - Cover letter generation & editing
    - Recruiter email generation & editing
    - User contact verification
    - Status updates (draft -> reviewed -> ready_for_apply)
    """
    # Create test job
    job = JobListing(
        source_id="api_test_job_1",
        source_name="arbeitnow",
        title="Full Stack Software Engineer",
        company="ScaleUp Solutions",
        location="New York, NY",
        url="https://scaleup.io/careers/fullstack",
        description="We are seeking a Full Stack Software Engineer. Send inquiries to talent@scaleup.io.",
        skills_required=json.dumps(["React", "FastAPI", "PostgreSQL"])
    )
    db_session.add(job)
    db_session.commit()

    # Mark as selected for apply in SavedJob
    saved = SavedJob(
        user_id=1,  # from auth_headers
        job_id=job.id,
        is_selected_for_apply=True
    )
    db_session.add(saved)
    db_session.commit()

    # 1. Check queue
    resp = client.get("/api/v1/applications/queue", headers=auth_headers)
    assert resp.status_code == 200
    queue_data = resp.json()
    assert queue_data["total_queued"] >= 1
    item = next(i for i in queue_data["items"] if i["job_id"] == job.id)
    assert item["title"] == "Full Stack Software Engineer"
    assert item["company"] == "ScaleUp Solutions"

    # 2. Get workspace (auto-discovers contact)
    resp = client.get(f"/api/v1/applications/{job.id}", headers=auth_headers)
    assert resp.status_code == 200
    ws_data = resp.json()
    assert ws_data["job_title"] == "Full Stack Software Engineer"
    assert ws_data["contact_email"] == "talent@scaleup.io"
    assert ws_data["contact_verification_status"] == "VERIFIED"

    # 3. Generate cover letter
    resp = client.post(
        f"/api/v1/applications/{job.id}/cover-letter/generate",
        json={"tone": "enthusiastic", "template_style": "modern"},
        headers=auth_headers
    )
    assert resp.status_code == 200
    assert "ScaleUp Solutions" in resp.json()["cover_letter_content"]

    # 4. Edit cover letter
    resp = client.put(
        f"/api/v1/applications/{job.id}/cover-letter",
        json={
            "content": "Customized cover letter content for ScaleUp.",
            "tone": "professional",
            "include_cover_letter": True
        },
        headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["cover_letter_content"] == "Customized cover letter content for ScaleUp."

    # 5. Generate recruiter email
    resp = client.post(
        f"/api/v1/applications/{job.id}/email/generate",
        json={"tone": "concise"},
        headers=auth_headers
    )
    assert resp.status_code == 200
    email_data = resp.json()
    assert email_data["email_subject"] is not None
    assert "Full Stack Software Engineer" in email_data["email_subject"]
    assert "ScaleUp Solutions" in email_data["email_body"]

    # 6. User verifies / edits contact
    resp = client.put(
        f"/api/v1/applications/{job.id}/contact",
        json={
            "name": "Jane Talent Lead",
            "email": "jane@scaleup.io",
            "role": "Lead Technical Recruiter",
            "verification_status": "USER_VERIFIED"
        },
        headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["contact_name"] == "Jane Talent Lead"
    assert resp.json()["contact_email"] == "jane@scaleup.io"
    assert resp.json()["contact_verification_status"] == "USER_VERIFIED"

    # 7. Update status to reviewed and ready_for_apply
    resp = client.put(
        f"/api/v1/applications/{job.id}/status",
        json={"status": "ready_for_apply"},
        headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready_for_apply"
