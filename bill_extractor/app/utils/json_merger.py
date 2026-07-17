"""
JSON Merger utility for integrating fallback vision results with rule-based extractions.
"""
from typing import Any, Dict, List

from app.utils.logger import get_logger

logger = get_logger(__name__)


def is_invalid_or_missing(value: Any) -> bool:
    """Check if value is missing, None, or a validation failure dictionary."""
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    if isinstance(value, dict) and value.get("status") == "FAILED_VALIDATION":
        return True
    return False


def merge_extracted_data(original: Dict[str, Any], fallback: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge fallback extraction results into the original rule-based extraction dict.

    Overwrites only invalid or missing values in the original dict.

    Args:
        original: Base dictionary containing regex-extracted (and potentially failed) fields.
        fallback: Dictionary returned by the Mistral Vision fallback.

    Returns:
        Merged dictionary.
    """
    if not fallback:
        return original

    merged = {}

    for key, value in original.items():
        fallback_value = fallback.get(key)

        if isinstance(value, dict):
            # Nested section (e.g. provider, customer, account_and_bill, balance_details)
            if isinstance(fallback_value, dict):
                merged[key] = _merge_sections(value, fallback_value)
            else:
                merged[key] = value.copy()
        elif isinstance(value, list) and key == "meter_details":
            # List of meter details
            if isinstance(fallback_value, list) and fallback_value:
                merged[key] = _merge_lists(value, fallback_value)
            else:
                merged[key] = value.copy()
        else:
            # Flat top-level values
            if is_invalid_or_missing(value) and fallback_value is not None:
                logger.info("Merging top-level field '%s': '%s' -> '%s'", key, value, fallback_value)
                merged[key] = fallback_value
            else:
                merged[key] = value

    # Check for sections present in fallback but missing in original
    for key, fallback_value in fallback.items():
        if key not in merged:
            logger.info("Adding missing key '%s' from fallback", key)
            merged[key] = fallback_value

    return merged


def _merge_sections(original_sec: Dict[str, Any], fallback_sec: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two section dictionaries field by field."""
    merged_sec = original_sec.copy()

    for field, value in original_sec.items():
        fallback_val = fallback_sec.get(field)
        if is_invalid_or_missing(value) and fallback_val is not None:
            logger.info("Merging field '%s': '%s' -> '%s'", field, value, fallback_val)
            merged_sec[field] = fallback_val

    # Add missing fields
    for field, fallback_val in fallback_sec.items():
        if field not in merged_sec:
            merged_sec[field] = fallback_val

    return merged_sec


def _merge_lists(original_list: List[Dict[str, Any]], fallback_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Merge two meter_details lists.

    If the original list is empty or fails rules, we prefer the fallback list.
    Otherwise, we try to merge or align them, or fall back to returning the
    fallback list if the original list is deemed incomplete/invalid.
    """
    # If original has no valid elements, use fallback
    valid_original_count = sum(1 for item in original_list if not any(is_invalid_or_missing(v) for v in item.values()))
    if valid_original_count == 0:
        logger.info("Original list has no valid elements; using fallback list of length %d", len(fallback_list))
        return fallback_list

    # Otherwise, return fallback as primary since visual table extraction is the ultimate source of truth
    # for charge tables.
    logger.info("Merging lists: returning fallback list of length %d as main source of truth for details", len(fallback_list))
    return fallback_list
