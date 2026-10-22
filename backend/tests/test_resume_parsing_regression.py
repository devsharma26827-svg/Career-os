import io
import pytest
from pypdf import PdfWriter
from app.services.ai_service import LocalHeuristicAIService
from app.services.file_extractor import extract_text_from_pdf, FileExtractionError
from app.services.semantic_classifier import ResumeSemanticClassifier


@pytest.mark.asyncio
async def test_name_never_assigned_to_section_heading():
    """
    Test 1: Section heading 'PROFESSIONAL SUMMARY' or 'CAREER OBJECTIVE' appearing
    at the top of the resume is NEVER extracted as full_name.
    Candidate's actual name is correctly identified.
    """
    parser = LocalHeuristicAIService()

    # Layout A: Heading above name
    text_heading_first = """
    PROFESSIONAL SUMMARY
    Sarah Connor
    sarah.connor@example.com | (310) 555-0199 | Austin, TX
    Experienced software engineer with 5 years of background.
    """
    profile_a = await parser.parse_resume_text(text_heading_first)
    assert profile_a.full_name == "Sarah Connor"
    assert "SUMMARY" not in (profile_a.full_name or "")
    assert profile_a.email == "sarah.connor@example.com"
    assert profile_a.location == "Austin, TX"

    # Layout B: Name in ALL CAPS followed by summary header
    text_caps_name = """
    DEV SHARMA
    dev.sharma@example.com | Jaipur, Rajasthan
    CAREER OBJECTIVE
    Passionate software developer.
    """
    profile_b = await parser.parse_resume_text(text_caps_name)
    assert profile_b.full_name == "Dev Sharma"
    assert "OBJECTIVE" not in (profile_b.full_name or "")


@pytest.mark.asyncio
async def test_location_isolates_geo_and_rejects_noise():
    """
    Test 2: Geographic location is correctly extracted and isolated from noise phrases
    like 'Available immediately, Relocating to Austin, TX'.
    Unrelated phrases like 'Expert in JavaScript, React' are never treated as locations.
    """
    parser = LocalHeuristicAIService()

    # Test phrase with relocation noise
    text_relocation = """
    John Doe
    john.doe@example.com
    Available immediately, Relocating to Austin, TX
    Full-Stack Developer
    """
    profile_reloc = await parser.parse_resume_text(text_relocation)
    assert profile_reloc.location == "Austin, TX"
    assert "Available" not in (profile_reloc.location or "")
    assert "Relocating" not in (profile_reloc.location or "")

    # Test phrase with tech skills at top (should NOT become location)
    text_skills_at_top = """
    Jane Smith
    jane.smith@example.com
    Expert in JavaScript, React, Node.js
    Software Developer
    """
    profile_skills = await parser.parse_resume_text(text_skills_at_top)
    assert profile_skills.location is None or "React" not in (profile_skills.location or "")


@pytest.mark.asyncio
async def test_numeric_date_ranges_and_multiple_employers():
    """
    Test 3 & 4: Supports numeric date ranges (e.g. '06/2021 - 08/2023') and preserves
    multiple employers independently without merging them into a single record.
    """
    parser = LocalHeuristicAIService()

    text_multiple_jobs = """
    Alex Rivera
    alex.rivera@example.com | San Francisco, CA

    EXPERIENCE
    Lead Systems Architect at Skynet Defense
    06/2021 - 08/2023
    - Architected distributed data pipelines using Python and Kafka.
    - Improved throughput by 45%.

    Senior Software Engineer at Cyberdyne Systems
    01/2019 - 05/2021
    - Developed backend REST services in Go and PostgreSQL.
    - Managed cloud infrastructure on AWS.
    """
    profile = await parser.parse_resume_text(text_multiple_jobs)

    assert len(profile.experiences) == 2, f"Expected 2 experiences, found {len(profile.experiences)}"

    exp1 = profile.experiences[0]
    assert exp1.title == "Lead Systems Architect"
    assert exp1.company == "Skynet Defense"
    assert exp1.start_date == "06/2021"
    assert exp1.end_date == "08/2023"

    exp2 = profile.experiences[1]
    assert exp2.title == "Senior Software Engineer"
    assert exp2.company == "Cyberdyne Systems"
    assert exp2.start_date == "01/2019"
    assert exp2.end_date == "05/2021"


@pytest.mark.asyncio
async def test_education_graduation_year_and_field_of_study():
    """
    Test 5: In date range '2018 - 2022', graduation year is assigned to the concluding year '2022',
    not the matriculation year '2018'. Degree and field of study are cleanly separated.
    """
    parser = LocalHeuristicAIService()

    text_education = """
    Maria Garcia
    maria@example.com

    EDUCATION
    Rajasthan Technical University, Kota
    Bachelor of Technology in Computer Science and Engineering | 2018 - 2022
    """
    profile = await parser.parse_resume_text(text_education)

    assert len(profile.education) >= 1
    edu = profile.education[0]
    assert edu.graduation_year == "2022", f"Expected graduation year 2022, got {edu.graduation_year}"
    assert "Rajasthan Technical University" in (edu.institution or "")
    assert "Bachelor of Technology" in (edu.degree or "")
    assert edu.field_of_study == "Computer Science and Engineering"


@pytest.mark.asyncio
async def test_header_parsing_with_location_does_not_contaminate_company_or_title():
    """
    Test 6: In headers containing company and location like 'TechCorp, Jaipur, Rajasthan',
    location is extracted cleanly and company is kept intact without leaking state into title.
    """
    parsed = ResumeSemanticClassifier.parse_header_line("TechCorp, Jaipur, Rajasthan")
    assert parsed.get("location") == "Jaipur, Rajasthan"
    assert parsed.get("company") == "TechCorp"
    assert parsed.get("title") is None or "Rajasthan" not in (parsed.get("title") or "")


def test_scanned_pdf_detection_raises_error():
    """
    Test 7: A scanned or image-only PDF with fewer than 30 characters of extracted text
    raises FileExtractionError instructing that OCR is required.
    """
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    pdf_bytes = buf.getvalue()

    with pytest.raises(FileExtractionError) as exc_info:
        extract_text_from_pdf(pdf_bytes)

    assert "OCR" in str(exc_info.value)


@pytest.mark.asyncio
async def test_multiple_jobs_without_bullets_separated_cleanly():
    """
    Test 8: Distinct jobs without bullet points are separated cleanly into
    multiple ExperienceItems and never merged into a single entry.
    """
    parser = LocalHeuristicAIService()

    text_no_bullets = """
    Priya Patel
    priya@example.com | Mumbai, Maharashtra

    EXPERIENCE
    Senior Frontend Engineer at Skynet Defense
    08/2022 - Present
    UI Developer at Cyberdyne Systems
    06/2020 - 07/2022
    """
    profile = await parser.parse_resume_text(text_no_bullets)

    assert len(profile.experiences) == 2, f"Expected 2 jobs, found {len(profile.experiences)}"
    assert profile.experiences[0].title == "Senior Frontend Engineer"
    assert profile.experiences[0].company == "Skynet Defense"
    assert profile.experiences[0].current is True

    assert profile.experiences[1].title == "UI Developer"
    assert profile.experiences[1].company == "Cyberdyne Systems"
    assert profile.experiences[1].current is False


@pytest.mark.asyncio
async def test_field_level_accuracy_benchmark(capsys):
    """
    Test 9: Field-Level Accuracy Benchmark
    Evaluates parsing accuracy across diverse resume layouts (standard, multi-column simulation,
    inverted title/company order, missing dates, numeric dates, and misleading section headers).
    Computes and reports exact field-level accuracy percentage.
    """
    parser = LocalHeuristicAIService()

    test_corpus = [
        {
            "name": "Standard Layout",
            "text": """
            Sarah Connor
            sarah.connor@example.com | (310) 555-0199 | Los Angeles, CA
            PROFESSIONAL SUMMARY
            Experienced software engineer with strong background.
            WORK EXPERIENCE
            Senior Software Engineer at Skynet Defense
            2020 - Present
            - Developed microservices in Python.
            EDUCATION
            Bachelor of Science in Computer Science
            University of California, Los Angeles (2017)
            """,
            "expected": {
                "full_name": "Sarah Connor",
                "email": "sarah.connor@example.com",
                "location": "Los Angeles, CA",
                "job_title": "Senior Software Engineer",
                "company": "Skynet Defense",
                "degree": "Bachelor of Science",
                "institution": "University of California",
                "graduation_year": "2017"
            }
        },
        {
            "name": "Numeric Dates & Inverted Header",
            "text": """
            DEV SHARMA
            dev.sharma@example.com | Jaipur, Rajasthan
            EXPERIENCE
            Google, LLC | Staff Software Engineer
            06/2021 - 08/2023
            - Core infrastructure.
            EDUCATION
            Rajasthan Technical University, Kota
            Bachelor of Technology in Computer Science | 2018 - 2022
            """,
            "expected": {
                "full_name": "Dev Sharma",
                "email": "dev.sharma@example.com",
                "location": "Jaipur, Rajasthan",
                "job_title": "Staff Software Engineer",
                "company": "Google, LLC",
                "degree": "Bachelor of Technology",
                "institution": "Rajasthan Technical University",
                "graduation_year": "2022"
            }
        },
        {
            "name": "Misleading Header & Relocation Phrase",
            "text": """
            CAREER OBJECTIVE
            Alex Rivera
            alex.rivera@example.com
            Available immediately, Relocating to Austin, TX
            EXPERIENCE
            Skynet Defense - Systems Architect
            2019 - 2021
            - Distributed systems.
            EDUCATION
            Master of Science | Stanford University | 2019
            """,
            "expected": {
                "full_name": "Alex Rivera",
                "email": "alex.rivera@example.com",
                "location": "Austin, TX",
                "job_title": "Systems Architect",
                "company": "Skynet Defense",
                "degree": "Master of Science",
                "institution": "Stanford University",
                "graduation_year": "2019"
            }
        }
    ]

    total_fields = 0
    correct_fields = 0
    field_breakdown = {}

    for item in test_corpus:
        profile = await parser.parse_resume_text(item["text"])
        exp = item["expected"]

        actual_fields = {
            "full_name": profile.full_name,
            "email": profile.email,
            "location": profile.location,
            "job_title": profile.experiences[0].title if profile.experiences else None,
            "company": profile.experiences[0].company if profile.experiences else None,
            "degree": profile.education[0].degree if profile.education else None,
            "institution": profile.education[0].institution if profile.education else None,
            "graduation_year": profile.education[0].graduation_year if profile.education else None,
        }

        for f_key, expected_val in exp.items():
            total_fields += 1
            if f_key not in field_breakdown:
                field_breakdown[f_key] = {"total": 0, "correct": 0}
            field_breakdown[f_key]["total"] += 1

            actual_val = actual_fields.get(f_key)
            is_match = False
            if actual_val and expected_val:
                is_match = (expected_val.lower() in actual_val.lower()) or (actual_val.lower() in expected_val.lower())

            if is_match:
                correct_fields += 1
                field_breakdown[f_key]["correct"] += 1

    overall_accuracy = (correct_fields / total_fields) * 100.0

    print("\n" + "=" * 50)
    print("RESUME PARSING FIELD-LEVEL ACCURACY BENCHMARK")
    print("=" * 50)
    for field, stats in field_breakdown.items():
        pct = (stats["correct"] / stats["total"]) * 100.0
        print(f"  - {field:16s}: {stats['correct']}/{stats['total']} ({pct:5.1f}%)")
    print("-" * 50)
    print(f"OVERALL ACCURACY: {correct_fields}/{total_fields} ({overall_accuracy:.1f}%)")
    print("=" * 50 + "\n")

    assert overall_accuracy >= 95.0, f"Expected >= 95% accuracy, got {overall_accuracy:.1f}%"

