import io
import pytest
from pypdf import PdfWriter
from app.models.job import JobListing
from app.models.profile import UserProfile
from app.services.ai_service import LocalHeuristicAIService
from app.services.file_extractor import extract_text_from_pdf, FileExtractionError
from app.services.job_matcher import JobMatcher
from app.services.semantic_classifier import ResumeSemanticClassifier


SAMPLE_RESUME_TEXT = """
Sarah Connor
sarah.connor@example.com | (310) 555-0199 | Los Angeles, CA
https://linkedin.com/in/sarahconnor | https://github.com/sarahconnor

PROFESSIONAL SUMMARY
Senior Full Stack Engineer with 7+ years of experience designing robust web systems.

TECHNICAL SKILLS
Python, TypeScript, React, FastAPI, Docker, PostgreSQL, Kubernetes, AWS, Git

WORK EXPERIENCE
Senior Software Engineer at Skynet Defense
2020 - Present
- Designed microservices using Python and FastAPI
- Implemented real-time telemetry dashboard in React

Software Engineer at Cyberdyne Systems
2017 - 2020
- Built REST APIs and relational databases using PostgreSQL and Python

EDUCATION
Bachelor of Science in Computer Science
University of California, Los Angeles (2017)

PROJECTS
Autonomous Drone Controller
https://github.com/sarahconnor/drone-controller
Built a real-time autonomous navigation system using Python and OpenCV.
"""


@pytest.mark.asyncio
async def test_heuristic_parser_extracts_all_core_fields():
    parser = LocalHeuristicAIService()
    profile = await parser.parse_resume_text(SAMPLE_RESUME_TEXT)

    assert profile.full_name == "Sarah Connor"
    assert profile.email == "sarah.connor@example.com"
    assert profile.phone == "(310) 555-0199"
    assert profile.location == "Los Angeles, CA"
    assert profile.linkedin_url == "https://linkedin.com/in/sarahconnor"
    assert profile.github_url == "https://github.com/sarahconnor"
    assert "Python" in profile.skills
    assert "FastAPI" in profile.skills
    assert "React" in profile.skills
    assert "Docker" in profile.skills

    # Verify Job 1: Exactly separated
    assert len(profile.experiences) == 2
    assert profile.experiences[0].title == "Senior Software Engineer"
    assert profile.experiences[0].company == "Skynet Defense"
    assert profile.experiences[0].current is True
    assert profile.experiences[0].start_date == "2020"

    # Verify Job 2: Exactly separated
    assert profile.experiences[1].title == "Software Engineer"
    assert profile.experiences[1].company == "Cyberdyne Systems"
    assert profile.experiences[1].current is False
    assert profile.experiences[1].start_date == "2017"

    # Verify Education: Exactly separated
    assert len(profile.education) == 1
    assert "Bachelor of Science" in (profile.education[0].degree or "")
    assert "University of California" in (profile.education[0].institution or "")
    assert profile.education[0].graduation_year == "2017"

    # Verify Projects
    assert len(profile.projects) >= 1
    assert "Autonomous Drone Controller" in (profile.projects[0].name or "")


@pytest.mark.asyncio
async def test_company_and_title_never_swapped_regardless_of_order():
    """
    Verifies that 'Company | Title' and 'Title | Company' are both parsed
    with exact semantic separation, never based on line position.
    """
    parser = LocalHeuristicAIService()

    # Layout A: Company first, Title second
    text_company_first = """
    John Doe
    john@example.com

    EXPERIENCE
    Google, LLC | Senior Software Engineer
    2021 - Present
    - Developed backend systems in Go.
    """
    profile_a = await parser.parse_resume_text(text_company_first)
    assert len(profile_a.experiences) == 1
    assert profile_a.experiences[0].company == "Google, LLC"
    assert profile_a.experiences[0].title == "Senior Software Engineer"

    # Layout B: Title first, Company second
    text_title_first = """
    John Doe
    john@example.com

    EXPERIENCE
    Senior Software Engineer | Google, LLC
    2021 - Present
    - Developed backend systems in Go.
    """
    profile_b = await parser.parse_resume_text(text_title_first)
    assert len(profile_b.experiences) == 1
    assert profile_b.experiences[0].company == "Google, LLC"
    assert profile_b.experiences[0].title == "Senior Software Engineer"


@pytest.mark.asyncio
async def test_multiline_experiences_and_different_layouts():
    """
    Tests multiple work experiences across diverse document layouts:
    - Multi-line company then title
    - Multi-line title then company with location
    - Labeled fields (Company:, Title:, Dates:)
    """
    parser = LocalHeuristicAIService()

    multi_layout_resume = """
    Jane Smith
    jane.smith@example.com | (415) 555-2671 | San Francisco, CA

    WORK EXPERIENCE
    Acme Technologies, Inc.
    Staff Software Architect | 2021 - Present
    - Designed cloud microservices.

    Principal DevOps Engineer
    Cyberdyne Systems - Austin, TX
    2018 - 2021
    - Managed Kubernetes clusters.

    Company: Initech Solutions
    Title: Full Stack Developer
    Dates: 2016 - 2018
    - Maintained customer portals using React and Python.
    """

    profile = await parser.parse_resume_text(multi_layout_resume)
    assert len(profile.experiences) == 3

    # Experience 1: Company on line 1, Title on line 2
    exp1 = profile.experiences[0]
    assert "Acme Technologies" in (exp1.company or "")
    assert "Software Architect" in (exp1.title or "")
    assert exp1.current is True

    # Experience 2: Title on line 1, Company on line 2
    exp2 = profile.experiences[1]
    assert "DevOps Engineer" in (exp2.title or "")
    assert "Cyberdyne Systems" in (exp2.company or "")
    assert "Austin, TX" in (exp2.location or "")

    # Experience 3: Labeled fields
    exp3 = profile.experiences[2]
    assert "Initech Solutions" in (exp3.company or "")
    assert "Full Stack Developer" in (exp3.title or "")


@pytest.mark.asyncio
async def test_education_degree_and_institution_disambiguation():
    """
    Verifies that Institution and Degree are correctly distinguished
    even when their order in text is swapped.
    """
    parser = LocalHeuristicAIService()

    # Layout 1: Institution first
    text_inst_first = """
    Alex Ray
    alex@example.com

    EDUCATION
    Stanford University | Bachelor of Science in Computer Science
    2019
    """
    prof1 = await parser.parse_resume_text(text_inst_first)
    assert len(prof1.education) == 1
    assert "Stanford University" in prof1.education[0].institution
    assert "Bachelor of Science" in prof1.education[0].degree
    assert prof1.education[0].graduation_year == "2019"

    # Layout 2: Degree first
    text_deg_first = """
    Alex Ray
    alex@example.com

    EDUCATION
    Master of Science in Artificial Intelligence - Massachusetts Institute of Technology
    2021
    """
    prof2 = await parser.parse_resume_text(text_deg_first)
    assert len(prof2.education) == 1
    assert "Institute of Technology" in prof2.education[0].institution
    assert "Master of Science" in prof2.education[0].degree
    assert prof2.education[0].graduation_year == "2021"


@pytest.mark.asyncio
async def test_heuristic_parser_never_invents_missing_fields():
    minimal_text = """
    John Doe
    john.doe@example.com
    Skills: Python, Git
    """
    parser = LocalHeuristicAIService()
    profile = await parser.parse_resume_text(minimal_text)

    assert profile.full_name == "John Doe"
    assert profile.email == "john.doe@example.com"
    assert profile.phone is None
    assert profile.linkedin_url is None
    assert profile.github_url is None
    assert len(profile.experiences) == 0
    assert len(profile.education) == 0
    assert "phone" in profile.missing_fields
    assert "experiences" in profile.missing_fields
    assert "education" in profile.missing_fields


@pytest.mark.asyncio
async def test_confidence_and_evidence_tracking():
    parser = LocalHeuristicAIService()
    profile = await parser.parse_resume_text(SAMPLE_RESUME_TEXT)

    assert "email" in profile.confidence_scores
    assert profile.confidence_scores["email"] >= 0.90
    assert "full_name" in profile.confidence_scores
    assert profile.confidence_scores["full_name"] >= 0.90
    assert len(profile.field_evidence) > 0


def test_profile_update_and_confirm(client, auth_headers):
    # Retrieve initial profile
    resp = client.get("/api/v1/profile", headers=auth_headers)
    assert resp.status_code == 200

    # Update profile with verified fields
    payload = {
        "full_name": "Alex Updated",
        "email": "alex.updated@example.com",
        "phone": "+1 (555) 000-1111",
        "location": "Seattle, WA",
        "headline": "Lead Full Stack Architect",
        "summary": "Specialized in scalable cloud native systems.",
        "skills": ["Python", "React", "TypeScript", "AWS"],
        "experiences": [
            {
                "title": "Lead Engineer",
                "company": "Cloud Corp",
                "location": "Seattle, WA",
                "start_date": "2022",
                "end_date": "Present",
                "current": True,
                "description": "Leading platform development."
            }
        ],
        "education": [
            {
                "degree": "B.S. Computer Engineering",
                "institution": "University of Washington",
                "graduation_year": "2018"
            }
        ],
        "projects": [
            {
                "name": "Cloud Observability Tool",
                "description": "Open-source monitoring tool",
                "url": "https://github.com/example/tool",
                "technologies": ["Go", "React"]
            }
        ],
        "is_confirmed": True
    }
    update_resp = client.put("/api/v1/profile", headers=auth_headers, json=payload)
    assert update_resp.status_code == 200
    updated_data = update_resp.json()
    assert updated_data["full_name"] == "Alex Updated"
    assert updated_data["is_confirmed"] is True
    assert len(updated_data["skills"]) == 4
    assert len(updated_data["experiences"]) == 1
    assert updated_data["experiences"][0]["title"] == "Lead Engineer"
    assert updated_data["experiences"][0]["company"] == "Cloud Corp"


def test_job_matching_uses_corrected_profile():
    """
    Verifies Requirement 9:
    Job matching uses the candidate's actual job title and company from the profile,
    demonstrating that title alignment works when fields are properly classified.
    """
    # Create profile with correct title
    profile = UserProfile(
        id=1,
        user_id=1,
        headline="Senior Full Stack Software Engineer",
        skills='["Python", "FastAPI", "React", "Docker"]',
        experiences='[{"title": "Senior Software Engineer", "company": "Skynet Defense", "current": true}]',
        education='[{"degree": "B.S. Computer Science", "institution": "UCLA"}]',
        location="Los Angeles, CA"
    )

    # Job listing looking for a Senior Software Engineer
    job = JobListing(
        id=1,
        source_id="job_1",
        source_name="arbeitnow",
        title="Senior Software Engineer",
        company="TechCorp",
        location="Los Angeles, CA",
        country="US",
        is_remote=False,
        description="Looking for a Senior Software Engineer proficient in Python and FastAPI.",
        skills_required='["python", "fastapi"]',
        cached_at="2026-10-10T00:00:00Z"
    )

    match = JobMatcher.evaluate(profile=profile, job=job)
    assert match.score >= 70.0
    assert any("title alignment" in r.lower() or "senior software engineer" in r.lower() for r in match.reasons)


def test_scanned_pdf_raises_clear_error(tmp_path):
    """
    Verifies Requirement 8:
    A scanned PDF with no selectable text raises FileExtractionError with a clear message.
    """
    # Create a 1-page PDF with no text elements (simulating a scanned image)
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    pdf_path = str(tmp_path / "scanned_resume.pdf")
    with open(pdf_path, "wb") as f:
        writer.write(f)

    with pytest.raises(FileExtractionError) as exc_info:
        extract_text_from_pdf(pdf_path)

    assert "scanned image" in str(exc_info.value).lower()
