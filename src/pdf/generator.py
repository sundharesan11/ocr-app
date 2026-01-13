"""PDF Generator - Creates clean structured PDFs from extracted form data.

Instead of overlaying text on templates, this generates a new, clean PDF
that organizes extracted fields into logical sections.
"""

import io
from dataclasses import dataclass, field
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class FormSection:
    """A section of form fields."""

    title: str
    fields: list[dict[str, Any]] = field(default_factory=list)


# Common form sections based on medical intake forms
SECTION_MAPPINGS = {
    # Patient Information
    "patient_info": {
        "title": "Patient Information",
        "keywords": [
            "name",
            "date_of_birth",
            "dob",
            "age",
            "gender",
            "sex",
            "address",
            "city",
            "state",
            "zip",
            "phone",
            "email",
            "ssn",
            "social_security",
            "marital_status",
            "occupation",
            "employer",
            "middle_initial",
            "today_date",
        ],
    },
    # Emergency Contact
    "emergency_contact": {
        "title": "Emergency Contact",
        "keywords": [
            "emergency",
            "contact",
            "relationship",
            "next_of_kin",
        ],
    },
    # Insurance Information
    "insurance": {
        "title": "Insurance Information",
        "keywords": [
            "insurance",
            "policy",
            "group",
            "subscriber",
            "carrier",
            "plan",
            "id_number",
            "member",
        ],
    },
    # Medical History
    "medical_history": {
        "title": "Medical History",
        "keywords": [
            "history",
            "condition",
            "diagnosis",
            "disease",
            "illness",
            "surgery",
            "hospitalization",
            "allergy",
            "allergies",
            "previous",
            "past",
            "chronic",
        ],
    },
    # Current Medications
    "medications": {
        "title": "Current Medications",
        "keywords": [
            "medication",
            "medicine",
            "drug",
            "prescription",
            "dosage",
            "dose",
            "pharmacy",
        ],
    },
    # Symptoms / Chief Complaint
    "symptoms": {
        "title": "Symptoms & Chief Complaint",
        "keywords": [
            "symptom",
            "complaint",
            "pain",
            "problem",
            "issue",
            "reason",
            "visit",
            "onset",
            "duration",
            "severity",
            "chief",
            "cause",
            "episode",
        ],
    },
    # Family History
    "family_history": {
        "title": "Family History",
        "keywords": [
            "family",
            "mother",
            "father",
            "sibling",
            "brother",
            "sister",
            "parent",
            "hereditary",
            "genetic",
        ],
    },
    # Lifestyle
    "lifestyle": {
        "title": "Lifestyle & Social History",
        "keywords": [
            "smoke",
            "smoking",
            "tobacco",
            "alcohol",
            "drink",
            "exercise",
            "diet",
            "sleep",
            "stress",
            "lifestyle",
            "recreational",
        ],
    },
    # Consent & Authorization
    "consent": {
        "title": "Consent & Authorization",
        "keywords": [
            "consent",
            "authorization",
            "signature",
            "agree",
            "acknowledge",
            "hipaa",
            "privacy",
            "release",
        ],
    },
}


def categorize_fields(fields: list[dict]) -> dict[str, FormSection]:
    """Categorize extracted fields into logical sections.

    Args:
        fields: List of field dictionaries with 'name' and 'value'

    Returns:
        Dictionary of section_id -> FormSection
    """
    sections: dict[str, FormSection] = {}
    uncategorized = FormSection(title="Other Information")

    for f in fields:
        field_name = f.get("name", "").lower()
        field_value = f.get("value")

        if not field_value:
            continue

        categorized = False
        for section_id, section_config in SECTION_MAPPINGS.items():
            for keyword in section_config["keywords"]:
                if keyword in field_name:
                    if section_id not in sections:
                        sections[section_id] = FormSection(title=section_config["title"])
                    sections[section_id].fields.append(f)
                    categorized = True
                    break
            if categorized:
                break

        if not categorized:
            uncategorized.fields.append(f)

    # Add uncategorized if it has fields
    if uncategorized.fields:
        sections["other"] = uncategorized

    return sections


def format_field_name(name: str) -> str:
    """Convert snake_case to Title Case.

    Args:
        name: Field name in snake_case

    Returns:
        Formatted field name
    """
    return name.replace("_", " ").title()


def generate_pdf(
    fields: list[dict],
    title: str = "Medical Intake Form",
    include_metadata: bool = True,
) -> bytes:
    """Generate a clean, structured PDF from extracted form fields.

    Args:
        fields: List of extracted field dictionaries
        title: PDF title/header
        include_metadata: Whether to include extraction metadata

    Returns:
        PDF file as bytes
    """
    logger.info(f"Generating PDF with {len(fields)} fields")

    # Create PDF buffer
    buffer = io.BytesIO()

    # Create document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    # Get styles
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=18,
        spaceAfter=20,
        textColor=colors.HexColor("#1a365d"),
    )

    section_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontSize=14,
        spaceBefore=15,
        spaceAfter=10,
        textColor=colors.HexColor("#2c5282"),
        borderColor=colors.HexColor("#2c5282"),
        borderWidth=0,
        borderPadding=5,
    )

    # Build content
    story = []

    # Title
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 0.2 * inch))

    # Categorize fields into sections
    sections = categorize_fields(fields)

    # Define section order
    section_order = [
        "patient_info",
        "emergency_contact",
        "insurance",
        "symptoms",
        "medical_history",
        "medications",
        "family_history",
        "lifestyle",
        "consent",
        "other",
    ]

    # Build each section
    for section_id in section_order:
        if section_id not in sections:
            continue

        section = sections[section_id]
        if not section.fields:
            continue

        # Section header
        story.append(Paragraph(section.title, section_style))

        # Create table data for this section
        table_data = []
        for f in section.fields:
            field_name = format_field_name(f.get("name", "Unknown"))
            field_value = str(f.get("value", ""))

            # Truncate long values
            if len(field_value) > 100:
                field_value = field_value[:97] + "..."

            table_data.append([field_name, field_value])

        if table_data:
            # Create table
            table = Table(
                table_data,
                colWidths=[2.5 * inch, 4.5 * inch],
                repeatRows=0,
            )

            table.setStyle(
                TableStyle(
                    [
                        # Header styling (first row)
                        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f7fafc")),
                        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#2d3748")),
                        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 10),
                        # Cell styling
                        ("ALIGN", (0, 0), (0, -1), "RIGHT"),
                        ("ALIGN", (1, 0), (1, -1), "LEFT"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("PADDING", (0, 0), (-1, -1), 8),
                        # Grid
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                        # Alternate row colors
                        (
                            "ROWBACKGROUNDS",
                            (0, 0),
                            (-1, -1),
                            [colors.white, colors.HexColor("#f7fafc")],
                        ),
                    ]
                )
            )

            story.append(table)
            story.append(Spacer(1, 0.15 * inch))

    # Build PDF
    doc.build(story)

    # Get PDF bytes
    pdf_bytes = buffer.getvalue()
    buffer.close()

    logger.info(f"PDF generated, size: {len(pdf_bytes)} bytes")
    return pdf_bytes
