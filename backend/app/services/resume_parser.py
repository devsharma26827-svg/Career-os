import logging
from app.schemas.profile import ParsedResumeProfile
from app.services.ai_service import get_ai_service
from app.services.file_extractor import extract_text_from_file

logger = logging.getLogger(__name__)


async def parse_resume_file(file_path: str, filename: str) -> ParsedResumeProfile:
    """
    Extracts text from the resume file (PDF or DOCX) and runs it through
    the AI provider abstraction (OpenRouter with fallback to deterministic local heuristics).
    """
    raw_text, ext = extract_text_from_file(file_path, filename)
    ai_service = get_ai_service()
    parsed_profile = await ai_service.parse_resume_text(raw_text)
    return parsed_profile
