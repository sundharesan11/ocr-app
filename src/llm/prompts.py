"""Prompt templates for LLM parsing."""

# System prompt for structured medical form extraction
EXTRACTION_SYSTEM_PROMPT = """You are a medical document processing assistant. Your task is to extract structured data from OCR text of medical forms.

IMPORTANT GUIDELINES:
1. Extract ALL visible fields from the document
2. For handwritten text, make your best interpretation
3. For checkboxes, use true/false values
4. For empty or unclear fields, use null
5. Preserve original formatting for narrative fields
6. Do NOT make up information - only extract what's present
7. For dates, use ISO 8601 format (YYYY-MM-DD) when possible
8. For phone numbers, preserve the original format

FIELD CATEGORIES:
- Patient Demographics: name, date_of_birth, address, phone, email, ssn
- Insurance: provider, policy_number, group_number
- Medical History: conditions, medications, allergies, surgeries
- Visit Information: date, reason, symptoms
- Checkboxes: yes/no or true/false fields
- Narratives: detailed descriptions, notes

OUTPUT FORMAT:
Return a valid JSON object with all extracted fields. Use snake_case for field names.
Include a "_field_confidences" object with confidence scores (0.0-1.0) for each field."""


def get_extraction_prompt(ocr_text: str, field_hints: list[str] | None = None) -> str:
    """Generate the extraction prompt for LLM parsing.

    Args:
        ocr_text: Raw OCR text to parse
        field_hints: Optional list of expected field names

    Returns:
        Formatted prompt string
    """
    prompt_parts = [
        "Extract structured data from the following OCR text of a medical form.",
        "",
    ]

    if field_hints:
        prompt_parts.extend(
            [
                "Expected fields to look for:",
                ", ".join(field_hints),
                "",
            ]
        )

    prompt_parts.extend(
        [
            "OCR TEXT:",
            "---",
            ocr_text,
            "---",
            "",
            "Return a JSON object with all extracted fields and a _field_confidences object.",
            "Use null for fields that cannot be determined.",
        ]
    )

    return "\n".join(prompt_parts)


# Common medical form fields for reference
COMMON_MEDICAL_FIELDS = [
    # Patient Demographics
    "patient_first_name",
    "patient_last_name",
    "patient_middle_name",
    "date_of_birth",
    "gender",
    "ssn",
    "address_street",
    "address_city",
    "address_state",
    "address_zip",
    "phone_home",
    "phone_cell",
    "phone_work",
    "email",
    "emergency_contact_name",
    "emergency_contact_phone",
    "emergency_contact_relationship",
    # Insurance
    "insurance_provider",
    "insurance_policy_number",
    "insurance_group_number",
    "insurance_subscriber_name",
    "insurance_subscriber_dob",
    # Medical History
    "current_medications",
    "allergies",
    "past_surgeries",
    "chronic_conditions",
    "family_history",
    # Visit Information
    "visit_date",
    "visit_reason",
    "chief_complaint",
    "symptoms_description",
    "pain_level",
    "pain_location",
    # Common Checkboxes
    "has_diabetes",
    "has_hypertension",
    "has_heart_disease",
    "has_asthma",
    "has_cancer_history",
    "is_pregnant",
    "is_smoker",
    "uses_alcohol",
    "uses_recreational_drugs",
    # Consent
    "consent_to_treat",
    "consent_to_share_info",
    "hipaa_acknowledgment",
    # Signatures
    "patient_signature_date",
    "guardian_signature_date",
]


# System prompt for position-aware extraction (for text overlay)
POSITION_EXTRACTION_SYSTEM_PROMPT = """You are a medical document processing assistant. Your task is to extract structured data from a medical form image, including the POSITION of each field.

IMPORTANT GUIDELINES:
1. Extract ALL visible fields from the document
2. For each field, provide both the VALUE and its POSITION (bounding box)
3. Positions should be in PERCENTAGE coordinates (0-100) relative to the image dimensions
4. For handwritten text, make your best interpretation
5. For checkboxes, use true/false values
6. For empty or unclear fields, use null for the value but still include position

OUTPUT FORMAT:
Return a valid JSON object with:
{
  "fields": [
    {
      "name": "field_name_in_snake_case",
      "value": "extracted value or null",
      "position": {
        "x": 10,      // percentage from left (0-100)
        "y": 15,      // percentage from top (0-100)  
        "width": 25,  // percentage of image width
        "height": 3   // percentage of image height
      },
      "confidence": 0.95
    }
  ],
  "page_count": 1
}

The position should represent where the HANDWRITTEN/FILLED VALUE appears, not the label.
This will be used to overlay typed text at the same locations on a blank form."""


def get_position_extraction_prompt(image_width: int, image_height: int) -> str:
    """Generate prompt for position-aware extraction from images.

    Args:
        image_width: Image width in pixels
        image_height: Image height in pixels

    Returns:
        Formatted prompt string
    """
    return f"""Analyze this medical form image and extract all filled fields.

Image dimensions: {image_width}x{image_height} pixels

For each field you find:
1. Identify the field name/label
2. Extract the handwritten or filled value
3. Determine the POSITION of the filled value (not the label) as percentage coordinates

Return positions as percentages (0-100) of the image dimensions.
For example, if text is at pixel position (150, 200) in a 1000x800 image:
- x = (150/1000) * 100 = 15
- y = (200/800) * 100 = 25

Focus on extracting the actual hand-filled data, not printed labels.
Return the JSON structure as specified in the system prompt."""
