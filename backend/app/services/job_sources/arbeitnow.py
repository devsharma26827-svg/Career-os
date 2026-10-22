import html
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx
from app.services.job_sources.base import BaseJobSourceAdapter

logger = logging.getLogger(__name__)


def strip_html_tags(text: str) -> str:
    """Utility to clean HTML tags from job descriptions into readable plain text."""
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = html.unescape(clean)
    return re.sub(r"\s+", " ", clean).strip()


class ArbeitnowAdapter(BaseJobSourceAdapter):
    """
    Official Arbeitnow Job Board API integration.
    Free, public, official JSON API. No API key needed.
    Provides verified technology, remote, and on-site listings across US and Europe.
    """

    BASE_URL = "https://www.arbeitnow.com/api/job-board-api"

    @property
    def source_name(self) -> str:
        return "arbeitnow"

    @property
    def display_name(self) -> str:
        return "Arbeitnow API"

    @property
    def requires_api_key(self) -> bool:
        return False

    async def fetch_jobs(
        self,
        query: Optional[str] = None,
        country: Optional[str] = None,
        states: Optional[List[str]] = None,
        city: Optional[str] = None,
        remote_only: bool = False,
        limit: int = 40
    ) -> List[Dict[str, Any]]:
        jobs: List[Dict[str, Any]] = []

        params = {}
        if query and query.strip():
            params["search"] = query.strip()

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {
                    "User-Agent": "JobPulse-AI-JobSearch/1.0 (Educational/Accessible Platform)",
                    "Accept": "application/json"
                }
                response = await client.get(self.BASE_URL, params=params, headers=headers)
                
                if response.status_code != 200:
                    logger.warning("Arbeitnow API responded with status %s", response.status_code)
                    return []

                payload = response.json()
                raw_items = payload.get("data", [])

                for item in raw_items[:limit]:
                    title = item.get("title") or "Untitled Position"
                    company = item.get("company_name") or "Company"
                    slug = item.get("slug") or f"{company}-{title}"
                    url = item.get("url") or f"https://www.arbeitnow.com/view/{slug}"
                    raw_desc = item.get("description") or ""
                    clean_desc = strip_html_tags(raw_desc)
                    is_remote = bool(item.get("remote", False))
                    location_str = item.get("location") or ("Remote" if is_remote else "Unknown")
                    tags = item.get("tags") or []
                    
                    job_types = item.get("job_types") or []
                    emp_type = "full_time"
                    if any("contract" in str(t).lower() for t in job_types):
                        emp_type = "contract"
                    elif any("part" in str(t).lower() for t in job_types):
                        emp_type = "part_time"
                    elif any("intern" in str(t).lower() for t in job_types):
                        emp_type = "internship"

                    # Parse created_at timestamp
                    posted_at = None
                    created_val = item.get("created_at")
                    if isinstance(created_val, (int, float)):
                        posted_at = datetime.fromtimestamp(created_val, timezone.utc)
                    elif isinstance(created_val, str):
                        try:
                            posted_at = datetime.fromisoformat(created_val)
                        except Exception:
                            pass

                    # Normalize location
                    from app.core.locations import normalize_job_location
                    loc_info = normalize_job_location(
                        raw_location=location_str,
                        raw_country=None,
                        raw_is_remote=is_remote
                    )

                    # If user asked for India/US and this Arbeitnow job is European, skip or label appropriately
                    if country and country.upper() == "IN" and loc_info["country"] in ["DE", "GB", "EU"]:
                        continue

                    jobs.append({
                        "source_id": slug,
                        "source_name": self.source_name,
                        "title": title,
                        "company": company,
                        "location": loc_info["canonical_location"],
                        "country": loc_info["country"],
                        "state": loc_info["state"],
                        "city": loc_info["city"],
                        "is_remote": loc_info["is_remote"],
                        "employment_type": emp_type,
                        "salary_min": None,
                        "salary_max": None,
                        "salary_currency": None,
                        "salary_text": None,
                        "url": url,
                        "description": clean_desc,
                        "skills_required": [str(t).strip() for t in tags if str(t).strip()],
                        "posted_at": posted_at
                    })

        except Exception as exc:
            logger.error("Error querying Arbeitnow adapter: %s", exc)

        return jobs
