"""
API routes for the water bill extraction service.
"""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.dependencies import get_extraction_service
from app.config.settings import get_settings
from app.schemas.bill_schema import ExtractionErrorResponse, WaterBillResponse
from app.services.extraction_service import ExtractionService
from app.utils.file_utils import ALLOWED_EXTENSIONS, validate_file_size
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["extraction"])

# Allowed content types for upload
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
}


@router.post(
    "/extract-water-bill",
    response_model=WaterBillResponse,
    responses={
        400: {"model": ExtractionErrorResponse, "description": "Invalid input"},
        422: {"model": ExtractionErrorResponse, "description": "Validation error"},
        500: {"model": ExtractionErrorResponse, "description": "Extraction failed"},
    },
    summary="Extract Water Bill Information",
    description=(
        "Upload a water utility bill (PDF, PNG, JPG, or JPEG) and receive "
        "structured JSON with extracted provider, customer, account, meter, "
        "and balance information."
    ),
)
async def extract_water_bill(
    file: UploadFile = File(
        ...,
        description="Water bill document (PDF, PNG, JPG, JPEG)",
    ),
    service: ExtractionService = Depends(get_extraction_service),
) -> WaterBillResponse:
    """
    Extract structured information from a water utility bill.

    Accepts PDF, PNG, JPG, or JPEG files. Processes the document through
    OCR and vision AI to extract all relevant fields into a standardized
    JSON format.
    """
    settings = get_settings()

    # Validate filename exists
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required",
        )

    logger.info("Received file: '%s' (content_type: %s)", file.filename, file.content_type)

    # Validate file extension
    filename = file.filename.lower()
    ext = "." + filename.rsplit(".", 1)[-1] if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type '{ext}'. "
                f"Supported: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            ),
        )

    # Read file content
    try:
        content = await file.read()
    except Exception as e:
        logger.error("Failed to read uploaded file: %s", e)
        raise HTTPException(status_code=400, detail="Failed to read uploaded file")

    # Validate file is not empty
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # Validate file size
    if not validate_file_size(content, settings.MAX_FILE_SIZE_MB):
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds maximum size of {settings.MAX_FILE_SIZE_MB}MB",
        )

    # Run extraction pipeline
    try:
        result = await service.extract(
            file_content=content,
            filename=file.filename,
        )
        logger.info("Extraction successful for '%s'", file.filename)
        return result

    except ValueError as e:
        logger.warning("Extraction validation error for '%s': %s", file.filename, e)
        raise HTTPException(status_code=400, detail=str(e))

    except RuntimeError as e:
        logger.error("Extraction runtime error for '%s': %s", file.filename, e)
        raise HTTPException(
            status_code=500,
            detail=f"Extraction failed: {e}",
        )

    except Exception as e:
        logger.error(
            "Unexpected error during extraction for '%s': %s",
            file.filename,
            e,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during extraction",
        )
