from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseJobSourceAdapter(ABC):
    """
    Abstract base adapter for job data providers.
    Every source implements this interface to provide isolation,
    graceful degradation, and provider-specific error handling.
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Unique slug identifier for the source (e.g. 'arbeitnow', 'remoteok')."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable display name for UI presentation."""
        pass

    @property
    @abstractmethod
    def requires_api_key(self) -> bool:
        """True if the source requires credential configuration."""
        pass

    def is_configured(self) -> bool:
        """Checks if required API keys/tokens are configured."""
        return True

    def get_configuration_help(self) -> Optional[str]:
        """Provides instructions for configuring optional credentials."""
        return None

    @abstractmethod
    async def fetch_jobs(
        self,
        query: Optional[str] = None,
        country: Optional[str] = None,
        states: Optional[List[str]] = None,
        city: Optional[str] = None,
        remote_only: bool = False,
        limit: int = 40
    ) -> List[Dict[str, Any]]:
        """
        Fetches job postings from the source.
        Returns a list of standardized job dictionaries:
        {
            "source_id": str,
            "source_name": str,
            "title": str,
            "company": str,
            "location": str,
            "country": Optional[str],
            "state": Optional[str],
            "city": Optional[str],
            "is_remote": bool,
            "employment_type": str,
            "salary_min": Optional[float],
            "salary_max": Optional[float],
            "salary_currency": Optional[str],
            "salary_text": Optional[str],
            "url": str,
            "description": str,
            "skills_required": List[str],
            "posted_at": Optional[datetime]
        }
        """
        pass
