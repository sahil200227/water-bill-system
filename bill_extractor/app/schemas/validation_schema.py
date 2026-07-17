"""
Validation result schemas for field-level validation output.
"""
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ValidationStatus(str, Enum):
    """Validation status values."""

    VALID = "VALID"
    FAILED_VALIDATION = "FAILED_VALIDATION"
    NOT_FOUND = "NOT_FOUND"


class ValidatedField(BaseModel):
    """A validated field with value and status."""

    value: Optional[Any] = Field(default=None, description="The validated value, or null on failure")
    status: ValidationStatus = Field(
        default=ValidationStatus.VALID,
        description="Validation status",
    )

    @classmethod
    def valid(cls, value: Any) -> "ValidatedField":
        return cls(value=value, status=ValidationStatus.VALID)

    @classmethod
    def failed(cls) -> "ValidatedField":
        return cls(value=None, status=ValidationStatus.FAILED_VALIDATION)

    @classmethod
    def not_found(cls) -> "ValidatedField":
        return cls(value=None, status=ValidationStatus.NOT_FOUND)
