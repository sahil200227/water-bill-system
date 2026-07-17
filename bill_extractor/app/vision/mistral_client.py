"""
Mistral Vision API client for water bill field extraction.

Sends document images and structured OCR data to the Mistral Vision model
for intelligent field extraction with visual reasoning.
"""
import json
import time
from typing import Any, Dict, List, Optional

from PIL import Image
from mistralai.client import Mistral

from app.schemas.ocr_schema import DocumentOCRResult
from app.utils.file_utils import image_to_base64
from app.utils.logger import get_logger
from app.vision.prompts import SYSTEM_PROMPT, build_user_prompt

logger = get_logger(__name__)


class MistralVisionClient:
    """
    Async client for the Mistral Vision API.

    Sends both the original document image and structured OCR output
    to the vision model for accurate field extraction.
    """

    def __init__(self, api_key: str, model: str = "pixtral-large-latest"):
        """
        Initialize the Mistral Vision client.

        Args:
            api_key: Mistral API key.
            model: Model identifier (must support vision).
        """
        if not api_key:
            raise ValueError("MISTRAL_API_KEY is required but not set")

        self.client = Mistral(api_key=api_key)
        self.model = model
        self.max_retries = 3
        self.retry_delay = 2.0

        logger.info("Mistral Vision client initialized (model: %s)", model)

    async def extract_fields(
        self,
        images: List[Image.Image],
        ocr_result: DocumentOCRResult,
        missing_fields_info: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Extract structured fields from document images using Mistral Vision.

        Sends both the original images and OCR text to the vision model.
        The model uses visual reasoning to identify and extract fields.

        Args:
            images: List of original document page images.
            ocr_result: Structured OCR results from PaddleOCR.
            missing_fields_info: Optional list of missing/invalid field names to target.

        Returns:
            Extracted fields as a dictionary matching the bill schema.

        Raises:
            RuntimeError: If extraction fails after all retries.
        """
        logger.info(
            "Sending %d image(s) and OCR data to Mistral Vision (%s)",
            len(images),
            self.model,
        )

        # Prepare OCR data for prompt
        all_ocr_blocks = []
        for page in ocr_result.pages:
            for block in page.blocks:
                all_ocr_blocks.append(block.to_dict())

        user_prompt = build_user_prompt(all_ocr_blocks)

        if missing_fields_info:
            logger.info("Customizing prompt for missing fields fallback: %s", missing_fields_info)
            fallback_instruction = (
                f"\n\n### FALLBACK INSTRUCTION:\n"
                f"You are running as a fallback extractor because some fields could not be confidently "
                f"parsed by our rules. Please focus on the document image and extract ONLY the following "
                f"fields/sections, leaving all other fields in the output JSON structure as null:\n"
                f"{', '.join(missing_fields_info)}"
            )
            user_prompt += fallback_instruction

        # Build message content with images and text
        content: List[Dict[str, Any]] = []

        # Add each page image
        for i, img in enumerate(images):
            b64 = image_to_base64(img, format="JPEG")
            content.append(
                {
                    "type": "image_url",
                    "image_url": f"data:image/jpeg;base64,{b64}",
                }
            )
            logger.debug("Added page %d image to request", i + 1)

        # Add the text prompt
        content.append({"type": "text", "text": user_prompt})

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ]

        # Retry loop with exponential backoff
        last_error: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info("Mistral Vision API call (attempt %d/%d)", attempt, self.max_retries)
                start_time = time.time()

                response = await self.client.chat.complete_async(
                    model=self.model,
                    messages=messages,
                    temperature=0.0,
                    max_tokens=4096,
                )

                elapsed = time.time() - start_time
                logger.info("Mistral Vision responded in %.2fs", elapsed)

                # Extract response text
                raw_text = response.choices[0].message.content.strip()
                logger.debug("Raw response length: %d chars", len(raw_text))

                # Parse JSON from response
                extracted = self._parse_response(raw_text)

                if extracted:
                    logger.info("Successfully extracted fields from Mistral Vision response")
                    return extracted

                logger.warning("Empty or invalid response on attempt %d", attempt)

            except json.JSONDecodeError as e:
                last_error = e
                logger.warning(
                    "JSON parse error on attempt %d: %s", attempt, e
                )
            except Exception as e:
                last_error = e
                logger.error(
                    "Mistral Vision API error on attempt %d: %s", attempt, e
                )

            if attempt < self.max_retries:
                delay = self.retry_delay * (2 ** (attempt - 1))
                logger.info("Retrying in %.1fs...", delay)
                time.sleep(delay)

        error_msg = f"Mistral Vision extraction failed after {self.max_retries} attempts"
        if last_error:
            error_msg += f": {last_error}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    def _parse_response(self, raw_text: str) -> Optional[Dict[str, Any]]:
        """
        Parse the JSON response from Mistral Vision.

        Handles cases where the response may be wrapped in markdown code fences.

        Args:
            raw_text: Raw response text from the API.

        Returns:
            Parsed dictionary, or None if parsing fails.
        """
        text = raw_text.strip()

        # Remove markdown code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first line (```json or ```)
            lines = lines[1:]
            # Remove last line (```)
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        try:
            parsed = json.loads(text)

            if not isinstance(parsed, dict):
                logger.warning("Mistral response is not a JSON object")
                return None

            return parsed

        except json.JSONDecodeError as e:
            logger.error("Failed to parse Mistral response as JSON: %s", e)
            logger.debug("Response text (first 500 chars): %s", text[:500])
            return None
