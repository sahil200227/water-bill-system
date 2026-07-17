"""
Field-level validator for extracted water bill data.

Validates each field against business rules using regex patterns
and allowed-value constraints. Returns validated fields with status.
"""
import re
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.schemas.validation_schema import ValidatedField, ValidationStatus
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Allowed values for constrained fields
ALLOWED_READ_CODES = {"A", "F", "E", "ACTUAL", "FINAL", "ESTIMATED"}
ALLOWED_UOM = {"GAL", "CCF", "TGA", "M3"}


class BillValidator:
    """
    Validates extracted water bill fields against business rules.

    Each field type has its own validation rule:
    - bill_number: Must exist (not null/empty)
    - account_number: Numeric
    - customer_name: Alphabetic (letters, spaces, hyphens, apostrophes)
    - Dates: Valid date in MM/DD/YYYY format
    - Amounts: Valid decimal number
    - usage: Numeric
    - meter_number: Numeric
    - read_code: Must be one of the allowed values
    - uom: Must be one of the allowed values

    On validation failure, returns { "value": null, "status": "FAILED_VALIDATION" }.
    """

    def validate_bill(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the entire extracted bill data.

        Args:
            data: Post-processed bill data dictionary.

        Returns:
            The same data with invalid fields replaced by
            {"value": null, "status": "FAILED_VALIDATION"}.
        """
        logger.info("Starting field validation")
        validated = {}
        failures = 0

        for section_key, section_value in data.items():
            if isinstance(section_value, dict):
                validated[section_key] = self._validate_section(
                    section_key, section_value
                )
            elif isinstance(section_value, list):
                validated_list = []
                for item in section_value:
                    if isinstance(item, dict):
                        validated_list.append(
                            self._validate_section(section_key, item, is_list_item=True)
                        )
                    else:
                        validated_list.append(item)
                validated[section_key] = validated_list
            else:
                validated[section_key] = section_value

        # Count failures
        failures = self._count_failures(validated)
        total_fields = self._count_fields(validated)
        logger.info(
            "Validation complete: %d/%d fields valid",
            total_fields - failures,
            total_fields,
        )

        return validated

    def _validate_section(
        self,
        section_key: str,
        section: Dict[str, Any],
        is_list_item: bool = False,
    ) -> Dict[str, Any]:
        """Validate all fields in a section."""
        validated = {}
        for field_name, value in section.items():
            rule = self._get_validation_rule(section_key, field_name)
            if rule and value is not None:
                is_valid, reason = rule(value)
                if not is_valid:
                    logger.warning(
                        "Validation failed for %s.%s: value='%s', reason='%s'",
                        section_key,
                        field_name,
                        value,
                        reason,
                    )
                    validated[field_name] = {
                        "value": None,
                        "status": "FAILED_VALIDATION",
                    }
                else:
                    validated[field_name] = value
            else:
                validated[field_name] = value

        return validated

    def _get_validation_rule(
        self, section_key: str, field_name: str
    ) -> Optional[Callable[[Any], Tuple[bool, str]]]:
        """
        Get the validation rule function for a given field.

        Args:
            section_key: The section (e.g., "customer", "account_and_bill").
            field_name: The field name within the section.

        Returns:
            Validation function that returns (is_valid, reason), or None.
        """
        rules: Dict[str, Callable[[Any], Tuple[bool, str]]] = {
            # Account and Bill
            "bill_number": self._validate_exists,
            "account_number": self._validate_numeric_string,
            "bill_date": self._validate_date,
            "due_date": self._validate_date,

            # Customer
            "customer_name": self._validate_alphabetic,

            # Meter details
            "meter_number": self._validate_numeric_string,
            "read_code": self._validate_read_code,
            "previous_read_date": self._validate_date,
            "current_read_date": self._validate_date,
            "previous_reading": self._validate_numeric_value,
            "current_reading": self._validate_numeric_value,
            "usage": self._validate_numeric_value,
            "charge_amount": self._validate_decimal,
            "uom": self._validate_uom,

            # Balance details
            "previous_balance": self._validate_decimal,
            "adjustments": self._validate_decimal,
            "total_current_billing": self._validate_decimal,
            "amount_due": self._validate_decimal,
            "less_payments_received": self._validate_decimal,
            "penalties": self._validate_decimal,
            "deposit_applied": self._validate_decimal,
        }

        return rules.get(field_name)

    @staticmethod
    def _validate_exists(value: Any) -> Tuple[bool, str]:
        """Validate that a value exists and is not empty."""
        if value is None or (isinstance(value, str) and not value.strip()):
            return False, "Field must not be empty"
        return True, ""

    @staticmethod
    def _validate_numeric_string(value: Any) -> Tuple[bool, str]:
        """Validate that a value contains only numeric characters."""
        cleaned = re.sub(r"[\s\-]", "", str(value))
        if re.match(r"^\d+$", cleaned):
            return True, ""
        return False, f"Expected numeric value, got '{value}'"

    @staticmethod
    def _validate_alphabetic(value: Any) -> Tuple[bool, str]:
        """Validate that a value contains only alphabetic characters, spaces, hyphens, apostrophes, and periods."""
        if re.match(r"^[A-Za-z\s\'\-\.&,]+$", str(value)):
            return True, ""
        return False, f"Expected alphabetic value, got '{value}'"

    @staticmethod
    def _validate_date(value: Any) -> Tuple[bool, str]:
        """Validate that a value is a valid date in MM/DD/YYYY format."""
        date_str = str(value).strip()
        try:
            datetime.strptime(date_str, "%m/%d/%Y")
            return True, ""
        except ValueError:
            return False, f"Expected date in MM/DD/YYYY format, got '{value}'"

    @staticmethod
    def _validate_decimal(value: Any) -> Tuple[bool, str]:
        """Validate that a value is a valid decimal number."""
        cleaned = str(value).strip()
        if re.match(r"^-?\d+(\.\d+)?$", cleaned):
            return True, ""
        return False, f"Expected decimal value, got '{value}'"

    @staticmethod
    def _validate_numeric_value(value: Any) -> Tuple[bool, str]:
        """Validate that a value is numeric (integer or decimal)."""
        cleaned = re.sub(r"[,\s]", "", str(value))
        if re.match(r"^-?\d+(\.\d+)?$", cleaned):
            return True, ""
        return False, f"Expected numeric value, got '{value}'"

    @staticmethod
    def _validate_read_code(value: Any) -> Tuple[bool, str]:
        """Validate read code against allowed values."""
        if str(value).strip().upper() in ALLOWED_READ_CODES:
            return True, ""
        return False, f"Invalid read code '{value}'. Allowed: {ALLOWED_READ_CODES}"

    @staticmethod
    def _validate_uom(value: Any) -> Tuple[bool, str]:
        """Validate unit of measure against allowed values."""
        if str(value).strip().upper() in ALLOWED_UOM:
            return True, ""
        return False, f"Invalid UOM '{value}'. Allowed: {ALLOWED_UOM}"

    @staticmethod
    def _count_failures(data: Dict[str, Any]) -> int:
        """Count total validation failures in the data."""
        count = 0
        for value in data.values():
            if isinstance(value, dict):
                for v in value.values():
                    if isinstance(v, dict) and v.get("status") == "FAILED_VALIDATION":
                        count += 1
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        for v in item.values():
                            if (
                                isinstance(v, dict)
                                and v.get("status") == "FAILED_VALIDATION"
                            ):
                                count += 1
        return count

    @staticmethod
    def _count_fields(data: Dict[str, Any]) -> int:
        """Count total validatable fields in the data."""
        count = 0
        for value in data.values():
            if isinstance(value, dict):
                count += len(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        count += len(item)
        return count

    def get_field_confidences(self, data: Dict[str, Any], blocks: List[Any]) -> Dict[str, float]:
        """
        Calculate OCR confidence for each extracted field based on matching text blocks.
        """
        confidences = {}
        # Calculate general average confidence as fallback
        fallback_conf = sum(getattr(b, "confidence", 1.0) for b in blocks) / len(blocks) if blocks else 1.0

        for section_name, section in data.items():
            if isinstance(section, dict):
                for field_name, value in section.items():
                    if value is None:
                        confidences[f"{section_name}.{field_name}"] = 0.0
                        continue
                    val_str = str(value).lower()
                    block_confs = []
                    for b in blocks:
                        b_text = getattr(b, "text", "")
                        b_conf = getattr(b, "confidence", 1.0)
                        if b_text and (b_text.lower() in val_str or val_str in b_text.lower()):
                            block_confs.append(b_conf)
                    confidences[f"{section_name}.{field_name}"] = sum(block_confs) / len(block_confs) if block_confs else fallback_conf
            elif isinstance(section, list) and section_name == "meter_details":
                for idx, row in enumerate(section):
                    if isinstance(row, dict):
                        for field_name, value in row.items():
                            if value is None:
                                confidences[f"meter_details[{idx}].{field_name}"] = 0.0
                                continue
                            val_str = str(value).lower()
                            block_confs = []
                            for b in blocks:
                                b_text = getattr(b, "text", "")
                                b_conf = getattr(b, "confidence", 1.0)
                                if b_text and (b_text.lower() in val_str or val_str in b_text.lower()):
                                    block_confs.append(b_conf)
                            confidences[f"meter_details[{idx}].{field_name}"] = sum(block_confs) / len(block_confs) if block_confs else fallback_conf

        return confidences
