"""
OCR output schemas for structured representation of PaddleOCR results.
"""
from typing import List, Optional

from pydantic import BaseModel, Field


class OCRBlock(BaseModel):
    """A single OCR text detection with metadata."""

    text: str = Field(..., description="Detected text content")
    confidence: float = Field(..., ge=0.0, le=1.0, description="OCR confidence score")
    bbox: List[int] = Field(
        ...,
        min_length=4,
        max_length=4,
        description="Bounding box [x_min, y_min, x_max, y_max]",
    )

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "confidence": round(self.confidence, 4),
            "bbox": self.bbox,
        }


class PageOCRResult(BaseModel):
    """OCR results for a single page."""

    page_number: int = Field(..., ge=1, description="1-indexed page number")
    blocks: List[OCRBlock] = Field(default_factory=list, description="OCR text blocks")
    raw_text: str = Field(default="", description="Concatenated raw text from all blocks")
    avg_confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Average confidence across all blocks"
    )

    def compute_raw_text(self) -> None:
        """Rebuild raw_text from blocks in reading order."""
        self.raw_text = "\n".join(block.text for block in self.blocks)
        if self.blocks:
            self.avg_confidence = sum(b.confidence for b in self.blocks) / len(
                self.blocks
            )


class DocumentOCRResult(BaseModel):
    """OCR results for the entire document (all pages)."""

    pages: List[PageOCRResult] = Field(
        default_factory=list, description="OCR results per page"
    )
    total_pages: int = Field(default=0, description="Total number of pages processed")

    def get_all_blocks(self) -> List[OCRBlock]:
        """Return all OCR blocks across all pages."""
        all_blocks: List[OCRBlock] = []
        for page in self.pages:
            all_blocks.extend(page.blocks)
        return all_blocks

    def get_full_text(self) -> str:
        """Return concatenated text from all pages."""
        return "\n\n--- Page Break ---\n\n".join(
            page.raw_text for page in self.pages if page.raw_text
        )
