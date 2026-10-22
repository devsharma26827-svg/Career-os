import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.profile import UserProfile
from app.models.resume import Resume
from app.models.user import User
from app.schemas.profile import (
    EducationItem,
    ExperienceItem,
    ProfileResponse,
    ProfileUpdate,
    ProjectItem,
)
from app.services.resume_parser import parse_resume_file

router = APIRouter(prefix="/profile", tags=["Profile"])


def _calculate_missing_fields(profile_dict: dict) -> List[str]:
    missing = []
    if not profile_dict.get("full_name"):
        missing.append("full_name")
    if not profile_dict.get("email"):
        missing.append("email")
    if not profile_dict.get("phone"):
        missing.append("phone")
    if not profile_dict.get("headline"):
        missing.append("headline")
    if not profile_dict.get("skills"):
        missing.append("skills")
    if not profile_dict.get("experiences"):
        missing.append("experiences")
    if not profile_dict.get("education"):
        missing.append("education")
    return missing


def _format_profile_response(profile: UserProfile) -> ProfileResponse:
    skills = json.loads(profile.skills or "[]")
    raw_exp = json.loads(profile.experiences or "[]")
    raw_edu = json.loads(profile.education or "[]")
    raw_proj = json.loads(profile.projects or "[]")

    experiences = [ExperienceItem(**item) for item in raw_exp]
    education = [EducationItem(**item) for item in raw_edu]
    projects = [ProjectItem(**item) for item in raw_proj]

    profile_dict = {
        "full_name": profile.full_name,
        "email": profile.email,
        "phone": profile.phone,
        "headline": profile.headline,
        "skills": skills,
        "experiences": experiences,
        "education": education,
    }

    confidence_scores = json.loads(profile.confidence_scores or "{}")
    uncertain_fields = json.loads(profile.uncertain_fields or "[]")
    field_evidence = json.loads(profile.field_evidence or "{}")

    missing_fields = _calculate_missing_fields(profile_dict)

    return ProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        full_name=profile.full_name,
        email=profile.email,
        phone=profile.phone,
        location=profile.location,
        headline=profile.headline,
        summary=profile.summary,
        linkedin_url=profile.linkedin_url,
        github_url=profile.github_url,
        portfolio_url=profile.portfolio_url,
        skills=skills,
        experiences=experiences,
        education=education,
        projects=projects,
        parser_source=profile.parser_source or "heuristic",
        is_confirmed=profile.is_confirmed,
        missing_fields=missing_fields,
        confidence_scores=confidence_scores,
        uncertain_fields=uncertain_fields,
        field_evidence=field_evidence,
        created_at=profile.created_at,
        updated_at=profile.updated_at
    )


@router.get("", response_model=Optional[ProfileResponse])
def get_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves current user's structured profile."""
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        # Create empty profile skeleton with user defaults
        profile = UserProfile(
            user_id=current_user.id,
            full_name=current_user.full_name,
            email=current_user.email,
            skills="[]",
            experiences="[]",
            education="[]",
            projects="[]",
            is_confirmed=False
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return _format_profile_response(profile)


@router.put("", response_model=ProfileResponse)
def update_user_profile(
    profile_in: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates and confirms the user's structured professional profile."""
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)

    profile.full_name = profile_in.full_name
    profile.email = profile_in.email
    profile.phone = profile_in.phone
    profile.location = profile_in.location
    profile.headline = profile_in.headline
    profile.summary = profile_in.summary
    profile.linkedin_url = profile_in.linkedin_url
    profile.github_url = profile_in.github_url
    profile.portfolio_url = profile_in.portfolio_url
    
    profile.skills = json.dumps(profile_in.skills)
    profile.experiences = json.dumps([e.model_dump() for e in profile_in.experiences])
    profile.education = json.dumps([e.model_dump() for e in profile_in.education])
    profile.projects = json.dumps([p.model_dump() for p in profile_in.projects])
    profile.confidence_scores = json.dumps(profile_in.confidence_scores)
    profile.uncertain_fields = json.dumps(profile_in.uncertain_fields)
    profile.field_evidence = json.dumps(profile_in.field_evidence)
    profile.is_confirmed = profile_in.is_confirmed

    # If full name was updated, synchronize with user record
    if profile_in.full_name and current_user.full_name != profile_in.full_name:
        current_user.full_name = profile_in.full_name

    db.commit()
    db.refresh(profile)

    return _format_profile_response(profile)


@router.post("/reparse", response_model=ProfileResponse)
async def reparse_resume(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Re-analyzes the user's active resume and refreshes draft profile fields."""
    resume = db.query(Resume).filter(
        Resume.user_id == current_user.id,
        Resume.is_active == True
    ).order_by(Resume.uploaded_at.desc()).first()

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No uploaded resume found to re-parse. Please upload a resume first."
        )

    parsed_profile = await parse_resume_file(resume.file_path, resume.original_filename)

    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)

    profile.full_name = parsed_profile.full_name or profile.full_name or current_user.full_name
    profile.email = parsed_profile.email or profile.email or current_user.email
    profile.phone = parsed_profile.phone or profile.phone
    profile.location = parsed_profile.location or profile.location
    profile.headline = parsed_profile.headline or profile.headline
    profile.summary = parsed_profile.summary or profile.summary
    profile.linkedin_url = parsed_profile.linkedin_url or profile.linkedin_url
    profile.github_url = parsed_profile.github_url or profile.github_url
    profile.portfolio_url = parsed_profile.portfolio_url or profile.portfolio_url
    
    if parsed_profile.skills:
        profile.skills = json.dumps(parsed_profile.skills)
    if parsed_profile.experiences:
        profile.experiences = json.dumps([e.model_dump() for e in parsed_profile.experiences])
    if parsed_profile.education:
        profile.education = json.dumps([e.model_dump() for e in parsed_profile.education])
    if parsed_profile.projects:
        profile.projects = json.dumps([p.model_dump() for p in parsed_profile.projects])

    profile.confidence_scores = json.dumps(parsed_profile.confidence_scores)
    profile.uncertain_fields = json.dumps(parsed_profile.uncertain_fields)
    profile.field_evidence = json.dumps(parsed_profile.field_evidence)
    profile.parser_source = parsed_profile.parser_source
    profile.raw_extracted_text = parsed_profile.raw_extracted_text
    profile.is_confirmed = False

    db.commit()
    db.refresh(profile)

    return _format_profile_response(profile)
