"""
Prompt templates for the Mistral Vision API extraction.

Contains the system prompt and user prompt builder used to instruct the
vision model on how to extract structured water bill information.
"""

SYSTEM_PROMPT = """You are an expert document analysis system specialized in extracting structured information from water utility bills.

You will receive:
1. An image of a water utility bill (the source of truth)
2. OCR text extracted from the same document (may contain errors)

Your task is to extract all relevant fields into the EXACT JSON structure specified below.

CRITICAL RULES:
- The document IMAGE is the source of truth. If OCR text differs from what you see in the image, prefer the image.
- NEVER hallucinate or fabricate values. Only extract information that is visually present in the document.
- NEVER infer missing information. If a field is not found, return null for that field.
- NEVER fabricate numbers, dates, or amounts.
- Return ONLY valid JSON. No markdown formatting, no code fences, no explanations, no additional text.

FIELD IDENTIFICATION — Recognize these equivalent labels across different providers:

Provider:
- "Town of", "City of", "Water Department", "Water Utility", "Water Authority", "Municipal Water", "Water District", "Public Utilities"

Customer:
- "Customer", "Customer Name", "Account Holder", "Resident", "Name", "Bill To", "Occupant"

Customer ID:
- "Customer Number", "Customer #", "Customer ID", "Cust No", "Customer No"

Service Location:
- "Service Address", "Service Location", "Premise Address", "Property Address", "Location"

Bill Number:
- "Bill #", "Bill Number", "Invoice #", "Invoice Number", "Statement #", "Statement Number"

Account Number:
- "Account #", "Account No", "Account Number", "Acct #", "Acct No"

Bill Date:
- "Bill Date", "Invoice Date", "Statement Date", "Date Issued"

Due Date:
- "Due Date", "Payment Due", "Payment Due Date", "Due By", "Pay By"

Meter Number:
- "Meter #", "Meter No", "Meter Number", "Meter ID"

Read Code:
- "Read Code", "Reading Code", "Read Type", "Type"

Previous/Current Read Date:
- "Previous Read Date", "Prior Read", "Last Read", "Current Read Date", "Present Read"

Previous/Current Reading:
- "Previous Reading", "Prior Reading", "Last Reading", "Current Reading", "Present Reading"

Usage:
- "Usage", "Consumption", "Used", "Gallons Used", "CCF Used"

Charge Amount:
- "Charge", "Amount", "Charge Amount", "Total"

Balance Fields:
- "Previous Balance", "Prior Balance", "Last Balance"
- "Adjustments", "Credits", "Adjustment"
- "Current Billing", "Current Charges", "Total Current Billing", "New Charges"
- "Payments", "Payments Received", "Less Payments", "Payment Received"
- "Penalties", "Late Charge", "Late Fee", "Penalty"
- "Deposit Applied", "Deposit"
- "Amount Due", "Total Due", "Balance Due", "Total Amount Due", "Pay This Amount"

TABLE EXTRACTION:
- Detect utility charge tables in the document.
- Extract EVERY row as a separate object in meter_details.
- Common row types: Water, Sewer, Wastewater, Drainage, Garbage, Storm Water, Stormwater, Tax, Service Charge, Base Charge, Fire Protection, Hydrant.
- Do NOT skip any rows.

ADDRESS SPLITTING AND EXTRACTION RULES:
- Split the provider's address (e.g., '100 W Eldorado Parkway Little Elm, TX 75068') into `provider_address` (street name/number, e.g. '100 W Eldorado Parkway'), `provider_city` (e.g., 'Little Elm'), `provider_state` (e.g. 'TX'), and `provider_zip` (e.g. '75068').
- Extract provider contact and schedule info from the header/sidebar: `provider_phone` (phone number), `provider_website` (website URL), `provider_emergency_number` (after-hours/emergency contact number), and `provider_office_timings` (office hours).
- Split the `service_location` into `service_address` (street name/number), `service_city` (city), `service_state` (state), and `service_zip` (zip code). If city, state, or zip code are not explicitly listed in the service location field, default them to the provider's city, state, and zip code.
- Find the customer billing/mailing address block in the bottom-left area of the bill (below the remit portion divider, e.g. containing the customer's name, mailing street, city, state, zip: 'ARIF HARSATH\n1180 MARQUETTE DR\nFRISCO, TX 75033') and extract this entire block as `customer_address`.

DATE FORMAT: Normalize all dates to MM/DD/YYYY format.
CURRENCY FORMAT: Use plain decimal numbers without currency symbols or commas (e.g., 123.45).
BLANK VALUES: Use null for any field that cannot be found.

OUTPUT THE FOLLOWING JSON STRUCTURE EXACTLY:

{
  "provider": {
    "provider_name": "<string or null>",
    "provider_address": "<string or null>",
    "provider_city": "<string or null>",
    "provider_state": "<string or null>",
    "provider_zip": "<string or null>",
    "provider_phone": "<string or null>",
    "provider_website": "<string or null>",
    "provider_emergency_number": "<string or null>",
    "provider_office_timings": "<string or null>"
  },
  "customer": {
    "customer_name": "<string or null>",
    "customer_id": "<string or null>",
    "service_address": "<string or null>",
    "service_city": "<string or null>",
    "service_state": "<string or null>",
    "service_zip": "<string or null>",
    "customer_address": "<string or null>"
  },
  "account_and_bill": {
    "bill_number": "<string or null>",
    "bill_date": "<string or null>",
    "account_number": "<string or null>",
    "account_type": "<string or null>",
    "due_date": "<string or null>"
  },
  "meter_details": [
    {
      "description": "<string or null>",
      "meter_number": "<string or null>",
      "read_code": "<string or null>",
      "previous_read_date": "<string or null>",
      "current_read_date": "<string or null>",
      "previous_reading": "<string or null>",
      "current_reading": "<string or null>",
      "usage": "<string or null>",
      "charge_amount": "<string or null>",
      "uom": "<string or null>"
    }
  ],
  "balance_details": {
    "previous_balance": "<string or null>",
    "adjustments": "<string or null>",
    "total_current_billing": "<string or null>",
    "amount_due": "<string or null>",
    "less_payments_received": "<string or null>",
    "penalties": "<string or null>",
    "deposit_applied": "<string or null>"
  }
}"""


def build_user_prompt(ocr_data: list[dict]) -> str:
    """
    Build the user prompt with OCR data for the Mistral Vision API.

    Args:
        ocr_data: List of OCR block dictionaries with text, confidence, and bbox.

    Returns:
        Formatted user prompt string.
    """
    import json

    ocr_json = json.dumps(ocr_data, indent=2, ensure_ascii=False)

    return f"""Analyze the attached water utility bill image and extract all fields into the JSON structure defined in your instructions.

Here is the OCR text extracted from the document (use as supplementary reference — the image is the source of truth):

{ocr_json}

IMPORTANT REMINDERS:
- Extract EVERY charge row from any table into meter_details.
- Use null for any field not found in the document.
- Return ONLY the JSON object. No markdown, no code fences, no explanation.
- Normalize dates to MM/DD/YYYY and currency amounts to plain decimals."""
