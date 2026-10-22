import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from app.core.config import settings
from app.models.job import JobListing
from app.models.profile import UserProfile
from app.services.ai_service import OpenRouterAIService, LocalHeuristicAIService
from app.services.job_matcher import JobMatcher
from app.core.locations import matches_location_filter, classify_location_hierarchy


@pytest.mark.asyncio
async def test_openrouter_retry_on_429_then_heuristic_fallback():
    """
    Verifies that when OpenRouter returns 429 rate limit errors,
    OpenRouterAIService retries with backoff and safely falls back
    to the local heuristic parser without crashing or leaking secrets.
    """
    heuristic_service = LocalHeuristicAIService()
    service = OpenRouterAIService(fallback_service=heuristic_service)
    service.api_key = "test_key_abc123"

    sample_resume = (
        "Jane Doe\n"
        "jane.doe@example.com\n"
        "555-0199\n"
        "San Francisco, CA\n"
        "Senior Cloud Architect\n"
        "EXPERIENCE\n"
        "Tech Global Corp\n"
        "Staff Infrastructure Engineer\n"
        "2020 - Present\n"
        "Led multi-region Kubernetes deployments.\n"
        "SKILLS\n"
        "Python, Docker, Kubernetes, AWS, Terraform\n"
    )

    # Mock response returning 429 with Retry-After header
    mock_resp_429 = MagicMock()
    mock_resp_429.status_code = 429
    mock_resp_429.headers = {"Retry-After": "0.1"}

    call_count = 0

    async def mock_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return mock_resp_429

    with patch("httpx.AsyncClient.post", new=mock_post):
        parsed = await service.parse_resume_text(sample_resume)

    # Should have retried 3 times for primary model, plus fallback attempts
    assert call_count >= 3
    # Transparently indicates heuristic fallback source
    assert parsed.parser_source == "heuristic"
    assert parsed.full_name == "Jane Doe"
    assert "Python" in parsed.skills
    assert "Kubernetes" in parsed.skills


def test_worldwide_search_matching():
    """
    Verifies that when filter_country is None, ALL, or WORLDWIDE,
    jobs across multiple countries (US, DE, IN, UK, Remote) match
    without restrictive geographic bounds.
    """
    # Worldwide should allow jobs from any country
    assert matches_location_filter(
        job_location="Berlin, Germany",
        job_country="DE",
        job_is_remote=False,
        filter_country=None,
        remote_only=False
    ) is True

    assert matches_location_filter(
        job_location="Bengaluru, Karnataka, India",
        job_country="IN",
        job_is_remote=False,
        filter_country="WORLDWIDE",
        remote_only=False
    ) is True

    assert matches_location_filter(
        job_location="San Francisco, CA, USA",
        job_country="US",
        job_is_remote=False,
        filter_country="ALL",
        remote_only=False
    ) is True

    assert matches_location_filter(
        job_location="Worldwide Remote",
        job_country="REMOTE",
        job_is_remote=True,
        filter_country="GLOBAL",
        remote_only=True
    ) is True


def test_classify_location_hierarchy_worldwide():
    """
    Verifies classify_location_hierarchy safely handles None or Worldwide country.
    """
    level, notice = classify_location_hierarchy(
        job_location="Worldwide Remote",
        filter_country=None,
        is_remote=True
    )
    assert level == "country"
    assert "Worldwide Remote Opportunity" in notice


def test_uncalibrated_match_score_without_resume():
    """
    Ensures personalized match score evaluates to 0% uncalibrated
    when user has not uploaded or confirmed a resume.
    """
    dummy_job = JobListing(
        id=1,
        source_id="test_1",
        source_name="arbeitnow",
        title="Full Stack Engineer",
        company="Global Software Inc",
        location="Remote",
        url="https://example.com/job/1",
        description="Looking for Python and React developers.",
        skills_required='["Python", "React"]'
    )

    # Empty/None profile
    match_result = JobMatcher.evaluate(profile=None, job=dummy_job)
    assert match_result.score == 0.0
    assert "No verified resume uploaded yet" in match_result.reasons[0]
