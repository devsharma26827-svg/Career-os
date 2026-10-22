import html
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
import httpx
from app.core.config import settings
from app.services.job_sources.base import BaseJobSourceAdapter

logger = logging.getLogger(__name__)


def clean_description(text: str) -> str:
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = html.unescape(clean)
    return re.sub(r"\s+", " ", clean).strip()


class AdzunaAdapter(BaseJobSourceAdapter):
    """
    Adzuna Official REST API integration (Optional).
    Covers millions of local and national job listings across US, UK, Canada, India, Germany, Australia, etc.
    Requires developer registration at https://developer.adzuna.com.
    If credentials are not configured, this source gracefully disables itself without disrupting other sources.
    """

    BASE_URL = "https://api.adzuna.com/v1/api/jobs"

    @property
    def source_name(self) -> str:
        return "adzuna"

    @property
    def display_name(self) -> str:
        return "Adzuna Global API"

    @property
    def requires_api_key(self) -> bool:
        return True

    def is_configured(self) -> bool:
        return bool(settings.ADZUNA_APP_ID and settings.ADZUNA_APP_KEY)

    def get_configuration_help(self) -> Optional[str]:
        if not self.is_configured():
            return (
                "Adzuna provides granular local and regional job listings worldwide. "
                "To enable it, get free developer keys at https://developer.adzuna.com and "
                "add ADZUNA_APP_ID and ADZUNA_APP_KEY to backend/.env."
            )
        return None

    async def fetch_jobs(
        self,
        query: Optional[str] = None,
        country: Optional[str] = None,
        states: Optional[List[str]] = None,
        city: Optional[str] = None,
        remote_only: bool = False,
        limit: int = 40
    ) -> List[Dict[str, Any]]:
        if not self.is_configured():
            return []

        country_code = (country or "US").lower()
        if country_code not in ["us", "gb", "ca", "de", "in", "au", "nz", "fr"]:
            country_code = "us"

        params: Dict[str, Any] = {
            "app_id": settings.ADZUNA_APP_ID,
            "app_key": settings.ADZUNA_APP_KEY,
            "results_per_page": min(limit, 30),
            "content-type": "application/json"
        }

        if query and query.strip():
            params["what"] = query.strip()
        else:
            params["what"] = "software developer"

        # Construct location filter (e.g. state or city)
        loc_parts = []
        if city:
            loc_parts.append(city)
        if states and len(states) > 0:
            loc_parts.append(states[0])
        if loc_parts:
            params["where"] = ", ".join(loc_parts)

        jobs: List[Dict[str, Any]] = []

        try:
            url = f"{self.BASE_URL}/{country_code}/search/1"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                
                if response.status_code != 200:
                    logger.warning("Adzuna API returned status %s: %s", response.status_code, response.text)
                    return []

                payload = response.json()
                results = payload.get("results", [])

                for item in results:
                    job_id = str(item.get("id") or "")
                    title = item.get("title") or "Position"
                    company = item.get("company", {}).get("display_name") or "Employer"
                    loc_display = item.get("location", {}).get("display_name") or country_code.upper()
                    url = item.get("redirect_url") or ""
                    description = clean_description(item.get("description") or "")
                    
                    # Salary
                    salary_min = item.get("salary_min")
                    salary_max = item.get("salary_max")
                    salary_text = None
                    if salary_min or salary_max:
                        if salary_min and salary_max:
                            salary_text = f"${int(salary_min):,} - ${int(salary_max):,}"
                        elif salary_min:
                            salary_text = f"From ${int(salary_min):,}"

                    is_remote = "remote" in title.lower() or "remote" in loc_display.lower() or "remote" in description.lower()

                    posted_at = None
                    created_str = item.get("created")
                    if created_str:
                        try:
                            posted_at = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                        except Exception:
                            pass

                    jobs.append({
                        "source_id": job_id,
                        "source_name": self.source_name,
                        "title": title,
                        "company": company,
                        "location": loc_display,
                        "country": country_code.upper(),
                        "state": states[0] if states else None,
                        "city": city,
                        "is_remote": is_remote,
                        "employment_type": "full_time",
                        "salary_min": float(salary_min) if salary_min else None,
                        "salary_max": float(salary_max) if salary_max else None,
                        "salary_currency": "USD" if country_code == "us" else None,
                        "salary_text": salary_text,
                        "url": url,
                        "description": description,
                        "skills_required": [],
                        "posted_at": posted_at
                    })

        except Exception as exc:
            logger.error("Error querying Adzuna adapter: %s", exc)

        return jobs
