import html
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
import httpx
from app.services.job_sources.base import BaseJobSourceAdapter

logger = logging.getLogger(__name__)


def clean_description(text: str) -> str:
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = html.unescape(clean)
    return re.sub(r"\s+", " ", clean).strip()


class RemotiveAdapter(BaseJobSourceAdapter):
    """
    Remotive Public Remote Jobs API.
    Official, reliable JSON API providing live remote job listings with
    verified URLs and candidate geographic eligibility metadata.
    """

    BASE_URL = "https://remotive.com/api/remote-jobs"

    @property
    def source_name(self) -> str:
        return "remotive"

    @property
    def display_name(self) -> str:
        return "Remotive Remote API"

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
        limit: int = 35
    ) -> List[Dict[str, Any]]:
        jobs: List[Dict[str, Any]] = []

        params: Dict[str, Any] = {"limit": min(limit, 50)}
        if query and query.strip():
            params["search"] = query.strip()

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {
                    "User-Agent": "JobPulse-AI/1.0",
                    "Accept": "application/json"
                }
                response = await client.get(self.BASE_URL, params=params, headers=headers)

                if response.status_code != 200:
                    logger.warning("Remotive responded with status %s", response.status_code)
                    return []

                payload = response.json()
                raw_jobs = payload.get("jobs", [])

                from app.core.locations import (
                    normalize_job_location,
                    is_remote_eligible_for_country,
                    is_location_in_north_america,
                    is_location_in_europe
                )

                for item in raw_jobs[:limit]:
                    job_id = str(item.get("id") or "")
                    if not job_id:
                        continue
                    title = (item.get("title") or "Remote Position").strip()
                    company = (item.get("company_name") or "Remote Company").strip()
                    url = (item.get("url") or "").strip()
                    if not url or "example.com" in url or not url.startswith("http"):
                        url = f"https://remotive.com/remote-jobs/{job_id}"

                    req_loc = (item.get("candidate_required_location") or "Worldwide").strip()
                    raw_loc = f"Remote ({req_loc})" if req_loc else "Remote (Worldwide)"

                    raw_desc = item.get("description") or ""
                    description = clean_description(raw_desc)

                    # Extract job type
                    job_type_str = (item.get("job_type") or "full_time").lower()
                    emp_type = "full_time"
                    if "contract" in job_type_str or "freelance" in job_type_str:
                        emp_type = "contract"
                    elif "part" in job_type_str:
                        emp_type = "part_time"
                    elif "intern" in job_type_str:
                        emp_type = "internship"

                    # Parse posted date
                    posted_at = None
                    pub_date = item.get("publication_date")
                    if pub_date:
                        try:
                            posted_at = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                        except Exception:
                            pass

                    # Extract skills
                    skills = []
                    tags = item.get("tags") or []
                    for t in tags:
                        if isinstance(t, str) and len(t.strip()) > 1:
                            skills.append(t.strip().title())

                    for kw in ["Python", "JavaScript", "TypeScript", "React", "Node.js", "Docker", "AWS", "SQL", "Git", "FastAPI", "Django"]:
                        if re.search(rf"\b{re.escape(kw)}\b", description, re.IGNORECASE):
                            if kw not in skills:
                                skills.append(kw)

                    # Location normalization & filtering
                    loc_info = normalize_job_location(
                        raw_location=raw_loc,
                        raw_country=None,
                        raw_is_remote=True
                    )

                    if country and country.upper() == "IN":
                        title_lower = title.lower()
                        if is_location_in_north_america(title_lower) or is_location_in_europe(title_lower):
                            continue
                        eligible, _ = is_remote_eligible_for_country(req_loc.lower(), "IN")
                        if not eligible:
                            continue
                    elif country and country.upper() == "US":
                        eligible, _ = is_remote_eligible_for_country(req_loc.lower(), "US")
                        if not eligible:
                            continue

                    jobs.append({
                        "source_id": job_id,
                        "source_name": self.source_name,
                        "title": title,
                        "company": company,
                        "location": loc_info["canonical_location"],
                        "country": loc_info["country"],
                        "state": loc_info["state"],
                        "city": loc_info["city"],
                        "is_remote": True,
                        "employment_type": emp_type,
                        "salary_min": None,
                        "salary_max": None,
                        "salary_currency": None,
                        "salary_text": item.get("salary") or None,
                        "url": url,
                        "description": description,
                        "skills_required": skills[:10],
                        "posted_at": posted_at
                    })

        except Exception as exc:
            logger.error("Error querying Remotive adapter: %s", exc)

        return jobs
