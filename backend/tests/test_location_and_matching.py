import json
import pytest
from app.core.locations import (
    matches_location_filter,
    normalize_job_location,
    is_remote_eligible_for_country,
    classify_location_hierarchy,
    SUPPORTED_COUNTRIES,
)
from app.models.job import JobListing
from app.models.profile import UserProfile
from app.services.job_matcher import JobMatcher


# =========================================================================
# 1. Location Normalization & Strict Country Boundaries Tests
# =========================================================================

def test_india_rajasthan_strictly_excludes_european_and_foreign_jobs():
    """
    Verifies that selecting India (IN) strictly rejects:
    - Jobs located in Europe (e.g., Berlin, Germany, Dublin, Ireland, London, UK).
    - Jobs indicating 'Remote in Europe' or regional European remote.
    - Jobs with US state abbreviations matching 'IN' (e.g., 'Columbus, IN').
    """
    foreign_locations = [
        ("Remote in Europe", True, None),
        ("Berlin, Germany", False, "DE"),
        ("Dublin, Ireland", False, "IE"),
        ("London, United Kingdom", False, "GB"),
        ("Paris, France", False, "FR"),
        ("Remote (Europe / UK Only)", True, "EU"),
        ("Columbus, IN", False, "US"),          # Columbus, Indiana (USA)
        ("Indianapolis, IN", False, "US"),      # Indianapolis, Indiana (USA)
        ("Austin, TX", False, "US"),
        ("Toronto, ON, Canada", False, "CA"),
    ]

    for loc, is_remote, country in foreign_locations:
        # Check raw country filtering
        assert matches_location_filter(
            job_location=loc,
            job_country=country,
            job_is_remote=is_remote,
            filter_country="IN",
            filter_states=["RJ"]
        ) is False, f"Expected {loc} to be rejected for India + Rajasthan filter"

        # Check country-only filter without states
        assert matches_location_filter(
            job_location=loc,
            job_country=country,
            job_is_remote=is_remote,
            filter_country="IN"
        ) is False, f"Expected {loc} to be rejected for India country filter"


def test_india_rajasthan_accepts_valid_local_and_worldwide_jobs():
    """
    Verifies that selecting India + Rajasthan accepts:
    - Jobs in Jaipur, Jodhpur, Udaipur, Kota (Rajasthan cities).
    - Jobs explicitly mentioning Rajasthan, India.
    - Genuine worldwide remote jobs open to India.
    """
    valid_rajasthan_jobs = [
        ("Jaipur, Rajasthan, India", False, "IN"),
        ("Jodhpur, RJ", False, "IN"),
        ("Udaipur, India", False, "IN"),
        ("Kota, Rajasthan", False, "IN"),
        ("Remote - India (Jaipur)", True, "IN"),
    ]

    for loc, is_remote, country in valid_rajasthan_jobs:
        assert matches_location_filter(
            job_location=loc,
            job_country=country,
            job_is_remote=is_remote,
            filter_country="IN",
            filter_states=["RJ"]
        ) is True, f"Expected {loc} to be accepted for India + Rajasthan"


def test_remote_eligibility_isolation():
    """
    Verifies is_remote_eligible_for_country isolates Worldwide vs. regional remote.
    """
    # India target
    eligible, reason = is_remote_eligible_for_country("Worldwide Remote (Anywhere)", "IN")
    assert eligible is True
    assert "worldwide" in reason.lower()

    eligible, reason = is_remote_eligible_for_country("Remote - India & APAC", "IN")
    assert eligible is True

    eligible, reason = is_remote_eligible_for_country("Remote (Europe Only)", "IN")
    assert eligible is False
    assert "europe" in reason.lower()

    eligible, reason = is_remote_eligible_for_country("Remote (US Only)", "IN")
    assert eligible is False
    assert "north american" in reason.lower()

    # Generic unverified remote without country scope should be rejected under strict country search
    eligible, reason = is_remote_eligible_for_country("Remote", "IN")
    assert eligible is False
    assert "unverified" in reason.lower()


def test_location_normalization_edge_cases():
    """
    Verifies normalize_job_location correctly identifies European, US state abbreviations,
    and Indian cities/states.
    """
    # Columbus, IN should be US, state IN, not India
    norm_columbus = normalize_job_location("Columbus, IN")
    assert norm_columbus["country"] == "US"
    assert norm_columbus["state"] == "IN"

    # Jaipur should be IN, state RJ, city Jaipur
    norm_jaipur = normalize_job_location("Jaipur, India")
    assert norm_jaipur["country"] == "IN"
    assert norm_jaipur["state"] == "RJ"
    assert norm_jaipur["city"] == "Jaipur"

    # Remote in Europe should be EU regional
    norm_eu = normalize_job_location("Remote in Europe", raw_is_remote=True)
    assert norm_eu["country"] == "EU"
    assert norm_eu["remote_scope"] == "regional_europe"


# =========================================================================
# 2. Location Hierarchy Classification & Expansion Tests
# =========================================================================

def test_classify_location_hierarchy():
    """
    Tests classification into: exact city -> nearby radius -> state -> country fallback.
    """
    # 1. Exact city match: Jaipur
    level, explanation = classify_location_hierarchy(
        job_city="Jaipur",
        job_state="RJ",
        job_country="IN",
        job_location="Jaipur, Rajasthan",
        filter_city="Jaipur",
        filter_states=["RJ"],
        filter_country="IN"
    )
    assert level == "city"
    assert "Jaipur" in explanation

    # 2. Nearby radius match: Ajmer is near Jaipur (~130km)
    level, explanation = classify_location_hierarchy(
        job_city="Ajmer",
        job_state="RJ",
        job_country="IN",
        job_location="Ajmer, Rajasthan",
        filter_city="Jaipur",
        filter_states=["RJ"],
        filter_country="IN"
    )
    assert level == "nearby"
    assert "Nearby location" in explanation

    # 3. State-level expansion: Udaipur (different city in RJ, outside radius)
    level, explanation = classify_location_hierarchy(
        job_city="Udaipur",
        job_state="RJ",
        job_country="IN",
        job_location="Udaipur, Rajasthan",
        filter_city="Jaipur",
        filter_states=["RJ"],
        filter_country="IN"
    )
    assert level == "state"
    assert "Rajasthan" in explanation

    # 4. Country-level expansion: Bangalore (in KA, not RJ)
    level, explanation = classify_location_hierarchy(
        job_city="Bengaluru",
        job_state="KA",
        job_country="IN",
        job_location="Bengaluru, Karnataka",
        filter_city="Jaipur",
        filter_states=["RJ"],
        filter_country="IN"
    )
    assert level == "country"
    assert "India" in explanation


# =========================================================================
# 3. Resume-to-Job Truthful Relevance & Guardrails Tests
# =========================================================================

def test_unrelated_profession_is_penalized_below_20_percent():
    """
    Verifies that a Software Engineer resume evaluated against completely unrelated
    professions (Nurse, Delivery Driver, Plumber, Accountant) scores < 20%
    and receives clear truthful explanations rather than inflated scores.
    """
    dev_profile = UserProfile(
        headline="Senior Full Stack Software Engineer",
        skills=json.dumps(["Python", "React", "TypeScript", "FastAPI", "PostgreSQL", "Docker", "AWS"]),
        experiences=json.dumps([
            {"title": "Senior Software Engineer", "company": "Tech Corp", "description": "Built scalable cloud APIs in Python and React"}
        ]),
        education=json.dumps([
            {"degree": "B.Tech in Computer Science", "institution": "Indian Institute of Technology"}
        ]),
        location="Jaipur, Rajasthan, India"
    )

    unrelated_jobs = [
        JobListing(
            title="Registered Nurse (ICU)",
            company="Metro Health Hospital",
            location="Jaipur, Rajasthan",
            description="Provide critical patient care, administer IV medications, collaborate with doctors in the ICU.",
            skills_required=json.dumps(["Nursing", "Patient Care", "BLS", "ACLS"])
        ),
        JobListing(
            title="Delivery Operations Driver & Fleet Associate",
            company="FastLogistics India",
            location="Jaipur, Rajasthan",
            description="Manage van parcel delivery schedules, route optimization on foot, and vehicle loading.",
            skills_required=json.dumps(["Driving License", "Route Management", "Loading"])
        ),
        JobListing(
            title="Senior Tax Accountant",
            company="FinAudit Partners",
            location="Jaipur, Rajasthan",
            description="Manage corporate GST filings, quarterly tax balance sheets, and audit reports.",
            skills_required=json.dumps(["GST", "Corporate Tax", "Tally", "Auditing"])
        )
    ]

    for job in unrelated_jobs:
        match = JobMatcher.evaluate(profile=dev_profile, job=job)
        assert match.score < 20.0, f"Expected {job.title} to score < 20.0, got {match.score}"
        assert any("different profession" in r.lower() or "unrelated" in r.lower() or "different field" in r.lower() for r in match.reasons), \
            f"Expected truthful mismatch explanation for {job.title}, got: {match.reasons}"


def test_seniority_mismatch_penalty():
    """
    Verifies that a Junior profile applied to a Principal/Director role receives a seniority penalty.
    """
    junior_profile = UserProfile(
        headline="Junior Python Developer",
        skills=json.dumps(["Python", "Django", "Git"]),
        experiences=json.dumps([
            {"title": "Junior Python Developer", "company": "Small Web Agency", "description": "Wrote Django templates and unit tests for 1 year"}
        ]),
        education=json.dumps([
            {"degree": "B.S. in Information Technology", "institution": "State University"}
        ]),
        location="Jaipur, Rajasthan"
    )

    lead_job = JobListing(
        title="Principal Software Architect & Engineering Director",
        company="Enterprise Tech",
        location="Jaipur, Rajasthan",
        description="Lead enterprise architecture across 12 engineering teams. 10+ years required.",
        skills_required=json.dumps(["Python", "System Architecture", "Executive Leadership"])
    )

    match = JobMatcher.evaluate(profile=junior_profile, job=lead_job)
    # Junior applying to Principal Architect capped below 50.0%
    assert match.score < 50.0
    assert any("seniority" in r.lower() or "leadership" in r.lower() for r in match.reasons)


def test_strong_technical_match_scores_high():
    """
    Verifies that a Software Engineer resume with matching skills and title receives a score >= 75%.
    """
    dev_profile = UserProfile(
        headline="Senior Full Stack Software Engineer",
        skills=json.dumps(["Python", "React", "TypeScript", "FastAPI", "PostgreSQL", "Docker"]),
        experiences=json.dumps([
            {"title": "Senior Software Engineer", "company": "SaaS Platform", "description": "Built FastAPI microservices and React dashboards"}
        ]),
        education=json.dumps([
            {"degree": "B.Tech in Computer Science", "institution": "Tech University"}
        ]),
        location="Jaipur, Rajasthan, India"
    )

    strong_job = JobListing(
        title="Senior Full Stack Python/React Developer",
        company="Global SaaS Ltd",
        location="Jaipur, Rajasthan, India",
        country="IN",
        state="RJ",
        city="Jaipur",
        description="Looking for a Senior Full Stack Engineer proficient in Python, FastAPI, React, and PostgreSQL.",
        skills_required=json.dumps(["Python", "React", "FastAPI", "PostgreSQL"])
    )

    match = JobMatcher.evaluate(profile=dev_profile, job=strong_job)
    assert match.score >= 75.0
    matched_lower = [s.lower() for s in match.matched_skills]
    assert "python" in matched_lower
    assert "react" in matched_lower
    assert "fastapi" in matched_lower


# =========================================================================
# 4. Search API Multi-Tier Hierarchy Integration Tests
# =========================================================================

def test_search_api_india_rajasthan_hierarchy(client, auth_headers, db_session):
    """
    Seeds jobs across Jaipur, Udaipur, Berlin, and Columbus.
    Searches with country=IN, state=RJ, city=Jaipur.
    Verifies:
    1. Zero European jobs returned.
    2. Jaipur job is tagged level 'city'.
    3. Udaipur job is tagged level 'state'.
    4. Location explanation and expansion notices are populated.
    """
    jobs = [
        JobListing(
            source_id="t-jaipur-1",
            source_name="arbeitnow",
            title="Senior Python Developer",
            company="Pink City Software",
            location="Jaipur, Rajasthan, India",
            country="IN",
            state="RJ",
            city="Jaipur",
            is_remote=False,
            url="https://example.com/job/jaipur-1",
            skills_required=json.dumps(["Python", "FastAPI"]),
            description="Python developer in Jaipur, Rajasthan.",
            is_active=True
        ),
        JobListing(
            source_id="t-udaipur-1",
            source_name="jobicy",
            title="Full Stack React Engineer",
            company="Lake City Tech",
            location="Udaipur, Rajasthan, India",
            country="IN",
            state="RJ",
            city="Udaipur",
            is_remote=False,
            url="https://example.com/job/udaipur-1",
            skills_required=json.dumps(["React", "TypeScript"]),
            description="React engineer in Udaipur, Rajasthan.",
            is_active=True
        ),
        JobListing(
            source_id="t-berlin-1",
            source_name="arbeitnow",
            title="Berlin Python Specialist",
            company="Spree GmbH",
            location="Berlin, Germany",
            country="DE",
            city="Berlin",
            is_remote=False,
            url="https://example.com/job/berlin-1",
            skills_required=json.dumps(["Python"]),
            description="Python developer in Berlin.",
            is_active=True
        ),
        JobListing(
            source_id="t-euro-remote-1",
            source_name="remoteok",
            title="Europe DevOps Engineer",
            company="EuroCloud",
            location="Remote (Europe Only)",
            country="EU",
            is_remote=True,
            url="https://example.com/job/euro-1",
            skills_required=json.dumps(["Docker", "Kubernetes"]),
            description="DevOps for European timezones.",
            is_active=True
        ),
        JobListing(
            source_id="t-columbus-1",
            source_name="remoteok",
            title="Indiana Systems Analyst",
            company="Midwest Logistics",
            location="Columbus, IN",
            country="US",
            state="IN",
            is_remote=False,
            url="https://example.com/job/columbus-1",
            skills_required=json.dumps(["SQL"]),
            description="On-site analyst in Columbus, Indiana, US.",
            is_active=True
        )
    ]

    for j in jobs:
        db_session.add(j)
    db_session.commit()

    # Search with country=IN, state=RJ, city=Jaipur
    resp = client.get("/api/v1/jobs/search?country=IN&states=RJ&city=Jaipur", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    returned_titles = [j["title"] for j in data["jobs"]]

    # Verify Strict Boundary: Absolutely NO European or US jobs
    assert "Berlin Python Specialist" not in returned_titles
    assert "Europe DevOps Engineer" not in returned_titles
    assert "Indiana Systems Analyst" not in returned_titles

    # Verify Jaipur job is present
    jaipur_job = next((j for j in data["jobs"] if j["title"] == "Senior Python Developer"), None)
    assert jaipur_job is not None
    assert jaipur_job["expansion_level"] == "city"
    assert "Jaipur" in jaipur_job["location_explanation"]

    # Verify Udaipur job is present and recognized as state level
    udaipur_job = next((j for j in data["jobs"] if j["title"] == "Full Stack React Engineer"), None)
    assert udaipur_job is not None
    assert udaipur_job["expansion_level"] == "state"
    assert "Rajasthan" in udaipur_job["location_explanation"]
