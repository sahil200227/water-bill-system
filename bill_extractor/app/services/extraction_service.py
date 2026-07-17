"""
Main extraction service that orchestrates the full processing pipeline.

Pipeline:
1. Detect file type → PDF or Image
2. If PDF → convert to high-resolution images
3. Preprocess each image with OpenCV
4. Run PaddleOCR on each page
5. Send images + OCR data to Mistral Vision
6. Post-process extracted fields
7. Validate all fields
8. Return structured WaterBillResponse
"""
import time
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image

from app.config.settings import Settings
from app.extraction.regex_extractor import RegexExtractor
from app.ocr.paddle_ocr_engine import PaddleOCREngine
from app.preprocessing.image_preprocessor import ImagePreprocessor
from app.preprocessing.pdf_converter import PDFConverter
from app.schemas.bill_schema import (
    AccountAndBill,
    BalanceDetails,
    CustomerInfo,
    MeterDetail,
    ProviderInfo,
    WaterBillResponse,
)
from app.schemas.ocr_schema import DocumentOCRResult
from app.services.provider_cache import ProviderCache
from app.utils.file_utils import bytes_to_pil_image, detect_file_type, is_pdf
from app.utils.json_merger import merge_extracted_data
from app.utils.logger import get_logger
from app.validation.post_processor import PostProcessor
from app.validation.validator import BillValidator
from app.vision.mistral_client import MistralVisionClient

logger = get_logger(__name__)


class ExtractionService:
    """
    Orchestrates the complete water bill extraction pipeline.

    Coordinates preprocessing, OCR, vision extraction, post-processing,
    and validation to produce a structured WaterBillResponse.
    """

    def __init__(self, settings: Settings):
        """
        Initialize the extraction service with all dependencies.

        Args:
            settings: Application settings.
        """
        self.settings = settings

        # Initialize pipeline components
        self.pdf_converter = PDFConverter(dpi=settings.PDF_DPI)
        self.preprocessor = ImagePreprocessor()
        self.ocr_engine = PaddleOCREngine(
            confidence_threshold=settings.OCR_CONFIDENCE_THRESHOLD
        )
        self.vision_client = MistralVisionClient(
            api_key=settings.MISTRAL_API_KEY,
            model=settings.MISTRAL_MODEL,
        )
        self.post_processor = PostProcessor()
        self.validator = BillValidator()
        self.regex_extractor = RegexExtractor(confidence_threshold=settings.OCR_CONFIDENCE_THRESHOLD)
        self.provider_cache = ProviderCache(settings)

        logger.info("ExtractionService initialized")

    async def extract(
        self, file_content: bytes, filename: str
    ) -> WaterBillResponse:
        """
        Run the full hybrid extraction pipeline on an uploaded document.

        Args:
            file_content: Raw bytes of the uploaded file.
            filename: Original filename for type detection.

        Returns:
            WaterBillResponse with extracted and validated fields.

        Raises:
            ValueError: If file type is unsupported or processing fails.
        """
        logger.info("Starting hybrid extraction pipeline for '%s'", filename)
        pipeline_start_time = time.time()

        # Step 1: Detect file type
        mime_type = detect_file_type(filename, file_content)
        if not mime_type:
            raise ValueError(
                f"Unsupported file type for '{filename}'. "
                "Supported: PDF, PNG, JPG, JPEG"
            )

        logger.info("Detected file type: %s", mime_type)

        # Step 2: Convert to page images
        if is_pdf(mime_type):
            logger.info("Converting PDF to images...")
            original_images = self.pdf_converter.convert(file_content)
        else:
            logger.info("Loading image file...")
            original_images = [bytes_to_pil_image(file_content)]

        logger.info("Total pages to process: %d", len(original_images))

        # Step 3: Preprocess each image
        preprocessed_images: List[Image.Image] = []
        for i, img in enumerate(original_images):
            logger.info("Preprocessing page %d/%d", i + 1, len(original_images))
            try:
                preprocessed = self.preprocessor.preprocess(img)
                preprocessed_images.append(preprocessed)
            except Exception as e:
                logger.warning(
                    "Preprocessing failed for page %d, using original: %s", i + 1, e
                )
                preprocessed_images.append(img)

        # Step 4: Run PaddleOCR on preprocessed images
        ocr_start_time = time.time()
        logger.info("Running PaddleOCR on %d page(s)", len(preprocessed_images))
        ocr_result: DocumentOCRResult = self.ocr_engine.process_document(
            preprocessed_images
        )
        ocr_duration = time.time() - ocr_start_time
        logger.info("PaddleOCR completed in %.2fs", ocr_duration)

        total_blocks = sum(len(p.blocks) for p in ocr_result.pages)
        logger.info("OCR extracted %d text blocks across %d page(s)", total_blocks, len(ocr_result.pages))

        # Step 5: Fast Field Extraction (Regex + Keyword rule-based)
        regex_start_time = time.time()
        raw_extracted, base_confidence = self.regex_extractor.extract(ocr_result)
        regex_duration = time.time() - regex_start_time
        logger.info("Fast rule-based extraction completed in %.2fs", regex_duration)

        # Post-process raw regex extraction results to clean dates/currency
        processed_data = self.post_processor.process(raw_extracted)

        # Step 6 & 7: Cache Lookup & Merge
        provider_name = processed_data.get("provider", {}).get("provider_name")
        account_number = processed_data.get("account_and_bill", {}).get("account_number")

        cache_hit = False
        if provider_name and account_number:
            cached_static = self.provider_cache.get(provider_name, account_number)
            if cached_static:
                cache_hit = True
                logger.info("Cache HIT! Merging cached static fields...")
                processed_data = self._merge_static_cache(processed_data, cached_static)
            else:
                logger.info("Cache MISS for: %s | %s", provider_name, account_number)
        else:
            logger.info("Skipping cache lookup: provider_name or account_number missing")

        # Validate the merged data
        logger.info("Validating extracted fields...")
        validated_data = self.validator.validate_bill(processed_data)

        # Calculate field confidences
        all_blocks = ocr_result.get_all_blocks()
        field_confidences = self.validator.get_field_confidences(processed_data, all_blocks)

        # Step 8: Decide whether Pixtral Vision fallback is needed
        fallback_required, fallback_reason = self._should_fallback(
            validated_data=validated_data,
            field_confidences=field_confidences,
            cache_hit=cache_hit,
        )

        pixtral_duration = 0.0
        if fallback_required:
            logger.info("Pixtral Fallback REQUIRED. Reason: %s", fallback_reason)
            
            # Find missing fields to query only those
            missing_fields = self._get_missing_fields_info(validated_data, field_confidences)
            logger.info("Requesting missing fields from Mistral: %s", missing_fields)

            pixtral_start_time = time.time()
            fallback_extracted = await self.vision_client.extract_fields(
                images=original_images,
                ocr_result=ocr_result,
                missing_fields_info=missing_fields,
            )
            pixtral_duration = time.time() - pixtral_start_time
            logger.info("Mistral Vision responded in %.2fs", pixtral_duration)

            # Post-process fallback results
            processed_fallback = self.post_processor.process(fallback_extracted)

            # Merge fallback results with the existing validated data
            merged_data = merge_extracted_data(processed_data, processed_fallback)

            # Re-validate after merging
            logger.info("Re-validating merged extraction data...")
            validated_data = self.validator.validate_bill(merged_data)
        else:
            logger.info("Pixtral Fallback SKIPPED. All required fields are valid and cached.")

        # Build response
        response = self._build_response(validated_data)

        # Step 9: Update Cache and Transaction Log
        if response.success:
            if not cache_hit:
                # Save static details for new provider
                self._update_provider_cache(validated_data)
            
            # Save complete transaction details
            self._save_to_mongodb(response, filename)

        total_duration = time.time() - pipeline_start_time
        logger.info(
            "Extraction Performance Summary:\n"
            "- Total Processing Time: %.2fs\n"
            "- OCR Duration: %.2fs\n"
            "- Regex/Rules Duration: %.2fs\n"
            "- Cache Status: %s\n"
            "- Pixtral Fallback: %s (Reason: %s, Response Time: %.2fs)",
            total_duration,
            ocr_duration,
            regex_duration,
            "HIT" if cache_hit else "MISS",
            "YES" if fallback_required else "NO",
            fallback_reason if fallback_required else "N/A",
            pixtral_duration,
        )

        return response

    def _save_to_mongodb(self, response: WaterBillResponse, filename: str) -> None:
        """
        Store the extracted bill details in MongoDB.
        """
        try:
            from pymongo import MongoClient
            from datetime import datetime, timezone
            
            logger.info("Connecting to MongoDB for bill storage...")
            client = MongoClient(self.settings.MONGO_URI)
            db = client["bill_extraction"]
            collection = db["bills"]
            
            # Convert response to dictionary format for MongoDB
            document = response.model_dump()
            
            # Deduplication: check if same provider, account number, bill number and bill date already exists
            provider_name = document.get("provider", {}).get("provider_name")
            account_number = document.get("account_and_bill", {}).get("account_number")
            bill_number = document.get("account_and_bill", {}).get("bill_number")
            bill_date = document.get("account_and_bill", {}).get("bill_date")
            
            if provider_name and account_number and bill_number and bill_date:
                query = {
                    "provider.provider_name": provider_name,
                    "account_and_bill.account_number": account_number,
                    "account_and_bill.bill_number": bill_number,
                    "account_and_bill.bill_date": bill_date
                }
                existing = collection.find_one(query)
                if existing:
                    logger.info("Matching bill record already exists in database. Updating document with ID: %s", existing["_id"])
                    document["extracted_at"] = datetime.now(timezone.utc)
                    document["original_filename"] = filename
                    collection.replace_one({"_id": existing["_id"]}, document)
                    client.close()
                    return
            
            # Add metadata
            document["extracted_at"] = datetime.now(timezone.utc)
            document["original_filename"] = filename
            
            insert_result = collection.insert_one(document)
            logger.info("Successfully stored water bill in MongoDB with ID: %s", insert_result.inserted_id)
            client.close()
        except Exception as e:
            logger.error("Failed to store water bill in MongoDB: %s", e, exc_info=True)

    def _merge_static_cache(self, current: Dict[str, Any], cached: Dict[str, Any]) -> Dict[str, Any]:
        """Merge cached static provider and customer metadata into current parsed data."""
        merged = current.copy()
        
        # Merge provider section
        if "provider" not in merged:
            merged["provider"] = {}
        cached_prov = cached.get("provider", {})
        for k, v in cached_prov.items():
            if merged["provider"].get(k) is None and v is not None:
                merged["provider"][k] = v
                
        # Merge customer section
        if "customer" not in merged:
            merged["customer"] = {}
        cached_cust = cached.get("customer", {})
        for k, v in cached_cust.items():
            if merged["customer"].get(k) is None and v is not None:
                merged["customer"][k] = v
                
        # Merge account type
        if "account_and_bill" not in merged:
            merged["account_and_bill"] = {}
        cached_acct = cached.get("account_and_bill", {})
        if merged["account_and_bill"].get("account_type") is None:
            merged["account_and_bill"]["account_type"] = cached_acct.get("account_type")
            
        return merged

    def _should_fallback(
        self,
        validated_data: Dict[str, Any],
        field_confidences: Dict[str, float],
        cache_hit: bool,
    ) -> Tuple[bool, str]:
        """
        Evaluate if we need to call Pixtral Vision fallback.
        """
        # Condition 1: Cache Miss
        if not cache_hit:
            return True, "Provider not found in cache (New Provider)"

        provider = validated_data.get("provider", {})
        customer = validated_data.get("customer", {})
        account = validated_data.get("account_and_bill", {})
        balance = validated_data.get("balance_details", {})
        meter = validated_data.get("meter_details", [])

        # Helper to check validation status and OCR confidence
        def is_invalid(section_name: str, field_name: str, val: Any) -> bool:
            if val is None:
                return True
            if isinstance(val, dict) and val.get("status") == "FAILED_VALIDATION":
                return True
            conf_key = f"{section_name}.{field_name}"
            if field_confidences.get(conf_key, 1.0) < self.settings.OCR_CONFIDENCE_THRESHOLD:
                return True
            return False

        # Condition 2, 3, 4, 7, 8, 9: Validate critical required fields
        if is_invalid("provider", "provider_name", provider.get("provider_name")):
            return True, "Provider name is invalid or missing"
        if is_invalid("account_and_bill", "account_number", account.get("account_number")):
            return True, "Account number is invalid or missing"
        if is_invalid("account_and_bill", "bill_number", account.get("bill_number")):
            return True, "Bill number is invalid or missing"
        if is_invalid("account_and_bill", "bill_date", account.get("bill_date")):
            return True, "Bill date is invalid or missing"
        if is_invalid("account_and_bill", "due_date", account.get("due_date")):
            return True, "Due date is invalid or missing"
        if is_invalid("balance_details", "amount_due", balance.get("amount_due")):
            return True, "Amount due is invalid or missing"

        # Condition 5 & 6: Table extraction failed or incomplete
        if not meter:
            return True, "Table extraction failed: no meter details found"

        for idx, row in enumerate(meter):
            desc = str(row.get("description", "")).upper()
            if "WATER" in desc:
                if is_invalid(f"meter_details[{idx}]", "meter_number", row.get("meter_number")):
                    return True, f"Incomplete meter row: meter_number missing in row {idx}"
                if is_invalid(f"meter_details[{idx}]", "current_reading", row.get("current_reading")):
                    return True, f"Incomplete meter row: current_reading missing in row {idx}"
                if is_invalid(f"meter_details[{idx}]", "charge_amount", row.get("charge_amount")):
                    return True, f"Incomplete meter row: charge_amount missing in row {idx}"

        return False, ""

    def _get_missing_fields_info(self, validated_data: Dict[str, Any], field_confidences: Dict[str, float]) -> List[str]:
        """Identify missing, low-confidence, or invalid fields to request from Pixtral."""
        missing = []
        
        provider = validated_data.get("provider", {})
        customer = validated_data.get("customer", {})
        account = validated_data.get("account_and_bill", {})
        balance = validated_data.get("balance_details", {})
        meter = validated_data.get("meter_details", [])

        def check_field(section_name: str, field_name: str, val: Any):
            if val is None or (isinstance(val, dict) and val.get("status") == "FAILED_VALIDATION"):
                missing.append(f"{section_name}.{field_name}")
            elif field_confidences.get(f"{section_name}.{field_name}", 1.0) < self.settings.OCR_CONFIDENCE_THRESHOLD:
                missing.append(f"{section_name}.{field_name} (low confidence)")

        check_field("provider", "provider_name", provider.get("provider_name"))
        check_field("provider", "provider_address", provider.get("provider_address"))
        check_field("account_and_bill", "account_number", account.get("account_number"))
        check_field("account_and_bill", "bill_number", account.get("bill_number"))
        check_field("account_and_bill", "bill_date", account.get("bill_date"))
        check_field("account_and_bill", "due_date", account.get("due_date"))
        check_field("balance_details", "amount_due", balance.get("amount_due"))

        if not meter:
            missing.append("meter_details (table extraction failed)")
        else:
            for idx, row in enumerate(meter):
                check_field(f"meter_details[{idx}]", "charge_amount", row.get("charge_amount"))

        # Check balance fields
        for k, v in balance.items():
            if v is None:
                missing.append(f"balance_details.{k}")

        return missing

    def _update_provider_cache(self, validated_data: Dict[str, Any]) -> None:
        """Cache static provider and customer metadata for future lookups."""
        try:
            provider_data = self._clean_for_model(validated_data.get("provider", {}))
            customer_data = self._clean_for_model(validated_data.get("customer", {}))
            account_data = self._clean_for_model(validated_data.get("account_and_bill", {}))

            provider_name = provider_data.get("provider_name")
            account_number = account_data.get("account_number")

            if provider_name and account_number:
                static_doc = {
                    "provider": provider_data,
                    "customer": customer_data,
                    "account_and_bill": {
                        "account_type": account_data.get("account_type")
                    }
                }
                self.provider_cache.set(provider_name, account_number, static_doc)
        except Exception as e:
            logger.error("Failed to update provider cache: %s", e)

    def _build_response(self, data: Dict[str, Any]) -> WaterBillResponse:
        """
        Build a WaterBillResponse from validated data.

        Handles missing sections gracefully by providing defaults.

        Args:
            data: Validated extraction data.

        Returns:
            WaterBillResponse instance.
        """
        try:
            provider_data = data.get("provider", {})
            customer_data = data.get("customer", {})
            account_data = data.get("account_and_bill", {})
            meter_data = data.get("meter_details", [])
            balance_data = data.get("balance_details", {})

            # Build meter details list
            meter_details = []
            if isinstance(meter_data, list):
                for item in meter_data:
                    if isinstance(item, dict):
                        meter_details.append(MeterDetail(**self._clean_for_model(item)))

            response = WaterBillResponse(
                success=True,
                document_type="Water Bill",
                provider=ProviderInfo(**self._clean_for_model(provider_data)),
                customer=CustomerInfo(**self._clean_for_model(customer_data)),
                account_and_bill=AccountAndBill(**self._clean_for_model(account_data)),
                meter_details=meter_details,
                balance_details=BalanceDetails(**self._clean_for_model(balance_data)),
            )

            return response

        except Exception as e:
            logger.error("Failed to build response: %s", e)
            # Return a partial response
            return WaterBillResponse(
                success=True,
                document_type="Water Bill",
            )

    @staticmethod
    def _clean_for_model(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean dictionary values for Pydantic model construction.

        Converts validation failure dicts back to None and filters
        out unexpected keys.

        Args:
            data: Dictionary of field values.

        Returns:
            Cleaned dictionary safe for model construction.
        """
        cleaned = {}
        for key, value in data.items():
            if isinstance(value, dict) and "status" in value:
                # Validation failure — use the value field (which is null)
                cleaned[key] = value.get("value")
            else:
                cleaned[key] = value
        return cleaned
