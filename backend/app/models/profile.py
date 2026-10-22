from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    
    # Core contact details
    full_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    location = Column(String, nullable=True)
    headline = Column(String, nullable=True)
    summary = Column(Text, nullable=True)
    
    # Links
    linkedin_url = Column(String, nullable=True)
    github_url = Column(String, nullable=True)
    portfolio_url = Column(String, nullable=True)
    
    # Structured collections stored as JSON strings
    skills = Column(Text, default="[]")  # JSON list of strings or tags
    experiences = Column(Text, default="[]")  # JSON list of Experience objects
    education = Column(Text, default="[]")  # JSON list of Education objects
    projects = Column(Text, default="[]")  # JSON list of Project objects
    
    # Parser metadata
    parser_source = Column(String, default="heuristic")  # "openrouter" or "heuristic"
    raw_extracted_text = Column(Text, nullable=True)
    is_confirmed = Column(Boolean, default=False)
    
    # Confidence and evidence tracking
    confidence_scores = Column(Text, default="{}")
    uncertain_fields = Column(Text, default="[]")
    field_evidence = Column(Text, default="{}")
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="profile")
