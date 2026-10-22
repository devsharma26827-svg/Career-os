from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class JobMatchDetails(BaseModel):
    score: float = Field(..., ge=0, le=100, description="Heuristic relevance score between 0 and 100")
    reasons: List[str] = Field(default_factory=list, description="Plain language reasons for the match")
    matched_skills: List[str] = Field(default_factory=list, description="Skills shared by candidate and job")
    unknown_skills: List[str] = Field(default_factory=list, description="Skills mentioned in job not explicitly on resume (treated as unknown, not disqualifying)")
    disclaimer: str = "This match score is a heuristic relevance indicator for discovery, not a guaranteed probability of hiring."

    model_config = ConfigDict(from_attributes=True)


class JobListingResponse(BaseModel):
    id: int
    source_id: str
    source_name: str
    title: str
    company: str
    location: str
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    is_remote: bool = False
    employment_type: str = "full_time"
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = None
    salary_text: Optional[str] = None
    url: str
    source_listing_url: Optional[str] = None
    application_url: Optional[str] = None
    company_website_url: Optional[str] = None
    last_verified_at: Optional[datetime] = None
    description: str
    skills_required: List[str] = Field(default_factory=list)
    posted_at: Optional[datetime] = None
    cached_at: datetime
    is_active: bool = True
    
    # Matching metadata computed for current authenticated user
    match: Optional[JobMatchDetails] = None
    is_saved: bool = False
    is_selected_for_apply: bool = False
    is_verified_link: bool = True
    expansion_level: Optional[str] = None  # "city", "nearby", "state", "country"
    location_explanation: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SourceHealth(BaseModel):
    source_name: str
    display_name: str
    status: str  # "online", "empty", "rate_limited", "unconfigured", "error"
    job_count: int = 0
    message: Optional[str] = None
    requires_key: bool = False
    config_help: Optional[str] = None


class JobSearchResponse(BaseModel):
    jobs: List[JobListingResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    source_statuses: List[SourceHealth]
    last_checked: datetime
    expansion_notice: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SearchPreferenceUpdate(BaseModel):
    keywords: Optional[str] = None
    country: str = "US"
    states: List[str] = Field(default_factory=list)
    city: Optional[str] = None
    remote_only: bool = False
    employment_type: Optional[str] = None
    min_salary: Optional[float] = None


class SearchPreferenceResponse(BaseModel):
    id: int
    user_id: int
    keywords: Optional[str] = None
    country: str
    states: List[str] = Field(default_factory=list)
    city: Optional[str] = None
    remote_only: bool = False
    employment_type: Optional[str] = None
    min_salary: Optional[float] = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SavedJobToggleRequest(BaseModel):
    job_id: int
    notes: Optional[str] = None


class SelectForApplyRequest(BaseModel):
    job_id: int
    selected: bool = True


class BatchSelectForApplyRequest(BaseModel):
    job_ids: List[int] = Field(..., description="List of job IDs to select or deselect")
    selected: bool = True
