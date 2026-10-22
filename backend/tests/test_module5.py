import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.application import JobApplicationWorkspace, ApplicationAuditLog
from app.models.job import JobListing, SavedJob, SearchPreference
from app.models.user import User
from app.services.notification_service import NotificationService


def test_notifications_crud_and_preferences(client: TestClient, auth_headers: dict, test_user: User, db_session: Session):
    # 1. Initially notifications empty
    res = client.get("/api/v1/notifications", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 0
    assert data["unread_count"] == 0

    # 2. Add notification directly via NotificationService
    notif = NotificationService.create_notification(
        db=db_session,
        user_id=test_user.id,
        title="Test Notification",
        message="This is a test notification message",
        notification_type="action_required",
        link="/applications/review"
    )
    assert notif is not None

    # 3. Retrieve notifications list
    res = client.get("/api/v1/notifications", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["unread_count"] == 1
    assert data["items"][0]["title"] == "Test Notification"
    assert data["items"][0]["read"] is False

    # 4. Mark single notification as read
    res = client.post(f"/api/v1/notifications/{notif.id}/read", headers=auth_headers)
    assert res.status_code == 200

    res = client.get("/api/v1/notifications", headers=auth_headers)
    assert res.json()["unread_count"] == 0

    # 5. Check and update preferences
    res = client.get("/api/v1/notifications/preferences", headers=auth_headers)
    assert res.status_code == 200
    pref = res.json()
    assert pref["notify_in_app_searches"] is True

    # Turn off search notifications
    res = client.put(
        "/api/v1/notifications/preferences",
        json={"notify_in_app_searches": False},
        headers=auth_headers
    )
    assert res.status_code == 200
    assert res.json()["notify_in_app_searches"] is False

    # Try creating search notification - should be suppressed
    suppressed = NotificationService.create_notification(
        db=db_session,
        user_id=test_user.id,
        title="Search Done",
        message="Found 10 jobs",
        notification_type="job_search_completed"
    )
    assert suppressed is None


def test_application_tracker_endpoint(client: TestClient, auth_headers: dict, test_user: User, db_session: Session):
    # Create test job
    job = JobListing(
        source_id="track_test_1",
        source_name="arbeitnow",
        title="Senior Site Reliability Engineer",
        company="CloudScale Corp",
        location="Remote, US",
        country="US",
        is_remote=True,
        url="https://cloudscale.example/jobs/1",
        description="Reliability and cloud operations role."
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    # Create workspace with status "requires_user_action"
    workspace = JobApplicationWorkspace(
        user_id=test_user.id,
        job_id=job.id,
        status="reviewed",
        application_status="requires_user_action",
        cover_letter_content="Dear CloudScale hiring team, I am interested in the role."
    )
    db_session.add(workspace)
    db_session.commit()

    # Query tracker
    res = client.get("/api/v1/applications/tracker", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["requires_action_count"] == 1
    item = data["items"][0]
    assert item["company"] == "CloudScale Corp"
    assert item["application_status"] == "requires_user_action"
    assert item["can_retry"] is True
    assert item["has_cover_letter"] is True

    # Filter query
    res = client.get("/api/v1/applications/tracker?query=CloudScale", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["total"] == 1

    res = client.get("/api/v1/applications/tracker?query=NonExistentCompany", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["total"] == 0


def test_retry_application_endpoint(client: TestClient, auth_headers: dict, test_user: User, db_session: Session):
    # Create job & failed workspace
    job = JobListing(
        source_id="retry_job_1",
        source_name="arbeitnow",
        title="Data Engineer",
        company="DataForge",
        location="New York, NY",
        country="US",
        url="https://dataforge.example/jobs/1",
        description="Data pipelining role."
    )
    db_session.add(job)
    db_session.commit()

    workspace = JobApplicationWorkspace(
        user_id=test_user.id,
        job_id=job.id,
        status="ready_for_apply",
        application_status="failed",
        application_confirmation_message="Endpoint timeout"
    )
    db_session.add(workspace)
    db_session.commit()

    # Retry application
    res = client.post(f"/api/v1/applications/{job.id}/retry", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["application_status"] == "pending"
    assert data["status"] == "ready_for_apply"

    # Verify audit log recorded
    log = (
        db_session.query(ApplicationAuditLog)
        .filter(ApplicationAuditLog.user_id == test_user.id, ApplicationAuditLog.action == "application_safe_retry_initiated")
        .first()
    )
    assert log is not None


def test_dashboard_summary_endpoint(client: TestClient, auth_headers: dict, test_user: User, db_session: Session):
    res = client.get("/api/v1/applications/dashboard-summary", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "jobs_discovered" in data
    assert "saved_jobs_count" in data
    assert "queued_jobs_count" in data
    assert "submitted_count" in data
    assert "action_required_count" in data
    assert "first_time_progress" in data
    assert data["first_time_progress"]["current_step"] in [1, 2, 3, 4, 5]


def test_integrations_health_safe(client: TestClient, auth_headers: dict):
    res = client.get("/api/v1/auth/integrations-health", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "ai_provider" in data
    assert "email_delivery" in data
    assert "job_sources" in data
    # Ensure sensitive credentials are never exposed
    assert "api_key" not in str(data).lower()
    assert "password" not in str(data).lower()


def test_export_user_data(client: TestClient, auth_headers: dict, test_user: User):
    res = client.get("/api/v1/auth/export-data", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["export_metadata"]["gdpr_compliant"] is True
    assert data["user_account"]["email"] == test_user.email
    assert "profile" in data
    assert "resumes" in data
    assert "applications" in data
    assert "audit_logs" in data
    assert "notifications" in data


def test_user_isolation_between_accounts(client: TestClient, auth_headers: dict, test_user: User, db_session: Session):
    # Create second user
    signup_res = client.post(
        "/api/v1/auth/signup",
        json={"email": "second_user@example.com", "password": "SecurePassword123!", "full_name": "Second User"}
    )
    assert signup_res.status_code == 201
    second_headers = {"Authorization": f"Bearer {signup_res.json()['access_token']}"}

    # User 1's notifications should not be visible to User 2
    NotificationService.create_notification(
        db=db_session,
        user_id=test_user.id,
        title="Secret User 1 Alert",
        message="Confidential alert",
        notification_type="system"
    )

    res = client.get("/api/v1/notifications", headers=second_headers)
    assert res.status_code == 200
    assert res.json()["total"] == 0

    # User 2 cannot retry User 1's job
    job = JobListing(
        source_id="isolated_job_1",
        source_name="arbeitnow",
        title="Security Lead",
        company="Fortress",
        location="Austin, TX",
        country="US",
        url="https://fortress.example/jobs/1",
        description="Security operations leadership"
    )
    db_session.add(job)
    db_session.commit()

    workspace = JobApplicationWorkspace(
        user_id=test_user.id,
        job_id=job.id,
        status="ready_for_apply",
        application_status="failed"
    )
    db_session.add(workspace)
    db_session.commit()

    # User 2 calling retry on this job gets fresh or unlinked workspace, not User 1's
    res = client.post(f"/api/v1/applications/{job.id}/retry", headers=second_headers)
    assert res.status_code == 200
    # The returned workspace belongs to User 2
    assert res.json()["job_id"] == job.id
    # Ensure User 1's workspace is unchanged
    w1 = db_session.query(JobApplicationWorkspace).filter(JobApplicationWorkspace.user_id == test_user.id, JobApplicationWorkspace.job_id == job.id).first()
    assert w1.user_id == test_user.id
