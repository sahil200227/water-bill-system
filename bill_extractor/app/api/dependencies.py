"""
FastAPI dependency injection for services and shared resources.
"""
from functools import lru_cache

from app.config.settings import Settings, get_settings
from app.services.extraction_service import ExtractionService


@lru_cache()
def get_extraction_service() -> ExtractionService:
    """
    Create and cache the extraction service singleton.

    Returns:
        Configured ExtractionService instance.
    """
    settings = get_settings()
    return ExtractionService(settings=settings)
