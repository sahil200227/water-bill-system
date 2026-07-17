"""
Water Bill Extractor — Application Entry Point
"""
import os
os.environ["FLAGS_allocator_strategy"] = "naive_best_fit"
import uvicorn
from app.config.settings import get_settings


def main():
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()
