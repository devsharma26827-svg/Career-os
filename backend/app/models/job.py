from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class JobListing(Base):
    __tablename__ = "job_listings"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(String, index=True, nullable=False)
    source_name = Column(String, index=True, nullable=False)  # "arbeitnow", "remoteok", "jobicy", "adzuna"
    
    title = Column(String, index=True, nullable=False)
    company = Column(String, index=True, nullable=False)
    location = Column(String, nullable=False, default="Remote")
    country = Column(String, index=True, nullable=True)
    state = Column(String, index=True, nullable=True)
    city = Column(String, nullable=True)
    is_remote = Column(Boolean, default=False, index=True)
    
    employment_type = Column(String, default="full_time")  # "full_time", "contract", "part_time", etc.
    salary_min = Column(Float, nullable=True)
    salary_max = Column(Float, nullable=True)
    salary_currency = Column(String, nullable=True)
    salary_text = Column(String, nullable=True)  # e.g. "$120,000 - $140,000 / yr"
    
    url = Column(String, nullable=False)  # Canonical link to original job posting
    source_listing_url = Column(String, nullable=True)  # Aggregator / source board listing URL
    application_url = Column(String, nullable=True)  # Direct employer careers page / ATS link
    company_website_url = Column(String, nullable=True)
    last_verified_at = Column(DateTime, nullable=True)
    description = Column(Text, nullable=False)
    skills_required = Column(Text, default="[]")  # JSON list of required skills
    
    posted_at = Column(DateTime, nullable=True)
    cached_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)

    __table_args__ = (
        UniqueConstraint("source_name", "source_id", name="uq_source_job_id"),
    )

    saved_by_users = relationship("SavedJob", back_populates="job", cascade="all, delete-orphan")


class SavedJob(Base):
    __tablename__ = "saved_jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("job_listings.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Checkbox indicating user selected this job for the application queue (Module 3)
    is_selected_for_apply = Column(Boolean, default=False, index=True)
    notes = Column(Text, nullable=True)
    saved_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_user_saved_job"),
    )

    user = relationship("User", backref="saved_jobs")
    job = relationship("JobListing", back_populates="saved_by_users")


class SearchPreference(Base):
    __tablename__ = "search_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    
    keywords = Column(String, nullable=True)
    country = Column(String, default="US")
    states = Column(Text, default="[]")  # JSON list of selected states
    city = Column(String, nullable=True)
    remote_only = Column(Boolean, default=False)
    employment_type = Column(String, nullable=True)  # "all", "full_time", "contract", etc.
    min_salary = Column(Float, nullable=True)
    
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", backref="search_preference")
