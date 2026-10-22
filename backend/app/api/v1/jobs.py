import json
import math
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.locations import (
    get_supported_locations,
    matches_location_filter,
    classify_location_hierarchy,
    normalize_job_location,
    SUPPORTED_COUNTRIES
)
from app.models.job import JobListing, SavedJob, SearchPreference
from app.models.profile import UserProfile
from app.models.user import User
from app.schemas.job import (
    JobListingResponse,
    JobSearchResponse,
    SavedJobToggleRequest,
    SearchPreferenceResponse,
    SearchPreferenceUpdate,
    SelectForApplyRequest,
    BatchSelectForApplyRequest,
    SourceHealth,
)
from app.services.job_matcher import JobMatcher
from app.services.job_sources.manager import JobSourceManager

router = APIRouter(prefix="/jobs", tags=["Job Discovery & Matching"])
source_manager = JobSourceManager()


@router.get("/locations")
def list_supported_locations():
    """Returns list of supported countries and their respective states/provinces."""
    return get_supported_locations()


@router.get("/sources", response_model=List[SourceHealth])
def list_job_sources():
    """Lists registered job source adapters, status, and configuration help."""
    return source_manager.get_source_statuses()


@router.get("/search", response_model=JobSearchResponse)
async def search_jobs(
    query: Optional[str] = Query(None, description="Job title, keywords, or skills"),
    country: Optional[str] = Query(None, description="Target country code (e.g. US, GB, CA, IN, REMOTE, or None for Worldwide)"),
    states: Optional[List[str]] = Query(None, description="One or more state codes within the selected country"),
    city: Optional[str] = Query(None, description="Optional city filter"),
    remote_only: bool = Query(False, description="Filter strictly for remote opportunities"),
    employment_type: Optional[str] = Query(None, description="Employment type filter"),
    min_match_score: Optional[float] = Query(None, ge=0, le=100, description="Minimum relevance match score"),
    sort_by: str = Query("relevance", description="Sorting option: relevance, date, title"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(15, ge=1, le=50, description="Page size limit"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Searches job opportunities across official and permitted sources.
    Strictly filters by country, multi-state selection, and radius.
    Expands in order: nearby radius -> selected state -> selected country when local results are scarce.
    Computes personalized AI match scores and plain-language explanations.
    """
    # 1. Fetch fresh jobs from external adapters and update DB cache
    synced_jobs, source_statuses = await source_manager.search_and_sync(
        db=db,
        query=query,
        country=country,
        states=states,
        city=city,
        remote_only=remote_only
    )

    # 2. Retrieve active jobs from database (strictly excluding demo/mock records)
    db_query = db.query(JobListing).filter(
        JobListing.is_active == True,
        JobListing.source_name != "official_feed"
    )
    if remote_only:
        db_query = db_query.filter(JobListing.is_remote == True)

    candidate_jobs = db_query.all()

    # Helper function to check keywords & employment type
    def passes_content_filters(job: JobListing) -> bool:
        if query and query.strip():
            q_words = [w.lower() for w in query.strip().split() if len(w) > 1]
            content = f"{job.title} {job.company} {job.skills_required} {job.description}".lower()
            if not any(qw in content for qw in q_words):
                return False
        if employment_type and employment_type != "all":
            if job.employment_type and job.employment_type != employment_type:
                return False
        return True

    # 3. Progressive Location Expansion Hierarchy:
    # Tier 1: Exact City Match (if city requested)
    # Tier 2: Nearby Radius / Metro Area
    # Tier 3: State Level
    # Tier 4: Country Level / Eligible Remote
    filtered_jobs: List[JobListing] = []
    expansion_notice: Optional[str] = None
    is_expanded = False

    # Check strict city match first if city provided
    if city and city.strip():
        city_jobs = [
            j for j in candidate_jobs
            if passes_content_filters(j) and matches_location_filter(
                job_location=j.location,
                job_country=j.country,
                job_is_remote=j.is_remote,
                filter_country=country,
                filter_states=states,
                filter_city=city,
                remote_only=remote_only,
                job_title=j.title
            )
        ]

        if len(city_jobs) >= 5:
            filtered_jobs = city_jobs
        else:
            # Expand to nearby radius / state / country
            is_expanded = True
            expanded_candidates = [
                j for j in candidate_jobs
                if passes_content_filters(j) and matches_location_filter(
                    job_location=j.location,
                    job_country=j.country,
                    job_is_remote=j.is_remote,
                    filter_country=country,
                    filter_states=states,
                    filter_city=None,  # Expand beyond city
                    remote_only=remote_only,
                    job_title=j.title
                )
            ]
            # If still fewer than 5, expand to full country
            if len(expanded_candidates) < 5 and states:
                expanded_country = [
                    j for j in candidate_jobs
                    if passes_content_filters(j) and matches_location_filter(
                        job_location=j.location,
                        job_country=j.country,
                        job_is_remote=j.is_remote,
                        filter_country=country,
                        filter_states=None,  # Expand beyond state
                        filter_city=None,
                        remote_only=remote_only,
                        job_title=j.title
                    )
                ]
                seen_ids = {j.id for j in expanded_candidates}
                for c_job in expanded_country:
                    if c_job.id not in seen_ids:
                        expanded_candidates.append(c_job)

            filtered_jobs = expanded_candidates
            c_name = SUPPORTED_COUNTRIES.get(country.upper(), {}).get("name", country) if country else "Worldwide"
            st_name = states[0] if states else "state"
            if len(city_jobs) > 0:
                expansion_notice = f"Showing {len(city_jobs)} direct match(es) in {city}, expanded to {st_name} and {c_name} for additional opportunities."
            else:
                expansion_notice = f"No direct matches in {city}. Expanded search to {st_name} and {c_name} to find relevant roles."

    elif states and len(states) > 0:
        state_jobs = [
            j for j in candidate_jobs
            if passes_content_filters(j) and matches_location_filter(
                job_location=j.location,
                job_country=j.country,
                job_is_remote=j.is_remote,
                filter_country=country,
                filter_states=states,
                filter_city=None,
                remote_only=remote_only,
                job_title=j.title
            )
        ]

        if len(state_jobs) >= 5:
            filtered_jobs = state_jobs
        else:
            # Expand to country
            is_expanded = True
            country_jobs = [
                j for j in candidate_jobs
                if passes_content_filters(j) and matches_location_filter(
                    job_location=j.location,
                    job_country=j.country,
                    job_is_remote=j.is_remote,
                    filter_country=country,
                    filter_states=None,
                    filter_city=None,
                    remote_only=remote_only,
                    job_title=j.title
                )
            ]
            filtered_jobs = country_jobs
            c_name = SUPPORTED_COUNTRIES.get(country.upper(), {}).get("name", country) if country else "Worldwide"
            expansion_notice = f"Showing state opportunities, expanded to national roles in {c_name}."

    else:
        # Strict Country Filter
        filtered_jobs = [
            j for j in candidate_jobs
            if passes_content_filters(j) and matches_location_filter(
                job_location=j.location,
                job_country=j.country,
                job_is_remote=j.is_remote,
                filter_country=country,
                filter_states=None,
                filter_city=None,
                remote_only=remote_only,
                job_title=j.title
            )
        ]

    # 4. Fetch candidate profile and saved jobs
    user_profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    saved_records = db.query(SavedJob).filter(SavedJob.user_id == current_user.id).all()
    saved_job_ids = {s.job_id for s in saved_records}
    selected_apply_ids = {s.job_id for s in saved_records if s.is_selected_for_apply}

    # 5. Compute match scores & assign location expansion metadata
    evaluated_jobs: List[JobListingResponse] = []
    user_country_pref = country if country and country.upper() not in ["ALL", "WORLDWIDE", "GLOBAL"] else None
    for job in filtered_jobs:
        match_details = JobMatcher.evaluate(
            profile=user_profile,
            job=job,
            user_country_preference=user_country_pref
        )

        effective_min = min_match_score if min_match_score is not None else (25.0 if user_profile and (user_profile.headline or user_profile.skills or user_profile.experiences) else None)
        if effective_min is not None and match_details.score < effective_min:
            continue

        raw_skills = json.loads(job.skills_required or "[]")
        skills_list = [str(s) for s in raw_skills] if isinstance(raw_skills, list) else []

        exp_level, loc_exp = classify_location_hierarchy(
            job_city=job.city,
            job_state=job.state,
            job_country=job.country,
            job_location=job.location,
            filter_city=city,
            filter_states=states,
            filter_country=country,
            is_remote=job.is_remote
        )

        is_verified = bool(
            job.url and
            job.url.startswith("http") and
            "example.com" not in job.url and
            not job.url.endswith("#") and
            job.url != "https://jobpulse.local"
        )

        evaluated_jobs.append(
            JobListingResponse(
                id=job.id,
                source_id=job.source_id,
                source_name=job.source_name,
                title=job.title,
                company=job.company,
                location=job.location,
                country=job.country,
                state=job.state,
                city=job.city,
                is_remote=job.is_remote,
                employment_type=job.employment_type or "full_time",
                salary_min=job.salary_min,
                salary_max=job.salary_max,
                salary_currency=job.salary_currency,
                salary_text=job.salary_text,
                url=job.url,
                source_listing_url=getattr(job, "source_listing_url", None) or job.url,
                application_url=getattr(job, "application_url", None),
                company_website_url=getattr(job, "company_website_url", None),
                last_verified_at=getattr(job, "last_verified_at", None),
                description=job.description,
                skills_required=skills_list,
                posted_at=job.posted_at,
                cached_at=job.cached_at,
                is_active=job.is_active,
                match=match_details,
                is_saved=job.id in saved_job_ids,
                is_selected_for_apply=job.id in selected_apply_ids,
                is_verified_link=is_verified,
                expansion_level=exp_level,
                location_explanation=loc_exp
            )
        )

    # 6. Sort results: Prioritize local radius tiers alongside AI match score
    tier_weights = {"city": 300.0, "nearby": 200.0, "state": 100.0, "country": 0.0}

    if sort_by == "relevance":
        evaluated_jobs.sort(
            key=lambda j: (
                tier_weights.get(j.expansion_level or "country", 0.0) + (j.match.score if j.match else 0.0)
            ),
            reverse=True
        )
    elif sort_by == "date":
        evaluated_jobs.sort(
            key=lambda j: (j.posted_at or j.cached_at or datetime.min.replace(tzinfo=timezone.utc)),
            reverse=True
        )
    elif sort_by == "title":
        evaluated_jobs.sort(key=lambda j: j.title.lower())

    # 6b. Company Diversity: Cap results to at most 2 per company unless explicit company query
    company_counts: Dict[str, int] = {}
    is_company_query = bool(query and query.strip())
    diverse_jobs: List[JobListingResponse] = []
    for ej in evaluated_jobs:
        c_norm = (ej.company or "").strip().lower()
        if is_company_query and query.strip().lower() in c_norm:
            diverse_jobs.append(ej)
        else:
            if company_counts.get(c_norm, 0) < 2:
                company_counts[c_norm] = company_counts.get(c_norm, 0) + 1
                diverse_jobs.append(ej)

    # 7. Paginate
    total = len(diverse_jobs)
    total_pages = max(1, math.ceil(total / page_size))
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_jobs = diverse_jobs[start_idx:end_idx]

    # Notify user on meaningful completed search
    if total > 0 and page == 1 and (query or states or country):
        from app.services.notification_service import NotificationService
        search_desc = f"'{query}'" if query else "matching roles"
        loc_desc = country if country else "selected location"
        NotificationService.create_notification(
            db=db,
            user_id=current_user.id,
            title="Job Search Completed",
            message=f"Discovered {total} {search_desc} in {loc_desc}.",
            notification_type="job_search_completed",
            link="/jobs"
        )

    return JobSearchResponse(
        jobs=paginated_jobs,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        source_statuses=source_statuses,
        last_checked=datetime.now(timezone.utc),
        expansion_notice=expansion_notice
    )


@router.get("/preferences", response_model=SearchPreferenceResponse)
def get_search_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves saved job search preferences for the current user."""
    pref = db.query(SearchPreference).filter(SearchPreference.user_id == current_user.id).first()
    if not pref:
        pref = SearchPreference(
            user_id=current_user.id,
            keywords="",
            country="US",
            states="[]",
            city="",
            remote_only=False,
            employment_type="all"
        )
        db.add(pref)
        db.commit()
        db.refresh(pref)

    states_list = json.loads(pref.states or "[]")
    return SearchPreferenceResponse(
        id=pref.id,
        user_id=pref.user_id,
        keywords=pref.keywords,
        country=pref.country,
        states=states_list,
        city=pref.city,
        remote_only=pref.remote_only,
        employment_type=pref.employment_type,
        min_salary=pref.min_salary,
        updated_at=pref.updated_at
    )


@router.put("/preferences", response_model=SearchPreferenceResponse)
def update_search_preferences(
    pref_in: SearchPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Saves or updates job search preferences for the user."""
    pref = db.query(SearchPreference).filter(SearchPreference.user_id == current_user.id).first()
    if not pref:
        pref = SearchPreference(user_id=current_user.id)
        db.add(pref)

    pref.keywords = pref_in.keywords
    pref.country = pref_in.country
    pref.states = json.dumps(pref_in.states)
    pref.city = pref_in.city
    pref.remote_only = pref_in.remote_only
    pref.employment_type = pref_in.employment_type
    pref.min_salary = pref_in.min_salary

    db.commit()
    db.refresh(pref)

    states_list = json.loads(pref.states or "[]")
    return SearchPreferenceResponse(
        id=pref.id,
        user_id=pref.user_id,
        keywords=pref.keywords,
        country=pref.country,
        states=states_list,
        city=pref.city,
        remote_only=pref.remote_only,
        employment_type=pref.employment_type,
        min_salary=pref.min_salary,
        updated_at=pref.updated_at
    )


@router.post("/save")
def toggle_save_job(
    request: SavedJobToggleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Saves or bookmarks a job for later review."""
    job = db.query(JobListing).filter(JobListing.id == request.job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job listing not found."
        )

    saved = db.query(SavedJob).filter(
        SavedJob.user_id == current_user.id,
        SavedJob.job_id == request.job_id
    ).first()

    if saved:
        db.delete(saved)
        db.commit()
        return {"message": "Job removed from saved list.", "is_saved": False}
    else:
        new_saved = SavedJob(
            user_id=current_user.id,
            job_id=request.job_id,
            notes=request.notes
        )
        db.add(new_saved)
        db.commit()
        return {"message": "Job saved successfully.", "is_saved": True}


@router.delete("/save/{job_id}")
def unsave_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Removes a job from saved list."""
    saved = db.query(SavedJob).filter(
        SavedJob.user_id == current_user.id,
        SavedJob.job_id == job_id
    ).first()
    if not saved:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found in saved list."
        )

    db.delete(saved)
    db.commit()
    return {"message": "Job unsaved."}


@router.get("/saved", response_model=List[JobListingResponse])
def list_saved_jobs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns all jobs saved/bookmarked by the current user."""
    user_profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    saved_records = db.query(SavedJob).filter(SavedJob.user_id == current_user.id).all()
    
    result = []
    for record in saved_records:
        job = record.job
        if not job:
            continue
        
        match_details = JobMatcher.evaluate(profile=user_profile, job=job)
        raw_skills = json.loads(job.skills_required or "[]")
        is_verified = bool(
            job.url and
            job.url.startswith("http") and
            "example.com" not in job.url and
            not job.url.endswith("#") and
            job.url != "https://jobpulse.local"
        )

        result.append(
            JobListingResponse(
                id=job.id,
                source_id=job.source_id,
                source_name=job.source_name,
                title=job.title,
                company=job.company,
                location=job.location,
                country=job.country,
                state=job.state,
                city=job.city,
                is_remote=job.is_remote,
                employment_type=job.employment_type or "full_time",
                salary_min=job.salary_min,
                salary_max=job.salary_max,
                salary_currency=job.salary_currency,
                salary_text=job.salary_text,
                url=job.url,
                source_listing_url=getattr(job, "source_listing_url", None) or job.url,
                application_url=getattr(job, "application_url", None),
                company_website_url=getattr(job, "company_website_url", None),
                last_verified_at=getattr(job, "last_verified_at", None),
                description=job.description,
                skills_required=raw_skills,
                posted_at=job.posted_at,
                cached_at=job.cached_at,
                is_active=job.is_active,
                match=match_details,
                is_saved=True,
                is_selected_for_apply=record.is_selected_for_apply,
                is_verified_link=is_verified
            )
        )

    return result


@router.post("/select")
def toggle_select_for_apply(
    request: SelectForApplyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Selects or deselects a job for application queue (Module 3).
    Automatically saves the job if not already saved.
    """
    saved = db.query(SavedJob).filter(
        SavedJob.user_id == current_user.id,
        SavedJob.job_id == request.job_id
    ).first()

    if not saved:
        # Create saved job entry
        saved = SavedJob(
            user_id=current_user.id,
            job_id=request.job_id,
            is_selected_for_apply=request.selected
        )
        db.add(saved)
    else:
        saved.is_selected_for_apply = request.selected

    db.commit()
    return {
        "message": f"Job {'selected for application queue' if request.selected else 'deselected'}.",
        "is_selected_for_apply": request.selected
    }


@router.post("/batch-select")
def batch_select_for_apply(
    request: BatchSelectForApplyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Selects or deselects multiple jobs for application queue in one operation.
    """
    if not request.job_ids:
        return {"message": "No jobs provided", "selected_count": 0, "selected": request.selected}

    # Fetch existing saved jobs for these job_ids
    existing = (
        db.query(SavedJob)
        .filter(SavedJob.user_id == current_user.id, SavedJob.job_id.in_(request.job_ids))
        .all()
    )
    existing_map = {s.job_id: s for s in existing}

    for job_id in request.job_ids:
        if job_id in existing_map:
            existing_map[job_id].is_selected_for_apply = request.selected
        else:
            new_saved = SavedJob(
                user_id=current_user.id,
                job_id=job_id,
                is_selected_for_apply=request.selected
            )
            db.add(new_saved)

    db.commit()
    return {
        "message": f"Successfully updated {len(request.job_ids)} jobs.",
        "selected_count": len(request.job_ids) if request.selected else 0,
        "selected": request.selected
    }


@router.get("/selected", response_model=List[JobListingResponse])
def list_selected_for_apply_jobs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns all jobs selected by the user for the application queue."""
    user_profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    selected_records = db.query(SavedJob).filter(
        SavedJob.user_id == current_user.id,
        SavedJob.is_selected_for_apply == True
    ).all()

    result = []
    for record in selected_records:
        job = record.job
        if not job:
            continue
        
        match_details = JobMatcher.evaluate(profile=user_profile, job=job)
        raw_skills = json.loads(job.skills_required or "[]")

        result.append(
            JobListingResponse(
                id=job.id,
                source_id=job.source_id,
                source_name=job.source_name,
                title=job.title,
                company=job.company,
                location=job.location,
                country=job.country,
                state=job.state,
                city=job.city,
                is_remote=job.is_remote,
                employment_type=job.employment_type or "full_time",
                salary_min=job.salary_min,
                salary_max=job.salary_max,
                salary_currency=job.salary_currency,
                salary_text=job.salary_text,
                url=job.url,
                source_listing_url=getattr(job, "source_listing_url", None) or job.url,
                application_url=getattr(job, "application_url", None),
                company_website_url=getattr(job, "company_website_url", None),
                last_verified_at=getattr(job, "last_verified_at", None),
                description=job.description,
                skills_required=raw_skills,
                posted_at=job.posted_at,
                cached_at=job.cached_at,
                is_active=job.is_active,
                match=match_details,
                is_saved=True,
                is_selected_for_apply=True
            )
        )

    return result
