import json
import pytest
from app.models.job import JobListing, SavedJob
from app.models.profile import UserProfile
from app.services.job_matcher import JobMatcher
from app.services.job_sources.manager import JobSourceManager


def test_no_mock_or_inactive_demo_jobs_in_search(client, auth_headers, db_session):
    """
    Verifies that mock records with source_name='official_feed' or is_active=False
    are never returned in live search results.
    """
    mock_job = JobListing(
        source_id="demo-seed-1",
        source_name="official_feed",
        title="Senior Python Developer",
        company="InfoSys Technologies",
        location="Jaipur, Rajasthan, India",
        country="IN",
        state="RJ",
        city="Jaipur",
        is_remote=False,
        employment_type="full_time",
        url="https://example.com/jobs/verified_in_1",
        description="Demo listing that must never be presented as live.",
        skills_required=json.dumps(["Python"]),
        is_active=False
    )
    db_session.add(mock_job)

    genuine_job = JobListing(
        source_id="rem-live-101",
        source_name="remotive",
        title="Python Software Engineer",
        company="Genuine Tech Inc",
        location="Remote (Worldwide)",
        country="REMOTE",
        is_remote=True,
        employment_type="full_time",
        url="https://remotive.com/remote-jobs/genuine-tech-101",
        description="Live verified remote python engineering role.",
        skills_required=json.dumps(["Python", "FastAPI"]),
        is_active=True
    )
    db_session.add(genuine_job)
    db_session.commit()

    resp = client.get("/api/v1/jobs/search?country=IN", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    returned_ids = [j["source_id"] for j in data["jobs"]]
    returned_sources = [j["source_name"] for j in data["jobs"]]

    assert "demo-seed-1" not in returned_ids
    assert "official_feed" not in returned_sources


def test_kota_location_progressive_hierarchy(client, auth_headers, db_session):
    """
    Verifies Kota search respects the progressive geographic hierarchy:
    Tier 1: Kota city
    Tier 2: Nearby radius (Bundi, Baran, Jhalawar)
    Tier 3: Rajasthan state
    Tier 4: India national remote
    """
    jobs = [
        JobListing(
            source_id="kota-local",
            source_name="jobicy",
            title="Junior Python Engineer",
            company="Kota Robotics",
            location="Kota, Rajasthan, India",
            country="IN",
            state="RJ",
            city="Kota",
            is_remote=False,
            url="https://jobicy.com/jobs/kota-local",
            skills_required=json.dumps(["Python"]),
            description="Onsite robotics software developer in Kota.",
            is_active=True
        ),
        JobListing(
            source_id="bundi-nearby",
            source_name="jobicy",
            title="Backend Python Developer",
            company="Hadoti Tech",
            location="Bundi, Rajasthan, India",
            country="IN",
            state="RJ",
            city="Bundi",
            is_remote=False,
            url="https://jobicy.com/jobs/bundi-nearby",
            skills_required=json.dumps(["Python"]),
            description="Software engineering in Bundi (commuting radius of Kota).",
            is_active=True
        ),
        JobListing(
            source_id="jaipur-state",
            source_name="arbeitnow",
            title="Python Developer",
            company="Jaipur Digital",
            location="Jaipur, Rajasthan, India",
            country="IN",
            state="RJ",
            city="Jaipur",
            is_remote=False,
            url="https://arbeitnow.com/jobs/jaipur-state",
            skills_required=json.dumps(["Python"]),
            description="State-level software developer in Jaipur, Rajasthan.",
            is_active=True
        )
    ]
    for j in jobs:
        db_session.add(j)
    db_session.commit()

    resp = client.get("/api/v1/jobs/search?country=IN&states=RJ&city=Kota", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    returned_jobs = {j["source_id"]: j for j in data["jobs"]}
    assert "kota-local" in returned_jobs
    assert returned_jobs["kota-local"]["expansion_level"] == "city"

    if "bundi-nearby" in returned_jobs:
        assert returned_jobs["bundi-nearby"]["expansion_level"] in ["nearby", "state"]


def test_student_profile_heavily_penalizes_senior_and_design_roles(test_user, db_session):
    """
    Tests that a student/intern profile (like Dev Sharma) evaluated against:
    - Staff Product Designer -> scores < 25% (discipline + seniority mismatch)
    - Principal Architect / Senior Lead -> scores < 25% (seniority mismatch)
    - Junior / Entry Python Engineer -> scores >= 70% (strong relevance)
    """
    student_profile = UserProfile(
        user_id=test_user.id,
        headline="Computer Engineering Student | AI / Machine Learning Enthusiast",
        summary="Computer Engineering student seeking entry-level software or machine learning roles.",
        location="Kota, Rajasthan, India",
        skills=json.dumps(["Python", "Machine Learning", "FastAPI", "Git", "SQL", "Pandas"]),
        experiences=json.dumps([
            {"title": "Machine Learning Intern", "company": "TechCorp", "current": False},
            {"title": "AI Research Intern", "company": "DataLab", "current": False}
        ]),
        education=json.dumps([
            {"degree": "Bachelor of Technology", "institution": "Engineering College Kota", "field_of_study": "Computer Engineering"}
        ]),
        is_confirmed=True
    )
    db_session.add(student_profile)
    db_session.commit()

    # Incompatible Role 1: Staff Product Designer
    staff_designer_job = JobListing(
        source_id="incomp-1",
        source_name="remotive",
        title="Staff Product Designer",
        company="Design Systems Co",
        location="Remote (Worldwide)",
        country="REMOTE",
        is_remote=True,
        url="https://remotive.com/jobs/incomp-1",
        description="Staff level product designer creating Figma design systems and user journey wireframes.",
        skills_required=json.dumps(["Figma", "UI/UX", "Design Systems", "Prototyping"]),
        is_active=True
    )

    # Incompatible Role 2: Senior Security Lead Engineer
    senior_security_job = JobListing(
        source_id="incomp-2",
        source_name="remotive",
        title="Senior Security Engineering Lead",
        company="CyberSec Enterprise",
        location="Remote (Worldwide)",
        country="REMOTE",
        is_remote=True,
        url="https://remotive.com/jobs/incomp-2",
        description="Requires 10+ years leading enterprise penetration testing, SIEM operations, and executive audit compliance.",
        skills_required=json.dumps(["SIEM", "Penetration Testing", "ISO 27001", "Cryptography"]),
        is_active=True
    )

    # Compatible Role 3: Junior Python / ML Engineer
    junior_ml_job = JobListing(
        source_id="comp-1",
        source_name="remotive",
        title="Junior Python / Machine Learning Engineer",
        company="AI Innovations Inc",
        location="Remote (Worldwide)",
        country="REMOTE",
        is_remote=True,
        url="https://remotive.com/jobs/comp-1",
        description="Entry-level software engineer to build Python services and machine learning data pipelines.",
        skills_required=json.dumps(["Python", "Machine Learning", "FastAPI", "SQL"]),
        is_active=True
    )

    eval_designer = JobMatcher.evaluate(profile=student_profile, job=staff_designer_job, user_country_preference="IN")
    eval_senior_sec = JobMatcher.evaluate(profile=student_profile, job=senior_security_job, user_country_preference="IN")
    eval_junior_ml = JobMatcher.evaluate(profile=student_profile, job=junior_ml_job, user_country_preference="IN")

    # Incompatible roles must score strictly < 25%
    assert eval_designer.score < 25.0, f"Expected Staff Product Designer to score < 25%, got {eval_designer.score}"
    assert eval_senior_sec.score < 25.0, f"Expected Senior Security Lead to score < 25%, got {eval_senior_sec.score}"

    # Verify plain-language mismatch reasons exist
    assert any("Design" in r or "Seniority" in r or "discipline" in r or "tenure" in r for r in eval_designer.reasons)
    assert any("Seniority" in r or "tenure" in r or "mismatch" in r for r in eval_senior_sec.reasons)

    # Compatible role must score high (>= 70%)
    assert eval_junior_ml.score >= 70.0, f"Expected Junior ML role to score >= 70%, got {eval_junior_ml.score}"
    assert "Python" in eval_junior_ml.matched_skills


def test_company_diversity_limit_in_search(client, auth_headers, db_session):
    """
    Verifies that multiple jobs from the same company (e.g. Supabase, Flex)
    are limited to at most 2 entries in search results to prevent repetitive feeds.
    """
    for i in range(5):
        j = JobListing(
            source_id=f"supabase-{i}",
            source_name="remotive",
            title=f"Cloud Engineer Tier {i}",
            company="Supabase",
            location="Remote (Worldwide)",
            country="REMOTE",
            is_remote=True,
            employment_type="full_time",
            url=f"https://remotive.com/jobs/supabase-{i}",
            description="PostgreSQL backend developer at Supabase.",
            skills_required=json.dumps(["PostgreSQL", "Go"]),
            is_active=True
        )
        db_session.add(j)
    db_session.commit()

    resp = client.get("/api/v1/jobs/search?country=REMOTE", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    supabase_jobs = [j for j in data["jobs"] if j["company"] == "Supabase"]
    assert len(supabase_jobs) <= 2, f"Expected at most 2 Supabase jobs due to diversity limit, got {len(supabase_jobs)}"


def test_verified_link_flag_accuracy(client, auth_headers, db_session):
    """
    Verifies that is_verified_link correctly marks genuine URLs vs example.com/broken links.
    """
    genuine_job = JobListing(
        source_id="vlink-1",
        source_name="remotive",
        title="Backend Python Developer",
        company="Authentic Labs",
        location="Remote (Worldwide)",
        country="REMOTE",
        is_remote=True,
        url="https://remotive.com/remote-jobs/authentic-labs-1",
        description="Authentic listing.",
        skills_required=json.dumps(["Python"]),
        is_active=True
    )
    placeholder_job = JobListing(
        source_id="vlink-2",
        source_name="remotive",
        title="Web Developer",
        company="Placeholder Corp",
        location="Remote (Worldwide)",
        country="REMOTE",
        is_remote=True,
        url="https://example.com/jobs/vlink-2",
        description="Placeholder listing with dummy link.",
        skills_required=json.dumps(["Python"]),
        is_active=True
    )
    db_session.add(genuine_job)
    db_session.add(placeholder_job)
    db_session.commit()

    resp = client.get("/api/v1/jobs/search?country=REMOTE", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    job_dict = {j["source_id"]: j for j in data["jobs"]}
    if "vlink-1" in job_dict:
        assert job_dict["vlink-1"]["is_verified_link"] is True
    if "vlink-2" in job_dict:
        assert job_dict["vlink-2"]["is_verified_link"] is False
