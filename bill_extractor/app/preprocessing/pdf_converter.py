"""
PDF to image conversion using pdf2image (poppler).
"""
from typing import List

from PIL import Image
from pdf2image import convert_from_bytes
from pdf2image.exceptions import PDFPageCountError, PDFSyntaxError

from app.utils.logger import get_logger

logger = get_logger(__name__)


class PDFConverter:
    """Converts PDF documents to high-resolution page images."""

    def __init__(self, dpi: int = 300):
        """
        Initialize PDF converter.

        Args:
            dpi: Resolution for PDF rendering (default 300).
        """
        self.dpi = dpi

    def convert(self, pdf_bytes: bytes) -> List[Image.Image]:
        """
        Convert a PDF to a list of PIL Images (one per page).

        Args:
            pdf_bytes: Raw PDF file bytes.

        Returns:
            List of PIL Images in RGB mode.

        Raises:
            ValueError: If the PDF is corrupted or empty.
        """
        try:
            logger.info("Converting PDF to images at %d DPI", self.dpi)

            images = convert_from_bytes(
                pdf_bytes,
                dpi=self.dpi,
                fmt="png",
                thread_count=2,
            )

            if not images:
                raise ValueError("PDF conversion produced no images")

            # Ensure RGB mode
            rgb_images = []
            for i, img in enumerate(images):
                rgb_img = img.convert("RGB")
                rgb_images.append(rgb_img)
                logger.debug(
                    "Page %d converted: %dx%d", i + 1, rgb_img.width, rgb_img.height
                )

            logger.info("Successfully converted %d page(s) from PDF", len(rgb_images))
            return rgb_images

        except PDFPageCountError as e:
            logger.error("Failed to determine PDF page count: %s", e)
            raise ValueError(f"Corrupted or invalid PDF: {e}") from e
        except PDFSyntaxError as e:
            logger.error("PDF syntax error: %s", e)
            raise ValueError(f"Invalid PDF syntax: {e}") from e
        except Exception as e:
            logger.error("PDF conversion failed: %s", e)
            raise ValueError(f"Failed to convert PDF: {e}") from e
