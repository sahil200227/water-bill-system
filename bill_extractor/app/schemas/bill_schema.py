"""
Water bill extraction response schemas matching the exact required JSON output.
"""
from typing import List, Optional

from pydantic import BaseModel, Field


class ProviderInfo(BaseModel):
    """Water utility provider information."""

    provider_name: Optional[str] = Field(default=None, description="Name of the water utility provider")
    provider_address: Optional[str] = Field(default=None, description="Address / street address of the provider")
    provider_city: Optional[str] = Field(default=None, description="City of the provider")
    provider_state: Optional[str] = Field(default=None, description="State of the provider")
    provider_zip: Optional[str] = Field(default=None, description="Zip code of the provider")
    provider_phone: Optional[str] = Field(default=None, description="Phone number of the provider")
    provider_website: Optional[str] = Field(default=None, description="Website of the provider")
    provider_emergency_number: Optional[str] = Field(default=None, description="Emergency contact number of the provider")
    provider_office_timings: Optional[str] = Field(default=None, description="Office hours/timings of the provider")


class CustomerInfo(BaseModel):
    """Customer information from the bill."""

    customer_name: Optional[str] = Field(default=None, description="Customer full name")
    customer_id: Optional[str] = Field(default=None, description="Customer identifier")
    service_address: Optional[str] = Field(default=None, description="Street address of the service location")
    service_city: Optional[str] = Field(default=None, description="City of the service location")
    service_state: Optional[str] = Field(default=None, description="State of the service location")
    service_zip: Optional[str] = Field(default=None, description="Zip code of the service location")
    customer_address: Optional[str] = Field(default=None, description="Customer billing/mailing address from bottom left")


class AccountAndBill(BaseModel):
    """Account and billing metadata."""

    bill_number: Optional[str] = Field(default=None, description="Bill / invoice number")
    bill_date: Optional[str] = Field(default=None, description="Bill date (MM/DD/YYYY)")
    account_number: Optional[str] = Field(default=None, description="Account number")
    account_type: Optional[str] = Field(default=None, description="Account type")
    due_date: Optional[str] = Field(default=None, description="Payment due date (MM/DD/YYYY)")


class MeterDetail(BaseModel):
    """A single meter reading / charge row."""

    description: Optional[str] = Field(default=None, description="Charge description (e.g. Water, Sewer)")
    meter_number: Optional[str] = Field(default=None, description="Meter number")
    read_code: Optional[str] = Field(default=None, description="Read code (A/F/E/Actual/Final/Estimated)")
    previous_read_date: Optional[str] = Field(default=None, description="Previous reading date")
    current_read_date: Optional[str] = Field(default=None, description="Current reading date")
    previous_reading: Optional[str] = Field(default=None, description="Previous meter reading")
    current_reading: Optional[str] = Field(default=None, description="Current meter reading")
    usage: Optional[str] = Field(default=None, description="Usage amount")
    charge_amount: Optional[str] = Field(default=None, description="Charge amount")
    uom: Optional[str] = Field(default=None, description="Unit of measure (GAL/CCF/TGA/M3)")


class BalanceDetails(BaseModel):
    """Balance and payment summary."""

    previous_balance: Optional[str] = Field(default=None, description="Previous balance amount")
    adjustments: Optional[str] = Field(default=None, description="Adjustments amount")
    total_current_billing: Optional[str] = Field(default=None, description="Total current billing")
    amount_due: Optional[str] = Field(default=None, description="Total amount due")
    less_payments_received: Optional[str] = Field(default=None, description="Payments received")
    penalties: Optional[str] = Field(default=None, description="Penalty charges")
    deposit_applied: Optional[str] = Field(default=None, description="Deposit applied")


class WaterBillResponse(BaseModel):
    """Top-level response for the water bill extraction API."""

    success: bool = Field(default=True, description="Whether extraction succeeded")
    document_type: str = Field(default="Water Bill", description="Document type identifier")
    provider: ProviderInfo = Field(default_factory=ProviderInfo)
    customer: CustomerInfo = Field(default_factory=CustomerInfo)
    account_and_bill: AccountAndBill = Field(default_factory=AccountAndBill)
    meter_details: List[MeterDetail] = Field(default_factory=list, description="Meter readings and charges")
    balance_details: BalanceDetails = Field(default_factory=BalanceDetails)


class ExtractionErrorResponse(BaseModel):
    """Error response when extraction fails."""

    success: bool = Field(default=False)
    error: str = Field(..., description="Error description")
    detail: Optional[str] = Field(default=None, description="Detailed error information")
