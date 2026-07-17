"""
Water Bill Information Extraction System — FastAPI Application.

A production-ready, provider-independent system that extracts structured
information from water utility bill PDFs and images using PaddleOCR and
the Mistral Vision API.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router as extraction_router
from app.utils.logger import get_logger

logger = get_logger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    application = FastAPI(
        title="Water Bill Information Extraction System",
        description=(
            "AI-powered system that extracts structured information from "
            "water utility bill PDFs and images using PaddleOCR and Mistral Vision API. "
            "Supports multiple providers without templates or fixed layouts."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global exception handler
    @application.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(
            "Unhandled exception on %s %s: %s",
            request.method,
            request.url.path,
            exc,
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Internal server error",
                "detail": str(exc),
            },
        )

    # Health check endpoint
    @application.get(
        "/health",
        tags=["system"],
        summary="Health Check",
        description="Returns the health status of the service.",
    )
    async def health_check():
        return {
            "status": "healthy",
            "service": "Water Bill Extraction System",
            "version": "1.0.0",
        }

    # Register routes
    application.include_router(extraction_router)

    logger.info("Water Bill Extraction System initialized")

    return application


# Create the application instance
app = create_app()
