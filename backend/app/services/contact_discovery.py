import re
from datetime import datetime, timezone
from typing import Optional, Tuple
from urllib.parse import urlparse
from app.models.job import JobListing
from app.models.application import RecruiterContact

# Known job aggregator domains to exclude from being treated as direct company domains
AGGREGATOR_DOMAINS = {
    "arbeitnow.com",
    "remoteok.com",
    "remoteok.io",
    "jobicy.com",
    "adzuna.com",
    "adzuna.co.uk",
    "linkedin.com",
    "indeed.com",
    "glassdoor.com",
    "monster.com",
    "ziprecruiter.com",
    "google.com",
}

# Generic platform emails to ignore
PLATFORM_EMAILS = {
    "support@arbeitnow.com",
    "info@arbeitnow.com",
    "hey@remoteok.com",
    "support@remoteok.com",
    "support@jobicy.com",
    "team@jobicy.com",
    "noreply@arbeitnow.com",
    "noreply@remoteok.com",
    "noreply@adzuna.com",
}


class ContactDiscoveryService:
    """
    Discovers permitted public recruiter and hiring contact information.
    Strictly differentiates between VERIFIED contacts (found explicitly in posting)
    and INFERRED contacts (derived from company domain).
    Never invents personal emails or marks inferred mailboxes as verified.
    """

    @classmethod
    def discover_contact_for_job(cls, job: JobListing) -> RecruiterContact:
        """
        Analyzes the job posting description, source URL, and company metadata
        to extract the most accurate recruiter contact.
        """
        description = job.description or ""
        company = job.company or "Company"
        job_url = job.url or ""

        # 1. Look for explicit recruiter name in the job description
        recruiter_name = cls._extract_recruiter_name(description)

        # 2. Look for explicit email address in the job description
        explicit_email = cls._extract_email_from_text(description)

        if explicit_email:
            # We found an explicit contact email in the actual job listing!
            return RecruiterContact(
                job_id=job.id,
                company=company,
                name=recruiter_name or f"{company} Hiring Team",
                email=explicit_email,
                role="Listed Hiring Contact",
                source_url=job_url,
                source_type="job_posting",
                verification_status="VERIFIED",
                confidence_score=1.0,
                notes="Explicitly listed in public job posting text.",
                discovered_at=datetime.now(timezone.utc),
            )

        # 3. Check if the job URL points directly to the employer's official domain
        company_domain = cls._extract_company_domain(job_url)

        if company_domain:
            # Inferred careers mailbox from official company domain
            inferred_email = f"careers@{company_domain}"
            return RecruiterContact(
                job_id=job.id,
                company=company,
                name=recruiter_name or f"{company} Talent Acquisition",
                email=inferred_email,
                role="Talent Acquisition Desk",
                source_url=job_url,
                source_type="inferred_domain",
                verification_status="INFERRED",
                confidence_score=0.45,
                notes=(
                    f"Inferred standard recruitment mailbox for {company_domain}. "
                    "Not guaranteed to be monitored. Please verify before sending."
                ),
                discovered_at=datetime.now(timezone.utc),
            )

        # 4. Fallback: No direct public email found
        return RecruiterContact(
            job_id=job.id,
            company=company,
            name=recruiter_name or f"{company} Recruitment Team",
            email=None,
            role="Official Hiring Team",
            source_url=job_url,
            source_type="job_posting",
            verification_status="NOT_FOUND",
            confidence_score=0.0,
            notes="No public direct email was found. Please apply via the official job posting link.",
            discovered_at=datetime.now(timezone.utc),
        )

    @classmethod
    def _extract_email_from_text(cls, text: str) -> Optional[str]:
        """
        Extracts valid email addresses from text, excluding known job aggregator platforms.
        Prioritizes recruitment-oriented email prefixes.
        """
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}\b"
        matches = re.findall(email_pattern, text)
        if not matches:
            return None

        # Filter out aggregator and generic platform emails
        candidates = [
            m.lower().strip() for m in matches
            if m.lower().strip() not in PLATFORM_EMAILS
            and not any(agg in m.lower() for agg in AGGREGATOR_DOMAINS)
        ]

        if not candidates:
            return None

        # Prioritize hiring/recruitment prefixes
        recruiting_prefixes = ("careers", "jobs", "recruiting", "talent", "hiring", "apply", "hr", "join")
        for candidate in candidates:
            if any(candidate.startswith(pref) for pref in recruiting_prefixes):
                return candidate

        return candidates[0]

    @classmethod
    def _extract_recruiter_name(cls, text: str) -> Optional[str]:
        """
        Extracts recruiter or hiring manager name from common job description patterns.
        """
        patterns = [
            r"(?:hiring manager|recruiter|contact person|reach out to|direct inquiries to|posted by)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b",
            r"(?:questions\? Contact)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # Basic sanity check
                if 3 <= len(name) <= 40 and not any(w in name.lower() for w in ["apply", "resume", "company", "team", "please"]):
                    return name
        return None

    @classmethod
    def _extract_company_domain(cls, url: str) -> Optional[str]:
        """
        Extracts the host domain if it's not a generic job aggregator.
        """
        if not url:
            return None
        try:
            parsed = urlparse(url)
            host = parsed.netloc.lower()
            if host.startswith("www."):
                host = host[4:]
            
            # If domain or parent domain is an aggregator, return None
            for agg in AGGREGATOR_DOMAINS:
                if host == agg or host.endswith(f".{agg}"):
                    return None
            
            # Must look like a valid domain
            if "." in host and len(host.split(".")) >= 2:
                return host
            return None
        except Exception:
            return None
