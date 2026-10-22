import json
import os
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.profile import UserProfile
from app.models.resume import Resume
from app.models.user import User
from app.schemas.profile import ParsedResumeProfile
from app.schemas.resume import ResumeResponse, ResumeUploadResponse
from app.services.file_extractor import FileExtractionError
from app.services.resume_parser import parse_resume_file

router = APIRouter(prefix="/resume", tags=["Resume"])


@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Uploads a resume file (.pdf or .docx).
    Validates file type and size.
    Parses content with AI / local heuristics and generates a draft profile.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided in upload."
        )

    # Validate file extension
    ext = os.path.splitext(file.filename.lower())[1]
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Only PDF (.pdf) and Microsoft Word (.docx) files are supported."
        )

    # Read content and validate size
    contents = await file.read()
    file_size = len(contents)
    
    if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"The file size ({file_size / (1024*1024):.1f} MB) exceeds the maximum allowed limit of 10 MB."
        )
    
    if file_size < 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file appears to be empty."
        )

    # Store file securely on disk
    user_upload_dir = os.path.join(settings.UPLOAD_DIR, str(current_user.id))
    os.makedirs(user_upload_dir, exist_ok=True)
    
    stored_filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(user_upload_dir, stored_filename)

    with open(file_path, "wb") as f:
        f.write(contents)

    # Deactivate existing active resumes for this user
    db.query(Resume).filter(Resume.user_id == current_user.id, Resume.is_active == True).update({"is_active": False})

    # Save new resume record
    mime_type = file.content_type or ("application/pdf" if ext == ".pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    new_resume = Resume(
        user_id=current_user.id,
        original_filename=file.filename,
        stored_filename=stored_filename,
        file_path=file_path,
        file_size=file_size,
        mime_type=mime_type,
        is_active=True
    )
    db.add(new_resume)
    db.commit()
    db.refresh(new_resume)

    # Parse resume
    parsed_profile: Optional[ParsedResumeProfile] = None
    try:
        parsed_profile = await parse_resume_file(file_path, file.filename)

        # Update or create UserProfile draft
        user_profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
        if not user_profile:
            user_profile = UserProfile(user_id=current_user.id)
            db.add(user_profile)

        user_profile.full_name = parsed_profile.full_name or current_user.full_name
        user_profile.email = parsed_profile.email or current_user.email
        user_profile.phone = parsed_profile.phone
        user_profile.location = parsed_profile.location
        user_profile.headline = parsed_profile.headline
        user_profile.summary = parsed_profile.summary
        user_profile.linkedin_url = parsed_profile.linkedin_url
        user_profile.github_url = parsed_profile.github_url
        user_profile.portfolio_url = parsed_profile.portfolio_url
        user_profile.skills = json.dumps(parsed_profile.skills)
        user_profile.experiences = json.dumps([e.model_dump() for e in parsed_profile.experiences])
        user_profile.education = json.dumps([e.model_dump() for e in parsed_profile.education])
        user_profile.projects = json.dumps([p.model_dump() for p in parsed_profile.projects])
        user_profile.confidence_scores = json.dumps(parsed_profile.confidence_scores)
        user_profile.uncertain_fields = json.dumps(parsed_profile.uncertain_fields)
        user_profile.field_evidence = json.dumps(parsed_profile.field_evidence)
        user_profile.parser_source = parsed_profile.parser_source
        user_profile.raw_extracted_text = parsed_profile.raw_extracted_text
        user_profile.is_confirmed = False

        db.commit()

    except FileExtractionError as e:
        # Clean up database record and stored file on extraction failure
        db.delete(new_resume)
        db.commit()
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # Determine transparent parser analysis status
    analysis_status = "heuristic_complete"
    if parsed_profile:
        if parsed_profile.parser_source in ["openrouter", "ai_openrouter"]:
            if parsed_profile.uncertain_fields or not parsed_profile.full_name or not parsed_profile.skills:
                analysis_status = "partial_uncertain"
            else:
                analysis_status = "ai_complete"
        else:
            if parsed_profile.uncertain_fields or not parsed_profile.full_name or not parsed_profile.skills:
                analysis_status = "partial_uncertain"
            else:
                analysis_status = "heuristic_complete"

    return ResumeUploadResponse(
        message="Resume uploaded and analyzed successfully.",
        resume=ResumeResponse.model_validate(new_resume),
        parsed_profile=parsed_profile,
        analysis_status=analysis_status
    )


@router.get("", response_model=Optional[ResumeResponse])
def get_current_resume(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves metadata of the current active resume for the user."""
    resume = db.query(Resume).filter(
        Resume.user_id == current_user.id,
        Resume.is_active == True
    ).order_by(Resume.uploaded_at.desc()).first()

    return resume


@router.get("/download")
def download_resume(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Allows authenticated user to securely download their active resume."""
    resume = db.query(Resume).filter(
        Resume.user_id == current_user.id,
        Resume.is_active == True
    ).order_by(Resume.uploaded_at.desc()).first()

    if not resume or not os.path.exists(resume.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active resume file found on your account."
        )

    return FileResponse(
        path=resume.file_path,
        filename=resume.original_filename,
        media_type=resume.mime_type
    )


@router.delete("", status_code=status.HTTP_200_OK)
def delete_resume(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes the user's active resume and removes the file from disk."""
    resumes = db.query(Resume).filter(Resume.user_id == current_user.id).all()
    if not resumes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No resume found to delete."
        )

    for resume in resumes:
        if os.path.exists(resume.file_path):
            try:
                os.remove(resume.file_path)
            except OSError:
                pass
        db.delete(resume)

    db.commit()
    return {"message": "Resume successfully deleted."}
