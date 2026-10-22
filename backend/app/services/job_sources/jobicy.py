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


class JobicyAdapter(BaseJobSourceAdapter):
    """
    Jobicy Public Remote Jobs API (v2).
    Free official API feed delivering global remote jobs with geographic eligibility metadata.
    """

    BASE_URL = "https://jobicy.com/api/v2/remote-jobs"

    @property
    def source_name(self) -> str:
        return "jobicy"

    @property
    def display_name(self) -> str:
        return "Jobicy Remote API"

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

        params: Dict[str, Any] = {"count": min(limit, 50)}
        if query and query.strip():
            params["tag"] = query.strip()
        if country and country.upper() == "US":
            params["geo"] = "usa"
        elif country and country.upper() == "GB":
            params["geo"] = "uk"
        elif country and country.upper() == "CA":
            params["geo"] = "canada"
        elif country and country.upper() == "IN":
            params["geo"] = "apac"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {
                    "User-Agent": "JobPulse-AI/1.0",
                    "Accept": "application/json"
                }
                response = await client.get(self.BASE_URL, params=params, headers=headers)
                
                if response.status_code != 200:
                    logger.warning("Jobicy responded with status %s", response.status_code)
                    return []

                payload = response.json()
                raw_jobs = payload.get("jobs", [])

                for item in raw_jobs[:limit]:
                    job_id = str(item.get("id") or "")
                    title = item.get("jobTitle") or "Remote Role"
                    company = item.get("companyName") or "Company"
                    url = item.get("url") or f"https://jobicy.com/jobs/{job_id}"
                    raw_geo = (item.get("jobGeo") or "").strip()
                    geo = raw_geo if raw_geo else "Location Unspecified"
                    raw_desc = item.get("jobDescription") or ""
                    description = clean_description(raw_desc)
                    job_types = item.get("jobType") or []
                    
                    emp_type = "full_time"
                    if isinstance(job_types, list):
                        type_str = " ".join(job_types).lower()
                    else:
                        type_str = str(job_types).lower()
                    if "contract" in type_str:
                        emp_type = "contract"
                    elif "part" in type_str:
                        emp_type = "part_time"

                    posted_at = None
                    pub_date = item.get("pubDate")
                    if pub_date:
                        try:
                            posted_at = datetime.fromisoformat(pub_date)
                        except Exception:
                            pass

                    # Extract common tech keywords from description as skills
                    skills = []
                    for kw in ["Python", "JavaScript", "TypeScript", "React", "Node.js", "Docker", "AWS", "SQL", "Git"]:
                        if re.search(rf"\b{re.escape(kw)}\b", description, re.IGNORECASE):
                            skills.append(kw)

                    # Normalize location and verify country boundaries
                    from app.core.locations import normalize_job_location, is_remote_eligible_for_country, is_location_in_north_america, is_location_in_europe
                    raw_loc = f"Remote ({geo})"
                    loc_info = normalize_job_location(raw_location=raw_loc, raw_country=None, raw_is_remote=True)

                    if country and country.upper() == "IN":
                        title_lower = title.lower()
                        if is_location_in_north_america(title_lower) or is_location_in_europe(title_lower):
                            continue
                        eligible, _ = is_remote_eligible_for_country(raw_loc.lower(), "IN")
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
                        "salary_text": None,
                        "url": url,
                        "description": description,
                        "skills_required": skills,
                        "posted_at": posted_at
                    })

        except Exception as exc:
            logger.error("Error querying Jobicy adapter: %s", exc)

        return jobs
