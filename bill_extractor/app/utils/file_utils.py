"""
File utility functions for type detection, temporary file management, and image encoding.
"""
import base64
import io
import tempfile
from pathlib import Path
from typing import Optional

from PIL import Image

from app.utils.logger import get_logger

logger = get_logger(__name__)

# Supported MIME types and their extensions
SUPPORTED_TYPES = {
    "application/pdf": [".pdf"],
    "image/png": [".png"],
    "image/jpeg": [".jpg", ".jpeg"],
}

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}


def detect_file_type(filename: str, content: bytes) -> Optional[str]:
    """
    Detect file type using magic bytes and extension fallback.

    Args:
        filename: Original filename.
        content: Raw file bytes.

    Returns:
        Detected MIME type string, or None if unsupported.
    """
    # Check magic bytes first
    if content[:4] == b"%PDF":
        return "application/pdf"
    if content[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if content[:2] == b"\xff\xd8":
        return "image/jpeg"

    # Fallback to extension
    ext = Path(filename).suffix.lower()
    for mime, extensions in SUPPORTED_TYPES.items():
        if ext in extensions:
            logger.warning(
                "Magic bytes detection failed for '%s', falling back to extension: %s",
                filename,
                mime,
            )
            return mime

    return None


def is_pdf(mime_type: str) -> bool:
    """Check if MIME type is PDF."""
    return mime_type == "application/pdf"


def is_image(mime_type: str) -> bool:
    """Check if MIME type is an image."""
    return mime_type in ("image/png", "image/jpeg")


def validate_file_size(content: bytes, max_size_mb: int) -> bool:
    """
    Validate that file size is within the allowed limit.

    Args:
        content: Raw file bytes.
        max_size_mb: Maximum allowed size in megabytes.

    Returns:
        True if within limit.
    """
    max_bytes = max_size_mb * 1024 * 1024
    return len(content) <= max_bytes


def image_to_base64(image: Image.Image, format: str = "JPEG", max_dim: int = 1600, quality: int = 85) -> str:
    """
    Convert a PIL Image to a base64-encoded string, resizing it if necessary
    to reduce payload size.

    Args:
        image: PIL Image object.
        format: Output format (PNG, JPEG).
        max_dim: Maximum dimension (width or height) to resize to.
        quality: JPEG compression quality (1-100).

    Returns:
        Base64-encoded string of the image.
    """
    # Resize if image exceeds max dimension to save bandwidth/prevent API timeouts
    w, h = image.size
    if max(w, h) > max_dim:
        scale = max_dim / max(w, h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        # Use Image.Resampling.LANCZOS if available, fallback to Image.LANCZOS
        try:
            resample_filter = Image.Resampling.LANCZOS
        except AttributeError:
            resample_filter = getattr(Image, "LANCZOS", Image.BICUBIC)
        
        image = image.resize((new_w, new_h), resample=resample_filter)
        logger.debug("Resized image from %dx%d to %dx%d for base64 encoding", w, h, new_w, new_h)

    # Ensure correct mode for JPEG
    if format.upper() == "JPEG" and image.mode != "RGB":
        image = image.convert("RGB")

    buffer = io.BytesIO()
    if format.upper() == "JPEG":
        image.save(buffer, format=format, quality=quality)
    else:
        image.save(buffer, format=format)
        
    buffer.seek(0)
    encoded = base64.b64encode(buffer.read()).decode("utf-8")
    logger.debug("Encoded image to base64 (%s format, %d chars)", format, len(encoded))
    return encoded


def bytes_to_pil_image(content: bytes) -> Image.Image:
    """
    Convert raw bytes to a PIL Image.

    Args:
        content: Raw image bytes.

    Returns:
        PIL Image object.
    """
    return Image.open(io.BytesIO(content)).convert("RGB")


def save_temp_file(content: bytes, suffix: str = ".tmp") -> str:
    """
    Save bytes to a temporary file and return the path.

    Args:
        content: Raw bytes to save.
        suffix: File extension for the temp file.

    Returns:
        Path to the temporary file.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        logger.debug("Saved temporary file: %s", tmp.name)
        return tmp.name
