"""
Application settings loaded from environment variables.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration via environment variables."""

    # Mistral Vision API
    MISTRAL_API_KEY: str = ""
    MISTRAL_MODEL: str = "pixtral-12b-2409"

    # MongoDB
    MONGO_URI: str = "mongodb+srv://aktharsahil6:Sahil2002@cluster0.vstf8.mongodb.net/"

    # Application
    LOG_LEVEL: str = "INFO"
    MAX_FILE_SIZE_MB: int = 50
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # OCR
    OCR_CONFIDENCE_THRESHOLD: float = 0.5

    # PDF Conversion
    PDF_DPI: int = 300

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
