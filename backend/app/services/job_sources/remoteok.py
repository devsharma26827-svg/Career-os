import html
import logging
import re
from datetime import datetime, timezone
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


class RemoteOkAdapter(BaseJobSourceAdapter):
    """
    Public RemoteOK API integration.
    Provides global, verified remote job opportunities with published salary ranges and tags.
    Terms permit public feed access with standard rate limits.
    """

    BASE_URL = "https://remoteok.com/api"

    @property
    def source_name(self) -> str:
        return "remoteok"

    @property
    def display_name(self) -> str:
        return "RemoteOK API"

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

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {
                    "User-Agent": "JobPulse-AI/1.0 (Accessible Career Navigator; devsh@local)",
                    "Accept": "application/json"
                }
                # RemoteOK accepts tag or search query in URL, or returns top jobs
                url = self.BASE_URL
                if query and query.strip():
                    clean_q = re.sub(r"[^a-zA-Z0-9]", "", query.strip().lower())
                    if clean_q:
                        url = f"{self.BASE_URL}?tag={clean_q}"

                response = await client.get(url, headers=headers)
                
                if response.status_code != 200:
                    logger.warning("RemoteOK responded with status %s", response.status_code)
                    return []

                raw_data = response.json()
                if not isinstance(raw_data, list):
                    return []

                # Item 0 is usually legal statement, slice from 1 onwards
                candidate_items = [item for item in raw_data if isinstance(item, dict) and item.get("id")]

                for item in candidate_items[:limit]:
                    job_id = str(item.get("id") or "")
                    position = item.get("position") or "Software Engineer"
                    company = item.get("company") or "Remote Company"
                    raw_desc = item.get("description") or ""
                    description = clean_description(raw_desc)
                    apply_url = item.get("url") or f"https://remoteok.com/remote-jobs/{job_id}"
                    raw_loc = (item.get("location") or "").strip()
                    location_val = raw_loc if raw_loc else "Remote (Location Unspecified)"
                    tags = item.get("tags") or []
                    
                    # Salaries
                    salary_min = item.get("salary_min")
                    salary_max = item.get("salary_max")
                    salary_text = None
                    if salary_min or salary_max:
                        if salary_min and salary_max:
                            salary_text = f"${int(salary_min):,} - ${int(salary_max):,} / yr"
                        elif salary_min:
                            salary_text = f"From ${int(salary_min):,} / yr"
                        elif salary_max:
                            salary_text = f"Up to ${int(salary_max):,} / yr"

                    # Parse date
                    posted_at = None
                    date_val = item.get("date") or item.get("epoch")
                    if isinstance(date_val, (int, float)):
                        posted_at = datetime.fromtimestamp(date_val, timezone.utc)
                    elif isinstance(date_val, str):
                        try:
                            posted_at = datetime.fromisoformat(date_val.replace("Z", "+00:00"))
                        except Exception:
                            pass

                    # Normalize location and verify country boundaries
                    from app.core.locations import normalize_job_location, is_remote_eligible_for_country, is_location_in_north_america, is_location_in_europe
                    loc_info = normalize_job_location(raw_location=location_val, raw_country=None, raw_is_remote=True)

                    if country and country.upper() == "IN":
                        # Check title for foreign restrictions (e.g. Ohio, US Tax)
                        pos_lower = position.lower()
                        if is_location_in_north_america(pos_lower) or is_location_in_europe(pos_lower):
                            continue
                        eligible, _ = is_remote_eligible_for_country(location_val.lower(), "IN")
                        if not eligible:
                            continue

                    jobs.append({
                        "source_id": job_id,
                        "source_name": self.source_name,
                        "title": position,
                        "company": company,
                        "location": loc_info["canonical_location"],
                        "country": loc_info["country"],
                        "state": loc_info["state"],
                        "city": loc_info["city"],
                        "is_remote": True,
                        "employment_type": "full_time",
                        "salary_min": float(salary_min) if salary_min else None,
                        "salary_max": float(salary_max) if salary_max else None,
                        "salary_currency": "USD" if (salary_min or salary_max) else None,
                        "salary_text": salary_text,
                        "url": apply_url,
                        "description": description,
                        "skills_required": [str(t).strip().capitalize() for t in tags if str(t).strip()],
                        "posted_at": posted_at
                    })

        except Exception as exc:
            logger.error("Error querying RemoteOK adapter: %s", exc)

        return jobs
