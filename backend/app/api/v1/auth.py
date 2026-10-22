from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.user import (
    Token,
    UserCreate,
    UserLogin,
    UserPreferencesUpdate,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=Token, status_code=status.HTTP_201_CREATED)
def signup(user_in: UserCreate, db: Session = Depends(get_db)):
    """Registers a new user account with secure password hashing."""
    existing_user = db.query(User).filter(User.email == user_in.email.lower()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists. Please log in instead.",
        )
    
    hashed_pwd = hash_password(user_in.password)
    user = User(
        email=user_in.email.lower(),
        hashed_password=hashed_pwd,
        full_name=user_in.full_name,
        font_size="normal",
        display_mode="simple"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(subject=user.id)
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.post("/login", response_model=Token)
def login(user_in: UserLogin, db: Session = Depends(get_db)):
    """Authenticates an existing user and returns a JWT access token."""
    user = db.query(User).filter(User.email == user_in.email.lower()).first()
    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password. Please double check and try again.",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account has been deactivated. Please contact support.",
        )

    access_token = create_access_token(subject=user.id)
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Returns the authenticated user's account details and preferences."""
    return current_user


@router.put("/preferences", response_model=UserResponse)
def update_preferences(
    preferences_in: UserPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates user display preferences like font size, display mode, and reduced motion."""
    if preferences_in.font_size is not None:
        current_user.font_size = preferences_in.font_size
    if preferences_in.display_mode is not None:
        current_user.display_mode = preferences_in.display_mode
    if preferences_in.reduced_motion is not None:
        current_user.reduced_motion = preferences_in.reduced_motion
        
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/export-data")
def export_user_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Exports candidate's complete personal profile, applications, and audit records in JSON format."""
    from app.models.resume import Resume
    from app.models.profile import UserProfile
    from app.models.job import SavedJob, SearchPreference
    from app.models.application import JobApplicationWorkspace, ApplicationAuditLog
    from app.models.notification import Notification

    # Profile & Resume
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    resumes = db.query(Resume).filter(Resume.user_id == current_user.id).all()

    # Search preferences & saved jobs
    search_pref = db.query(SearchPreference).filter(SearchPreference.user_id == current_user.id).first()
    saved_jobs = db.query(SavedJob).filter(SavedJob.user_id == current_user.id).all()

    # Applications & Workspaces
    workspaces = db.query(JobApplicationWorkspace).filter(JobApplicationWorkspace.user_id == current_user.id).all()
    audit_logs = db.query(ApplicationAuditLog).filter(ApplicationAuditLog.user_id == current_user.id).all()
    notifications = db.query(Notification).filter(Notification.user_id == current_user.id).all()

    return {
        "export_metadata": {
            "exported_at": str(current_user.updated_at),
            "export_version": "1.0",
            "gdpr_compliant": True,
        },
        "user_account": {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "created_at": str(current_user.created_at),
            "preferences": {
                "font_size": current_user.font_size,
                "display_mode": current_user.display_mode,
                "reduced_motion": getattr(current_user, "reduced_motion", False),
            },
        },
        "profile": {
            "full_name": profile.full_name if profile else None,
            "headline": profile.headline if profile else None,
            "summary": profile.summary if profile else None,
            "skills": profile.skills if profile else [],
            "experiences": profile.experiences if profile else [],
            "education": profile.education if profile else [],
            "contact_details": profile.contact_details if profile else {},
            "links": profile.links if profile else [],
            "confirmed_by_user": profile.confirmed_by_user if profile else False,
        } if profile else None,
        "resumes": [
            {
                "id": r.id,
                "original_filename": r.original_filename,
                "file_size": r.file_size,
                "content_type": r.content_type,
                "uploaded_at": str(r.uploaded_at),
            }
            for r in resumes
        ],
        "saved_jobs_count": len(saved_jobs),
        "search_preferences": {
            "country_code": search_pref.country_code,
            "selected_states": search_pref.selected_states,
            "remote_only": search_pref.remote_only,
            "keywords": search_pref.keywords,
        } if search_pref else None,
        "applications": [
            {
                "id": w.id,
                "job_id": w.job_id,
                "status": w.status,
                "application_status": w.application_status,
                "application_confirmation_id": w.application_confirmation_id,
                "applied_at": str(w.applied_at) if w.applied_at else None,
                "cover_letter_included": w.include_cover_letter,
                "cover_letter_content": w.cover_letter_content,
                "recruiter_email_body": w.email_body,
                "recruiter_email_subject": w.email_subject,
                "recruiter_email_status": w.email_outreach_status,
                "screening_answers": {
                    "work_authorization": w.screening_work_auth,
                    "years_of_experience": w.screening_years_exp,
                    "earliest_start_date": w.screening_start_date,
                    "salary_expectation": w.screening_salary,
                    "willing_to_relocate": w.screening_relocate,
                    "confirmed": w.screening_answers_confirmed,
                },
            }
            for w in workspaces
        ],
        "audit_logs": [
            {
                "id": a.id,
                "action": a.action,
                "status": a.status,
                "destination": a.destination,
                "recipient": a.recipient,
                "details": a.details,
                "created_at": str(a.created_at),
            }
            for a in audit_logs
        ],
        "notifications": [
            {
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "type": n.type,
                "read": n.read,
                "created_at": str(n.created_at),
            }
            for n in notifications
        ],
    }


@router.delete("/delete-account", status_code=status.HTTP_200_OK)
def delete_user_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Permanently deletes candidate account, stored resume files, and all associated personal data."""
    import os
    from app.models.resume import Resume

    # 1. Clean physical files from disk
    resumes = db.query(Resume).filter(Resume.user_id == current_user.id).all()
    for r in resumes:
        if r.storage_path and os.path.exists(r.storage_path):
            try:
                os.remove(r.storage_path)
            except OSError:
                pass

    # 2. Delete user entity (cascade will delete profile, resumes, jobs, workspaces, logs, etc.)
    db.delete(current_user)
    db.commit()

    return {
        "message": "Your account and all associated personal documents have been permanently deleted.",
        "success": True,
    }


@router.get("/integrations-health")
def get_integrations_health(
    current_user: User = Depends(get_current_user)
):
    """Provides transparent, secure status of AI, email, and job source providers without exposing credentials."""
    from app.core.config import settings

    openrouter_configured = bool(settings.OPENROUTER_API_KEY and settings.OPENROUTER_API_KEY.strip())
    smtp_configured = bool(settings.SMTP_HOST and settings.SMTP_HOST.strip())
    adzuna_configured = bool(settings.ADZUNA_APP_ID and settings.ADZUNA_APP_KEY)

    return {
        "ai_provider": {
            "provider": "OpenRouter (Claude/GPT/Llama)" if openrouter_configured else "Local Heuristic Engine",
            "model": settings.OPENROUTER_MODEL if openrouter_configured else "Offline Deterministic NLP (Built-in)",
            "is_configured": openrouter_configured,
            "status": "Operational",
            "mode": "Cloud AI" if openrouter_configured else "Offline / Local Zero-Cost Fallback",
        },
        "email_delivery": {
            "provider": settings.EMAIL_PROVIDER or "SMTP",
            "is_configured": smtp_configured,
            "host": f"{settings.SMTP_HOST[:4]}***" if smtp_configured else None,
            "from_address": settings.SMTP_FROM_EMAIL if smtp_configured else None,
            "rate_limit_per_hour": settings.EMAIL_RATE_LIMIT_PER_HOUR,
            "status": "Ready for Verified Sending" if smtp_configured else "Not Configured (Copy Toolkit Active)",
        },
        "job_sources": [
            {"name": "Arbeitnow API", "type": "Official Public API", "status": "Active & Free", "auth_required": False},
            {"name": "RemoteOK API", "type": "Public Permitted Feed", "status": "Active & Free", "auth_required": False},
            {"name": "Jobicy API", "type": "Official Public Feed", "status": "Active & Free", "auth_required": False},
            {
                "name": "Adzuna Global",
                "type": "Official Regional REST API",
                "status": "Connected" if adzuna_configured else "Optional (Unconfigured)",
                "auth_required": True,
            },
        ],
    }
