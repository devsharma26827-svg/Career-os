from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.application import JobApplicationWorkspace
from app.models.job import JobListing
from app.models.resume import Resume
from app.models.user import User


class ApplicationResult(BaseModel):
    status: str  # "submitted", "requires_user_action", "failed", "status_unknown", "cancelled"
    confirmation_id: Optional[str] = None
    confirmation_message: str
    manual_action_url: Optional[str] = None
    manual_action_guide: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class BaseApplicationAdapter(ABC):
    name: str

    @abstractmethod
    def can_handle(self, job: JobListing, workspace: JobApplicationWorkspace) -> bool:
        """
        Determines whether this adapter can execute the application submission
        for the given job and workspace.
        """
        pass

    @abstractmethod
    async def submit(
        self,
        job: JobListing,
        workspace: JobApplicationWorkspace,
        user: User,
        resume: Optional[Resume],
        screening_answers: Dict[str, Any],
        db: Session
    ) -> ApplicationResult:
        """
        Executes the application submission according to the destination requirements.
        Never bypasses platform security, logins, or CAPTCHAs.
        """
        pass
