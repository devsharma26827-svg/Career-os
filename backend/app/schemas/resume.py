from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.profile import ParsedResumeProfile


class ResumeResponse(BaseModel):
    id: int
    user_id: int
    original_filename: str
    file_size: int
    mime_type: str
    is_active: bool
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResumeUploadResponse(BaseModel):
    message: str
    resume: ResumeResponse
    parsed_profile: Optional[ParsedResumeProfile] = None
    analysis_status: Optional[str] = "heuristic_complete"
