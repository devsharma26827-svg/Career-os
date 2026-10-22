import json
import pytest
from app.core.locations import matches_location_filter
from app.models.job import JobListing, SavedJob, SearchPreference
from app.models.profile import UserProfile
from app.services.job_matcher import JobMatcher
from app.services.job_sources.manager import JobSourceManager


def test_location_filtering_strict_country_check():
    # US filter should match US jobs and reject UK / Germany jobs
    assert matches_location_filter(job_location="San Francisco, CA", filter_country="US") is True
    assert matches_location_filter(job_location="New York, NY", filter_country="US") is True
    assert matches_location_filter(job_location="Berlin, Germany", filter_country="US") is False
    assert matches_location_filter(job_location="London, United Kingdom", filter_country="US") is False

    # GB filter should match UK jobs and reject US jobs
    assert matches_location_filter(job_location="London, UK", filter_country="GB") is True
    assert matches_location_filter(job_location="Edinburgh, Scotland", filter_country="GB") is True
    assert matches_location_filter(job_location="Austin, Texas", filter_country="GB") is False

    # CA (Canada) filter
    assert matches_location_filter(job_location="Toronto, Ontario, Canada", filter_country="CA") is True
    assert matches_location_filter(job_location="Seattle, WA", filter_country="CA") is False


def test_location_filtering_multiple_states_selection():
    # User selects US with states: ["CA", "NY"]
    assert matches_location_filter(
        job_location="San Francisco, CA",
        filter_country="US",
        filter_states=["CA", "NY"]
    ) is True

    assert matches_location_filter(
        job_location="New York, NY",
        filter_country="US",
        filter_states=["CA", "NY"]
    ) is True

    # Job in Texas should be filtered out
    assert matches_location_filter(
        job_location="Austin, TX",
        filter_country="US",
        filter_states=["CA", "NY"]
    ) is False

    # Job in Florida should be filtered out
    assert matches_location_filter(
        job_location="Miami, Florida",
        filter_country="US",
        filter_states=["CA", "NY"]
    ) is False


def test_location_filtering_remote_only():
    # remote_only=True should only pass remote positions
    assert matches_location_filter(
        job_location="Anywhere (Remote)",
        job_is_remote=True,
        remote_only=True
    ) is True

    assert matches_location_filter(
        job_location="Chicago, IL",
        job_is_remote=False,
        remote_only=True
    ) is False


def test_deduplicate_raw_jobs():
    manager = JobSourceManager()
    raw_jobs = [
        {
            "source_id": "job-1",
            "source_name": "remoteok",
            "title": "Senior Python Engineer",
            "company": "Acme Corp",
            "url": "https://example.com/jobs/1?ref=feed",
            "location": "Remote"
        },
        # Duplicate with different query params in URL
        {
            "source_id": "job-2",
            "source_name": "arbeitnow",
            "title": "Senior Python Engineer",
            "company": "Acme Corp",
            "url": "https://example.com/jobs/1",
            "location": "Remote"
        },
        # Distinct job
        {
            "source_id": "job-3",
            "source_name": "jobicy",
            "title": "Frontend React Developer",
            "company": "Beta Inc",
            "url": "https://example.com/jobs/3",
            "location": "Remote"
        }
    ]

    deduped = manager._deduplicate_raw_jobs(raw_jobs)
    assert len(deduped) == 2
    titles = [j["title"] for j in deduped]
    assert "Senior Python Engineer" in titles
    assert "Frontend React Developer" in titles


def test_job_matcher_evaluates_skills_and_reasons():
    profile = UserProfile(
        headline="Senior Full Stack Engineer",
        skills=json.dumps(["Python", "React", "TypeScript", "FastAPI", "Docker", "SQL"]),
        experiences=json.dumps([
            {"title": "Senior Software Engineer", "company": "TechCorp", "description": "Built cloud systems"}
        ]),
        education=json.dumps([
            {"degree": "B.S. in Computer Science", "institution": "State University"}
        ]),
        location="San Francisco, CA"
    )

    matching_job = JobListing(
        source_id="m1",
        source_name="arbeitnow",
        title="Senior Python & React Developer",
        company="Startup Co",
        location="Remote",
        is_remote=True,
        skills_required=json.dumps(["Python", "React", "Docker"]),
        description="We are looking for a Senior Developer with Python, React, and Docker experience.",
        url="https://example.com/job/m1"
    )

    match = JobMatcher.evaluate(profile=profile, job=matching_job)

    assert match.score >= 75.0
    assert "Python" in match.matched_skills
    assert "React" in match.matched_skills
    assert any("skill" in r.lower() for r in match.reasons)
    assert any("title" in r.lower() or "senior" in r.lower() for r in match.reasons)
    assert "heuristic" in match.disclaimer.lower()


def test_job_search_api_and_saved_preferences(client, auth_headers, test_user, db_session):
    # 1. Update search preferences
    pref_payload = {
        "keywords": "Full Stack",
        "country": "US",
        "states": ["CA", "NY"],
        "city": "San Francisco",
        "remote_only": True,
        "employment_type": "full_time"
    }
    put_pref_resp = client.put("/api/v1/jobs/preferences", headers=auth_headers, json=pref_payload)
    assert put_pref_resp.status_code == 200
    pref_data = put_pref_resp.json()
    assert pref_data["country"] == "US"
    assert "CA" in pref_data["states"]

    # 2. Query search preferences
    get_pref_resp = client.get("/api/v1/jobs/preferences", headers=auth_headers)
    assert get_pref_resp.status_code == 200
    assert get_pref_resp.json()["city"] == "San Francisco"

    # 3. Seed sample jobs into database
    sample_job1 = JobListing(
        source_id="seed-1",
        source_name="remoteok",
        title="Lead Python Architect",
        company="Global Cloud",
        location="Remote, US",
        country="US",
        state="CA",
        is_remote=True,
        employment_type="full_time",
        url="https://example.com/seed-1",
        description="Lead engineering using Python, React, and PostgreSQL.",
        skills_required=json.dumps(["Python", "React"]),
        is_active=True
    )
    sample_job2 = JobListing(
        source_id="seed-2",
        source_name="arbeitnow",
        title="Berlin Java Specialist",
        company="Berlin Auto",
        location="Berlin, Germany",
        country="DE",
        is_remote=False,
        employment_type="full_time",
        url="https://example.com/seed-2",
        description="Java development on-site in Berlin.",
        skills_required=json.dumps(["Java"]),
        is_active=True
    )
    db_session.add(sample_job1)
    db_session.add(sample_job2)
    db_session.commit()
    db_session.refresh(sample_job1)

    # 4. Search jobs with US filter
    search_resp = client.get("/api/v1/jobs/search?country=US", headers=auth_headers)
    assert search_resp.status_code == 200
    search_data = search_resp.json()
    assert "jobs" in search_data
    
    returned_titles = [j["title"] for j in search_data["jobs"]]
    assert "Lead Python Architect" in returned_titles
    # German on-site job must NOT be returned when country=US
    assert "Berlin Java Specialist" not in returned_titles

    # 5. Save job and select for apply
    save_resp = client.post(
        "/api/v1/jobs/save",
        headers=auth_headers,
        json={"job_id": sample_job1.id, "notes": "Top pick"}
    )
    assert save_resp.status_code == 200
    assert save_resp.json()["is_saved"] is True

    # 6. List saved jobs
    saved_list_resp = client.get("/api/v1/jobs/saved", headers=auth_headers)
    assert saved_list_resp.status_code == 200
    assert len(saved_list_resp.json()) == 1
    assert saved_list_resp.json()[0]["id"] == sample_job1.id

    # 7. Select job for application queue
    select_resp = client.post(
        "/api/v1/jobs/select",
        headers=auth_headers,
        json={"job_id": sample_job1.id, "selected": True}
    )
    assert select_resp.status_code == 200
    assert select_resp.json()["is_selected_for_apply"] is True

    # 8. List selected jobs
    selected_list_resp = client.get("/api/v1/jobs/selected", headers=auth_headers)
    assert selected_list_resp.status_code == 200
    assert len(selected_list_resp.json()) == 1
    assert selected_list_resp.json()[0]["id"] == sample_job1.id


def test_locations_and_sources_metadata_endpoints(client, auth_headers):
    # Locations
    loc_resp = client.get("/api/v1/jobs/locations")
    assert loc_resp.status_code == 200
    locations = loc_resp.json()
    us_entry = next((item for item in locations if item["code"] == "US"), None)
    assert us_entry is not None
    assert len(us_entry["states"]) >= 50

    # Sources
    src_resp = client.get("/api/v1/jobs/sources")
    assert src_resp.status_code == 200
    sources = src_resp.json()
    source_names = [s["source_name"] for s in sources]
    assert "arbeitnow" in source_names
    assert "remoteok" in source_names
    assert "jobicy" in source_names
    assert "adzuna" in source_names
