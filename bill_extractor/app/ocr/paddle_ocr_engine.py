"""
PaddleOCR engine for text extraction from document images.

Extracts text, confidence scores, bounding boxes, and maintains reading order.
"""
from typing import List, Optional

import numpy as np
from PIL import Image

from app.schemas.ocr_schema import DocumentOCRResult, OCRBlock, PageOCRResult
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PaddleOCREngine:
    """
    PaddleOCR wrapper for document text extraction.

    Initializes the PaddleOCR model lazily on first use and provides
    methods to extract structured OCR data from images.
    """

    def __init__(self, confidence_threshold: float = 0.5):
        """
        Initialize the OCR engine.

        Args:
            confidence_threshold: Minimum confidence score to include a detection.
        """
        self.confidence_threshold = confidence_threshold
        self._ocr = None

    def _get_ocr(self):
        """Lazy-initialize PaddleOCR model."""
        if self._ocr is None:
            logger.info("Initializing PaddleOCR engine...")
            import os
            os.environ["FLAGS_allocator_strategy"] = "naive_best_fit"
            import paddle
            try:
                paddle.set_device('cpu')
                logger.info("Forced Paddle device to CPU")
            except Exception as pe:
                logger.warning("Failed to set Paddle device to CPU: %s", pe)
            
            from paddleocr import PaddleOCR

            self._ocr = PaddleOCR(
                use_angle_cls=True,
                lang="en",
                show_log=False,
                use_gpu=False,
            )
            logger.info("PaddleOCR engine initialized")
        return self._ocr

    def process_single_page(
        self, image: Image.Image, page_number: int = 1
    ) -> PageOCRResult:
        """
        Run OCR on a single page image.

        Args:
            image: PIL Image to process.
            page_number: 1-indexed page number.

        Returns:
            PageOCRResult with extracted text blocks.
        """
        logger.info(
            "Running PaddleOCR on page %d (size: %dx%d)",
            page_number,
            image.width,
            image.height,
        )

        ocr = self._get_ocr()
        img_array = np.array(image)

        try:
            results = ocr.ocr(img_array, cls=True)
        except Exception as e:
            logger.error("PaddleOCR failed on page %d: %s", page_number, e)
            return PageOCRResult(page_number=page_number)

        blocks: List[OCRBlock] = []

        if results and results[0]:
            for detection in results[0]:
                try:
                    bbox_points = detection[0]  # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
                    text = detection[1][0]
                    confidence = float(detection[1][1])

                    # Convert polygon to bounding box [x_min, y_min, x_max, y_max]
                    xs = [p[0] for p in bbox_points]
                    ys = [p[1] for p in bbox_points]
                    bbox = [
                        int(min(xs)),
                        int(min(ys)),
                        int(max(xs)),
                        int(max(ys)),
                    ]

                    if confidence < self.confidence_threshold:
                        logger.debug(
                            "Low confidence (%.3f) for text: '%s' — including anyway",
                            confidence,
                            text[:50],
                        )

                    block = OCRBlock(text=text, confidence=confidence, bbox=bbox)
                    blocks.append(block)

                except (IndexError, ValueError, TypeError) as e:
                    logger.warning(
                        "Skipping malformed OCR detection on page %d: %s",
                        page_number,
                        e,
                    )
                    continue

        # Sort blocks by reading order: top-to-bottom, then left-to-right
        blocks = self._sort_reading_order(blocks)

        page_result = PageOCRResult(page_number=page_number, blocks=blocks)
        page_result.compute_raw_text()

        logger.info(
            "Page %d: %d text blocks extracted (avg confidence: %.3f)",
            page_number,
            len(blocks),
            page_result.avg_confidence,
        )

        return page_result

    def process_document(self, images: List[Image.Image]) -> DocumentOCRResult:
        """
        Run OCR on all pages of a document.

        Args:
            images: List of PIL Images (one per page).

        Returns:
            DocumentOCRResult with all pages.
        """
        logger.info("Processing document with %d page(s)", len(images))

        pages: List[PageOCRResult] = []
        for i, image in enumerate(images):
            page_result = self.process_single_page(image, page_number=i + 1)
            pages.append(page_result)

        result = DocumentOCRResult(pages=pages, total_pages=len(pages))

        total_blocks = sum(len(p.blocks) for p in pages)
        logger.info(
            "Document OCR complete: %d pages, %d total text blocks",
            len(pages),
            total_blocks,
        )

        return result

    @staticmethod
    def _sort_reading_order(blocks: List[OCRBlock]) -> List[OCRBlock]:
        """
        Sort OCR blocks in reading order (top-to-bottom, left-to-right).

        Groups blocks into rows based on vertical overlap, then sorts
        each row left-to-right.

        Args:
            blocks: List of OCR blocks.

        Returns:
            Sorted list of OCR blocks.
        """
        if not blocks:
            return blocks

        # Sort primarily by y_min, secondarily by x_min
        sorted_blocks = sorted(blocks, key=lambda b: (b.bbox[1], b.bbox[0]))

        # Group into rows based on vertical overlap
        rows: List[List[OCRBlock]] = []
        current_row: List[OCRBlock] = [sorted_blocks[0]]

        for block in sorted_blocks[1:]:
            prev_y_center = (current_row[-1].bbox[1] + current_row[-1].bbox[3]) / 2
            curr_y_center = (block.bbox[1] + block.bbox[3]) / 2
            row_height = current_row[-1].bbox[3] - current_row[-1].bbox[1]

            # If the block is within half the row height, it's in the same row
            if abs(curr_y_center - prev_y_center) < max(row_height * 0.5, 10):
                current_row.append(block)
            else:
                rows.append(current_row)
                current_row = [block]

        rows.append(current_row)

        # Sort each row left-to-right and flatten
        result: List[OCRBlock] = []
        for row in rows:
            row.sort(key=lambda b: b.bbox[0])
            result.extend(row)

        return result
