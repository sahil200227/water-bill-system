"""
Post-processing module for normalizing extracted field values.

Handles date normalization, currency formatting, whitespace trimming,
and type conversion.
"""
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from app.utils.logger import get_logger

logger = get_logger(__name__)

# Common date formats to parse
DATE_FORMATS = [
    "%m/%d/%Y",
    "%m-%d-%Y",
    "%Y-%m-%d",
    "%m/%d/%y",
    "%m-%d-%y",
    "%d/%m/%Y",
    "%B %d, %Y",
    "%b %d, %Y",
    "%B %d %Y",
    "%b %d %Y",
    "%d %B %Y",
    "%d %b %Y",
    "%Y/%m/%d",
]


class PostProcessor:
    """
    Post-processes extracted field values to normalize formats.

    Normalizes:
    - Dates → MM/DD/YYYY
    - Currency → plain decimals (no $, no commas)
    - Blank strings → None
    - Whitespace trimming
    """

    # Fields that should be treated as dates
    DATE_FIELDS = {
        "bill_date",
        "due_date",
        "previous_read_date",
        "current_read_date",
    }

    # Fields that should be treated as currency/decimal
    CURRENCY_FIELDS = {
        "previous_balance",
        "adjustments",
        "total_current_billing",
        "amount_due",
        "less_payments_received",
        "penalties",
        "deposit_applied",
        "charge_amount",
    }

    # Fields that should be numeric
    NUMERIC_FIELDS = {
        "usage",
        "previous_reading",
        "current_reading",
    }

    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run full post-processing on the extracted data dictionary.

        Args:
            data: Raw extracted data from Mistral Vision.

        Returns:
            Post-processed data with normalized values.
        """
        logger.info("Starting post-processing of extracted data")

        result = {}
        for key, value in data.items():
            if isinstance(value, dict):
                result[key] = self._process_section(value)
            elif isinstance(value, list):
                result[key] = [
                    self._process_section(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                result[key] = value

        logger.info("Post-processing complete")
        return result

    def _process_section(self, section: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single section of the extracted data."""
        processed = {}
        for field_name, value in section.items():
            processed[field_name] = self._process_field(field_name, value)
        return processed

    def _process_field(self, field_name: str, value: Any) -> Any:
        """
        Process a single field value based on its name.

        Args:
            field_name: Name of the field.
            value: Raw value to process.

        Returns:
            Processed value.
        """
        # Convert blank/empty to None
        if value is None:
            return None

        if isinstance(value, str):
            value = value.strip()
            if not value or value.lower() in ("", "n/a", "none", "null", "-"):
                return None

        # Apply type-specific normalization
        if field_name in self.DATE_FIELDS:
            return self._normalize_date(value)
        elif field_name in self.CURRENCY_FIELDS:
            return self._normalize_currency(value)
        elif field_name in self.NUMERIC_FIELDS:
            return self._normalize_numeric(value)
        else:
            return self._clean_string(value)

    def _normalize_date(self, value: Any) -> Optional[str]:
        """
        Normalize a date value to MM/DD/YYYY format.

        Args:
            value: Date string in various formats.

        Returns:
            Normalized date string or None.
        """
        if value is None:
            return None

        date_str = str(value).strip()
        if not date_str:
            return None

        for fmt in DATE_FORMATS:
            try:
                parsed = datetime.strptime(date_str, fmt)
                normalized = parsed.strftime("%m/%d/%Y")
                if normalized != date_str:
                    logger.debug("Date normalized: '%s' → '%s'", date_str, normalized)
                return normalized
            except ValueError:
                continue

        logger.warning("Could not normalize date: '%s', keeping original", date_str)
        return date_str

    def _normalize_currency(self, value: Any) -> Optional[str]:
        """
        Normalize a currency value to a plain decimal string.

        Removes currency symbols ($), commas, and whitespace.

        Args:
            value: Currency string.

        Returns:
            Normalized decimal string (e.g., "123.45") or None.
        """
        if value is None:
            return None

        currency_str = str(value).strip()
        if not currency_str:
            return None

        # Remove currency symbols and commas
        cleaned = re.sub(r"[$€£¥,\s]", "", currency_str)

        # Handle negative amounts (parentheses or leading minus)
        is_negative = False
        if cleaned.startswith("(") and cleaned.endswith(")"):
            cleaned = cleaned[1:-1]
            is_negative = True
        elif cleaned.startswith("-"):
            cleaned = cleaned[1:]
            is_negative = True

        # Validate it's a valid number
        try:
            num = float(cleaned)
            if is_negative:
                num = -num
            result = f"{num:.2f}"
            if result != currency_str:
                logger.debug("Currency normalized: '%s' → '%s'", currency_str, result)
            return result
        except ValueError:
            logger.warning(
                "Could not normalize currency: '%s', keeping original", currency_str
            )
            return currency_str

    def _normalize_numeric(self, value: Any) -> Optional[str]:
        """
        Normalize a numeric value (remove commas, trim spaces).

        Args:
            value: Numeric string.

        Returns:
            Cleaned numeric string or None.
        """
        if value is None:
            return None

        num_str = str(value).strip()
        if not num_str:
            return None

        # Remove commas and spaces
        cleaned = re.sub(r"[,\s]", "", num_str)

        try:
            # Check if it's a valid number
            float(cleaned)
            return cleaned
        except ValueError:
            logger.warning(
                "Could not normalize numeric: '%s', keeping original", num_str
            )
            return num_str

    def _clean_string(self, value: Any) -> Optional[str]:
        """
        Clean a string value (trim whitespace, normalize spaces).

        Args:
            value: String value.

        Returns:
            Cleaned string or None.
        """
        if value is None:
            return None

        cleaned = str(value).strip()
        # Strip out utility labels like "CONSUMER FROM" or "CUSTOMER COPY"
        cleaned = re.sub(r"(?i)\b(?:consumer\s+from|customer\s+copy)\b", "", cleaned)
        # Collapse multiple spaces into one
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip() if cleaned.strip() else None
