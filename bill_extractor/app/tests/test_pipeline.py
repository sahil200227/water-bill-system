"""
Tests for the water bill extraction pipeline.

Includes unit tests for preprocessing, OCR schema, validation,
post-processing, and an integration test for the API endpoint.
"""
import json
from datetime import datetime
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

from app.schemas.bill_schema import (
    AccountAndBill,
    BalanceDetails,
    CustomerInfo,
    MeterDetail,
    ProviderInfo,
    WaterBillResponse,
)
from app.schemas.ocr_schema import DocumentOCRResult, OCRBlock, PageOCRResult
from app.schemas.validation_schema import ValidatedField, ValidationStatus
from app.validation.post_processor import PostProcessor
from app.validation.validator import BillValidator


# ======================================================================
# OCR Schema Tests
# ======================================================================

class TestOCRSchema:
    """Tests for OCR data models."""

    def test_ocr_block_creation(self):
        block = OCRBlock(
            text="Customer Name",
            confidence=0.99,
            bbox=[100, 120, 260, 145],
        )
        assert block.text == "Customer Name"
        assert block.confidence == 0.99
        assert block.bbox == [100, 120, 260, 145]

    def test_ocr_block_to_dict(self):
        block = OCRBlock(
            text="John Smith",
            confidence=0.9876,
            bbox=[300, 120, 520, 145],
        )
        d = block.to_dict()
        assert d["text"] == "John Smith"
        assert d["confidence"] == 0.9876
        assert d["bbox"] == [300, 120, 520, 145]

    def test_page_ocr_result_compute_raw_text(self):
        page = PageOCRResult(
            page_number=1,
            blocks=[
                OCRBlock(text="Line 1", confidence=0.95, bbox=[0, 0, 100, 20]),
                OCRBlock(text="Line 2", confidence=0.85, bbox=[0, 30, 100, 50]),
            ],
        )
        page.compute_raw_text()
        assert "Line 1" in page.raw_text
        assert "Line 2" in page.raw_text
        assert page.avg_confidence == pytest.approx(0.9, abs=0.01)

    def test_document_ocr_result_get_full_text(self):
        doc = DocumentOCRResult(
            pages=[
                PageOCRResult(page_number=1, raw_text="Page 1 text"),
                PageOCRResult(page_number=2, raw_text="Page 2 text"),
            ],
            total_pages=2,
        )
        full_text = doc.get_full_text()
        assert "Page 1 text" in full_text
        assert "Page 2 text" in full_text


# ======================================================================
# Bill Schema Tests
# ======================================================================

class TestBillSchema:
    """Tests for bill response data models."""

    def test_water_bill_response_defaults(self):
        response = WaterBillResponse()
        assert response.success is True
        assert response.document_type == "Water Bill"
        assert response.provider.provider_name is None
        assert response.meter_details == []

    def test_water_bill_response_with_data(self):
        response = WaterBillResponse(
            provider=ProviderInfo(
                provider_name="City Water Department",
                provider_address="123 Main St",
            ),
            customer=CustomerInfo(
                customer_name="John Smith",
                customer_id="12345",
                service_address="456 Oak Ave",
            ),
            meter_details=[
                MeterDetail(
                    description="Water",
                    meter_number="98765",
                    usage="1500",
                    charge_amount="25.50",
                    uom="GAL",
                ),
            ],
        )
        assert response.provider.provider_name == "City Water Department"
        assert response.customer.customer_name == "John Smith"
        assert len(response.meter_details) == 1
        assert response.meter_details[0].description == "Water"


# ======================================================================
# Validation Schema Tests
# ======================================================================

class TestValidationSchema:
    """Tests for validation result models."""

    def test_validated_field_valid(self):
        field = ValidatedField.valid("123")
        assert field.value == "123"
        assert field.status == ValidationStatus.VALID

    def test_validated_field_failed(self):
        field = ValidatedField.failed()
        assert field.value is None
        assert field.status == ValidationStatus.FAILED_VALIDATION

    def test_validated_field_not_found(self):
        field = ValidatedField.not_found()
        assert field.value is None
        assert field.status == ValidationStatus.NOT_FOUND


# ======================================================================
# Post-Processing Tests
# ======================================================================

class TestPostProcessor:
    """Tests for the post-processing module."""

    def setup_method(self):
        self.processor = PostProcessor()

    def test_normalize_date_mm_dd_yyyy(self):
        result = self.processor._normalize_date("01/15/2024")
        assert result == "01/15/2024"

    def test_normalize_date_from_iso(self):
        result = self.processor._normalize_date("2024-01-15")
        assert result == "01/15/2024"

    def test_normalize_date_from_text(self):
        result = self.processor._normalize_date("January 15, 2024")
        assert result == "01/15/2024"

    def test_normalize_date_none(self):
        result = self.processor._normalize_date(None)
        assert result is None

    def test_normalize_currency_plain(self):
        result = self.processor._normalize_currency("123.45")
        assert result == "123.45"

    def test_normalize_currency_with_symbol(self):
        result = self.processor._normalize_currency("$1,234.56")
        assert result == "1234.56"

    def test_normalize_currency_negative_parens(self):
        result = self.processor._normalize_currency("($50.00)")
        assert result == "-50.00"

    def test_normalize_currency_none(self):
        result = self.processor._normalize_currency(None)
        assert result is None

    def test_normalize_numeric(self):
        result = self.processor._normalize_numeric("1,500")
        assert result == "1500"

    def test_clean_string(self):
        result = self.processor._clean_string("  Hello   World  ")
        assert result == "Hello World"

    def test_blank_to_none(self):
        result = self.processor._process_field("customer_name", "  ")
        assert result is None

    def test_na_to_none(self):
        result = self.processor._process_field("customer_name", "N/A")
        assert result is None

    def test_full_section_processing(self):
        data = {
            "provider": {
                "provider_name": "  City Water  ",
                "provider_address": "",
            },
            "account_and_bill": {
                "bill_date": "2024-03-15",
                "due_date": "April 15, 2024",
                "bill_number": "INV-001",
                "account_number": "12345",
                "account_type": None,
            },
            "balance_details": {
                "amount_due": "$1,234.56",
                "previous_balance": "500.00",
                "adjustments": None,
                "total_current_billing": "",
                "less_payments_received": "N/A",
                "penalties": "0.00",
                "deposit_applied": None,
            },
        }
        result = self.processor.process(data)
        assert result["provider"]["provider_name"] == "City Water"
        assert result["provider"]["provider_address"] is None
        assert result["account_and_bill"]["bill_date"] == "03/15/2024"
        assert result["account_and_bill"]["due_date"] == "04/15/2024"
        assert result["balance_details"]["amount_due"] == "1234.56"
        assert result["balance_details"]["less_payments_received"] is None


# ======================================================================
# Validator Tests
# ======================================================================

class TestBillValidator:
    """Tests for the field validation module."""

    def setup_method(self):
        self.validator = BillValidator()

    def test_validate_exists_pass(self):
        is_valid, _ = BillValidator._validate_exists("INV-001")
        assert is_valid is True

    def test_validate_exists_fail_empty(self):
        is_valid, _ = BillValidator._validate_exists("")
        assert is_valid is False

    def test_validate_numeric_pass(self):
        is_valid, _ = BillValidator._validate_numeric_string("123456")
        assert is_valid is True

    def test_validate_numeric_fail(self):
        is_valid, _ = BillValidator._validate_numeric_string("ABC123")
        assert is_valid is False

    def test_validate_alphabetic_pass(self):
        is_valid, _ = BillValidator._validate_alphabetic("John Smith")
        assert is_valid is True

    def test_validate_alphabetic_with_special(self):
        is_valid, _ = BillValidator._validate_alphabetic("O'Brien-Johnson Jr.")
        assert is_valid is True

    def test_validate_alphabetic_fail(self):
        is_valid, _ = BillValidator._validate_alphabetic("John123")
        assert is_valid is False

    def test_validate_date_pass(self):
        is_valid, _ = BillValidator._validate_date("01/15/2024")
        assert is_valid is True

    def test_validate_date_fail(self):
        is_valid, _ = BillValidator._validate_date("2024-01-15")
        assert is_valid is False

    def test_validate_decimal_pass(self):
        is_valid, _ = BillValidator._validate_decimal("123.45")
        assert is_valid is True

    def test_validate_decimal_negative(self):
        is_valid, _ = BillValidator._validate_decimal("-50.00")
        assert is_valid is True

    def test_validate_decimal_fail(self):
        is_valid, _ = BillValidator._validate_decimal("$123.45")
        assert is_valid is False

    def test_validate_read_code_pass(self):
        for code in ["A", "F", "E", "Actual", "Final", "Estimated"]:
            is_valid, _ = BillValidator._validate_read_code(code)
            assert is_valid is True, f"Read code '{code}' should be valid"

    def test_validate_read_code_fail(self):
        is_valid, _ = BillValidator._validate_read_code("X")
        assert is_valid is False

    def test_validate_uom_pass(self):
        for uom in ["GAL", "CCF", "TGA", "M3"]:
            is_valid, _ = BillValidator._validate_uom(uom)
            assert is_valid is True, f"UOM '{uom}' should be valid"

    def test_validate_uom_fail(self):
        is_valid, _ = BillValidator._validate_uom("LITERS")
        assert is_valid is False

    def test_validate_bill_section(self):
        data = {
            "account_and_bill": {
                "bill_number": "INV-001",
                "account_number": "123456",
                "bill_date": "01/15/2024",
                "due_date": "02/15/2024",
                "account_type": "Residential",
            },
            "customer": {
                "customer_name": "John Smith",
                "customer_id": None,
                "service_address": "123 Main St",
            },
        }
        result = self.validator.validate_bill(data)
        assert result["account_and_bill"]["bill_number"] == "INV-001"
        assert result["account_and_bill"]["account_number"] == "123456"
        assert result["customer"]["customer_name"] == "John Smith"

    def test_validate_bill_with_failures(self):
        data = {
            "account_and_bill": {
                "bill_number": None,
                "account_number": "ABC",  # Should fail — not numeric
                "bill_date": "invalid",  # Should fail — not a date
                "due_date": None,
                "account_type": None,
            },
        }
        result = self.validator.validate_bill(data)
        assert result["account_and_bill"]["account_number"]["status"] == "FAILED_VALIDATION"
        assert result["account_and_bill"]["bill_date"]["status"] == "FAILED_VALIDATION"


# ======================================================================
# File Utilities Tests
# ======================================================================

class TestFileUtils:
    """Tests for file utility functions."""

    def test_detect_pdf(self):
        from app.utils.file_utils import detect_file_type
        content = b"%PDF-1.4 test content"
        assert detect_file_type("test.pdf", content) == "application/pdf"

    def test_detect_png(self):
        from app.utils.file_utils import detect_file_type
        content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        assert detect_file_type("test.png", content) == "image/png"

    def test_detect_jpeg(self):
        from app.utils.file_utils import detect_file_type
        content = b"\xff\xd8\xff" + b"\x00" * 100
        assert detect_file_type("test.jpg", content) == "image/jpeg"

    def test_detect_unsupported(self):
        from app.utils.file_utils import detect_file_type
        content = b"random binary data"
        assert detect_file_type("test.xyz", content) is None

    def test_validate_file_size_within_limit(self):
        from app.utils.file_utils import validate_file_size
        content = b"x" * (10 * 1024 * 1024)  # 10 MB
        assert validate_file_size(content, max_size_mb=50) is True

    def test_validate_file_size_exceeds_limit(self):
        from app.utils.file_utils import validate_file_size
        content = b"x" * (60 * 1024 * 1024)  # 60 MB
        assert validate_file_size(content, max_size_mb=50) is False

    def test_image_to_base64(self):
        from app.utils.file_utils import image_to_base64
        img = Image.new("RGB", (100, 100), color="white")
        b64 = image_to_base64(img)
        assert isinstance(b64, str)
        assert len(b64) > 0


# ======================================================================
# API Integration Test (with mocked Mistral)
# ======================================================================

class TestAPIEndpoint:
    """Integration tests for the /extract-water-bill endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app)

    def test_health_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_reject_unsupported_file(self, client):
        response = client.post(
            "/extract-water-bill",
            files={"file": ("test.txt", b"Hello world", "text/plain")},
        )
        assert response.status_code == 400

    def test_reject_empty_file(self, client):
        response = client.post(
            "/extract-water-bill",
            files={"file": ("test.pdf", b"", "application/pdf")},
        )
        assert response.status_code == 400


# ======================================================================
# Hybrid Pipeline Component Tests
# ======================================================================

class TestRegexExtractor:
    """Unit tests for Fast RegexExtractor parser."""

    def test_extract_basic(self):
        from app.extraction.regex_extractor import RegexExtractor
        from app.schemas.ocr_schema import DocumentOCRResult, PageOCRResult, OCRBlock
        
        blocks = [
            OCRBlock(text="Town of Little Elm", bbox=[10, 10, 150, 30], confidence=0.99),
            OCRBlock(text="100 W Eldorado Parkway", bbox=[10, 35, 200, 55], confidence=0.99),
            OCRBlock(text="Little Elm, TX 75068", bbox=[10, 60, 200, 80], confidence=0.99),
            OCRBlock(text="Account # 0440000800", bbox=[500, 10, 700, 30], confidence=0.99),
            OCRBlock(text="Bill Date 02/05/2026", bbox=[500, 35, 700, 55], confidence=0.99),
            OCRBlock(text="WATER 7206864 F 01/12/2026 01/30/2026 76 77 1 TGA $29.25", bbox=[10, 200, 800, 220], confidence=0.99),
        ]
        page = PageOCRResult(page_number=1, blocks=blocks, width=1000, height=1000)
        page.compute_raw_text()
        ocr = DocumentOCRResult(pages=[page])
        
        extractor = RegexExtractor()
        data, conf = extractor.extract(ocr)
        
        assert data["provider"]["provider_name"] == "Town of Little Elm"
        assert data["provider"]["provider_zip"] == "75068"
        assert data["account_and_bill"]["account_number"] == "0440000800"
        assert len(data["meter_details"]) == 1
        assert data["meter_details"][0]["description"] == "WATER"
        assert data["meter_details"][0]["meter_number"] == "7206864"
        assert data["meter_details"][0]["charge_amount"] == "29.25"
        assert conf > 0.50


class TestJsonMerger:
    """Unit tests for json_merger utility."""

    def test_merge_missing_and_invalid(self):
        from app.utils.json_merger import merge_extracted_data
        
        original = {
            "provider": {"provider_name": "Little Elm", "provider_address": None},
            "customer": {"customer_name": "Arif", "customer_id": {"value": None, "status": "FAILED_VALIDATION"}},
            "meter_details": []
        }
        fallback = {
            "provider": {"provider_name": "Little Elm", "provider_address": "123 Elm St"},
            "customer": {"customer_name": "Arif", "customer_id": "12345"},
            "meter_details": [{"description": "WATER", "charge_amount": "25.00"}]
        }
        
        merged = merge_extracted_data(original, fallback)
        assert merged["provider"]["provider_address"] == "123 Elm St"
        assert merged["customer"]["customer_id"] == "12345"
        assert len(merged["meter_details"]) == 1


class TestProviderCache:
    """Unit tests for ProviderCache."""

    def test_cache_set_and_get(self, monkeypatch):
        from app.services.provider_cache import ProviderCache
        from app.config.settings import Settings

        # Mock MongoClient
        class MockCollection:
            def __init__(self):
                self.store = {}
            def create_index(self, *args, **kwargs):
                pass
            def find_one(self, query):
                key = (query["provider_name_key"], query["account_number_key"])
                return self.store.get(key)
            def replace_one(self, query, doc, upsert=True):
                key = (query["provider_name_key"], query["account_number_key"])
                self.store[key] = doc

        mock_col = MockCollection()

        # Patch _get_collection to return our mock
        monkeypatch.setattr(ProviderCache, "_get_collection", lambda self: mock_col)

        settings = Settings(MONGO_URI="mongodb://localhost:27017")
        cache = ProviderCache(settings)

        static_data = {
            "provider": {"provider_name": "Little Elm", "provider_address": "100 W Eldorado"},
            "customer": {"customer_name": "Arif", "customer_id": "12345"}
        }

        # Set value
        res = cache.set("Little Elm", "0440000800", static_data)
        assert res is True

        # Get value
        val = cache.get("Little Elm", "0440000800")
        assert val is not None
        assert val["provider"]["provider_name"] == "Little Elm"
        assert val["customer"]["customer_name"] == "Arif"


