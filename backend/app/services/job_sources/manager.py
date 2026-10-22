import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.core.locations import matches_location_filter
from app.models.job import JobListing
from app.schemas.job import SourceHealth
from app.services.job_sources.adzuna import AdzunaAdapter
from app.services.job_sources.arbeitnow import ArbeitnowAdapter
from app.services.job_sources.base import BaseJobSourceAdapter
from app.services.job_sources.jobicy import JobicyAdapter
from app.services.job_sources.remoteok import RemoteOkAdapter
from app.services.job_sources.remotive import RemotiveAdapter

logger = logging.getLogger(__name__)


class JobSourceManager:
    """
    Coordinates modular job-source adapters with concurrency,
    rate limit protection, error isolation, deduplication, and caching.
    """

    def __init__(self):
        self.adapters: List[BaseJobSourceAdapter] = [
            ArbeitnowAdapter(),
            RemoteOkAdapter(),
            JobicyAdapter(),
            RemotiveAdapter(),
            AdzunaAdapter()
        ]

    def get_source_statuses(self) -> List[SourceHealth]:
        """Returns the operational status of all registered adapters."""
        statuses = []
        for adapter in self.adapters:
            configured = adapter.is_configured()
            statuses.append(SourceHealth(
                source_name=adapter.source_name,
                display_name=adapter.display_name,
                status="online" if configured else "unconfigured",
                job_count=0,
                requires_key=adapter.requires_api_key,
                config_help=adapter.get_configuration_help()
            ))
        return statuses

    async def search_and_sync(
        self,
        db: Session,
        query: Optional[str] = None,
        country: Optional[str] = None,
        states: Optional[List[str]] = None,
        city: Optional[str] = None,
        remote_only: bool = False,
        limit_per_source: int = 35
    ) -> Tuple[List[JobListing], List[SourceHealth]]:
        """
        Executes concurrent fetching across all active source adapters.
        Deduplicates results and persists fresh listings into SQLite cache.
        """
        tasks = []
        active_adapters: List[BaseJobSourceAdapter] = []

        for adapter in self.adapters:
            if adapter.is_configured():
                active_adapters.append(adapter)
                tasks.append(
                    adapter.fetch_jobs(
                        query=query,
                        country=country,
                        states=states,
                        city=city,
                        remote_only=remote_only,
                        limit=limit_per_source
                    )
                )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_raw_jobs: List[Dict[str, Any]] = []
        source_health_list: List[SourceHealth] = []

        for adapter, res in zip(active_adapters, results):
            if isinstance(res, Exception):
                logger.warning("Adapter %s encountered error: %s", adapter.source_name, res)
                source_health_list.append(SourceHealth(
                    source_name=adapter.source_name,
                    display_name=adapter.display_name,
                    status="error",
                    job_count=0,
                    message=f"Source temporarily unavailable: {str(res)}",
                    requires_key=adapter.requires_api_key,
                    config_help=adapter.get_configuration_help()
                ))
            elif isinstance(res, list):
                count = len(res)
                source_health_list.append(SourceHealth(
                    source_name=adapter.source_name,
                    display_name=adapter.display_name,
                    status="online" if count > 0 else "empty",
                    job_count=count,
                    message=f"Retrieved {count} job(s)" if count > 0 else "No active jobs found for this query",
                    requires_key=adapter.requires_api_key,
                    config_help=adapter.get_configuration_help()
                ))
                all_raw_jobs.extend(res)

        # Include unconfigured adapters in status report so user knows how to enable them
        for adapter in self.adapters:
            if not adapter.is_configured():
                source_health_list.append(SourceHealth(
                    source_name=adapter.source_name,
                    display_name=adapter.display_name,
                    status="unconfigured",
                    job_count=0,
                    message="API credentials not configured",
                    requires_key=adapter.requires_api_key,
                    config_help=adapter.get_configuration_help()
                ))

        # 1. Deduplicate listings
        deduped_raw_jobs = self._deduplicate_raw_jobs(all_raw_jobs)

        # 2. Strict Location Filtering
        filtered_raw_jobs = [
            job for job in deduped_raw_jobs
            if matches_location_filter(
                job_location=job.get("location", ""),
                job_country=job.get("country"),
                job_is_remote=job.get("is_remote", False),
                filter_country=country,
                filter_states=states,
                filter_city=city,
                remote_only=remote_only
            )
        ]

        # 3. Synchronize / Cache in Database
        job_models = self._persist_and_sync_jobs(db, filtered_raw_jobs)

        return job_models, source_health_list

    def _deduplicate_raw_jobs(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Removes duplicates across different job feeds using:
        1. Canonical clean URL
        2. Normalized title + normalized company name
        """
        seen_urls = set()
        seen_signatures = set()
        seen_source_keys = set()
        unique_jobs = []

        for job in jobs:
            raw_url = (job.get("url") or "").strip()
            # Canonical URL (strip query parameters and trailing slashes)
            clean_url = raw_url.split("?")[0].rstrip("/")
            source_key = f"{job.get('source_name')}::{job.get('source_id')}"
            
            title = (job.get("title") or "").strip().lower()
            company = (job.get("company") or "").strip().lower()
            # Normalize title words
            clean_title = re.sub(r"[^a-z0-9]", "", title)
            clean_company = re.sub(r"[^a-z0-9]", "", company)
            signature = f"{clean_title}@@{clean_company}"

            if source_key in seen_source_keys:
                continue
            if clean_url and clean_url in seen_urls:
                continue
            if clean_title and clean_company and signature in seen_signatures:
                continue

            seen_source_keys.add(source_key)
            if clean_url:
                seen_urls.add(clean_url)
            if clean_title and clean_company:
                seen_signatures.add(signature)

            unique_jobs.append(job)

        return unique_jobs

    def _persist_and_sync_jobs(self, db: Session, raw_jobs: List[Dict[str, Any]]) -> List[JobListing]:
        """
        Upserts job records in SQLite.
        Updates cached_at timestamp and returns saved JobListing model instances.
        """
        job_instances: List[JobListing] = []
        now = datetime.now(timezone.utc)

        from app.core.locations import normalize_job_location

        for data in raw_jobs:
            source_name = data["source_name"]
            source_id = str(data["source_id"])

            # Guarantee canonical normalized location metadata
            norm_loc = normalize_job_location(
                raw_location=data.get("location") or "Remote",
                raw_country=data.get("country"),
                raw_is_remote=data.get("is_remote", False)
            )

            existing = db.query(JobListing).filter(
                JobListing.source_name == source_name,
                JobListing.source_id == source_id
            ).first()

            skills_json = json.dumps(data.get("skills_required") or [])

            source_url = data.get("source_listing_url") or data.get("url") or "#"
            app_url = data.get("application_url")
            if not app_url and source_name != "jobicy":
                app_url = source_url
            comp_url = data.get("company_website_url")

            if existing:
                existing.title = data.get("title") or existing.title
                existing.company = data.get("company") or existing.company
                existing.location = norm_loc["canonical_location"]
                existing.country = norm_loc["country"]
                existing.state = norm_loc["state"] or data.get("state")
                existing.city = norm_loc["city"] or data.get("city")
                existing.is_remote = norm_loc["is_remote"]
                existing.employment_type = data.get("employment_type") or existing.employment_type
                existing.salary_min = data.get("salary_min")
                existing.salary_max = data.get("salary_max")
                existing.salary_currency = data.get("salary_currency")
                existing.salary_text = data.get("salary_text")
                existing.url = data.get("url") or existing.url
                existing.source_listing_url = source_url
                existing.application_url = app_url or existing.application_url
                existing.company_website_url = comp_url or existing.company_website_url
                existing.last_verified_at = now
                existing.description = data.get("description") or existing.description
                existing.skills_required = skills_json
                existing.cached_at = now
                existing.is_active = True
                job_instances.append(existing)
            else:
                new_job = JobListing(
                    source_name=source_name,
                    source_id=source_id,
                    title=data.get("title") or "Position",
                    company=data.get("company") or "Company",
                    location=norm_loc["canonical_location"],
                    country=norm_loc["country"],
                    state=norm_loc["state"] or data.get("state"),
                    city=norm_loc["city"] or data.get("city"),
                    is_remote=norm_loc["is_remote"],
                    employment_type=data.get("employment_type") or "full_time",
                    salary_min=data.get("salary_min"),
                    salary_max=data.get("salary_max"),
                    salary_currency=data.get("salary_currency"),
                    salary_text=data.get("salary_text"),
                    url=data.get("url") or "#",
                    source_listing_url=source_url,
                    application_url=app_url,
                    company_website_url=comp_url,
                    last_verified_at=now,
                    description=data.get("description") or "",
                    skills_required=skills_json,
                    posted_at=data.get("posted_at"),
                    cached_at=now,
                    is_active=True
                )
                db.add(new_job)
                job_instances.append(new_job)

        db.commit()
        for j in job_instances:
            db.refresh(j)

        return job_instances
