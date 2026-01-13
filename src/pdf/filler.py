"""PDF form filling utilities using AcroForm."""

import io
from dataclasses import dataclass
from typing import Any

from pypdf import PdfReader, PdfWriter

from src.utils.logging import get_logger

logger = get_logger(__name__)


class FormFillingError(Exception):
    """Exception raised when PDF form filling fails."""

    pass


@dataclass
class FormField:
    """Represents a PDF form field.

    Attributes:
        name: Field name in the PDF
        field_type: Type of field (text, checkbox, radio, etc.)
        value: Current field value
        options: Available options for choice fields
    """

    name: str
    field_type: str
    value: Any = None
    options: list[str] | None = None


def get_form_fields(pdf_content: bytes) -> list[FormField]:
    """Extract all form fields from a PDF.

    Args:
        pdf_content: PDF file bytes

    Returns:
        List of FormField objects

    Raises:
        FormFillingError: If PDF cannot be read
    """
    try:
        reader = PdfReader(io.BytesIO(pdf_content))

        if not reader.get_fields():
            logger.warning("PDF has no form fields")
            return []

        fields = []
        for field_name, field_obj in reader.get_fields().items():
            field_type = _get_field_type(field_obj)
            current_value = field_obj.get("/V")
            options = None

            # Get options for choice fields
            if "/Opt" in field_obj:
                options = field_obj["/Opt"]

            fields.append(
                FormField(
                    name=field_name,
                    field_type=field_type,
                    value=current_value,
                    options=options,
                )
            )

        logger.info("Extracted form fields", field_count=len(fields))
        return fields

    except Exception as e:
        logger.error("Failed to extract form fields", error=str(e))
        raise FormFillingError(f"Failed to read PDF form: {e}") from e


def fill_pdf_form(
    pdf_content: bytes,
    field_values: dict[str, Any],
    flatten: bool = False,
) -> bytes:
    """Fill PDF form fields with provided values.

    The function matches field names from the extracted data to PDF form fields.
    Field names are matched case-insensitively with common variations handled.

    Args:
        pdf_content: Original PDF file bytes
        field_values: Dictionary mapping field names to values
        flatten: If True, flatten form fields (make non-editable)

    Returns:
        Filled PDF as bytes

    Raises:
        FormFillingError: If form filling fails

    Example:
        filled_pdf = fill_pdf_form(
            pdf_bytes,
            {
                "patient_name": "John Doe",
                "date_of_birth": "1990-01-15",
                "has_diabetes": True,
            }
        )
    """
    if not pdf_content:
        raise FormFillingError("Empty PDF content provided")

    if not field_values:
        logger.warning("No field values provided, returning original PDF")
        return pdf_content

    try:
        reader = PdfReader(io.BytesIO(pdf_content))
        writer = PdfWriter()

        # Clone the PDF
        writer.append(reader)

        # Get available form fields
        pdf_fields = reader.get_fields() or {}

        if not pdf_fields:
            logger.warning("PDF has no fillable form fields")
            return pdf_content

        # Create field name mapping (case-insensitive, normalized)
        field_mapping = _create_field_mapping(pdf_fields.keys(), field_values.keys())

        # Fill matched fields
        filled_count = 0
        for pdf_field_name, data_field_name in field_mapping.items():
            value = field_values.get(data_field_name)

            if value is not None:
                try:
                    formatted_value = _format_field_value(value, pdf_fields.get(pdf_field_name))
                    writer.update_page_form_field_values(
                        writer.pages[0] if len(writer.pages) == 1 else None,
                        {pdf_field_name: formatted_value},
                    )
                    filled_count += 1
                except Exception as e:
                    logger.warning(f"Failed to fill field {pdf_field_name}", error=str(e))

        logger.info(
            "Filled form fields",
            filled_count=filled_count,
            total_fields=len(pdf_fields),
            provided_values=len(field_values),
        )

        # Optionally flatten the form
        if flatten:
            for page in writer.pages:
                # Remove annotations to flatten
                if "/Annots" in page:
                    del page["/Annots"]

        # Write to bytes
        output = io.BytesIO()
        writer.write(output)
        return output.getvalue()

    except FormFillingError:
        raise
    except Exception as e:
        logger.error("Form filling failed", error=str(e))
        raise FormFillingError(f"Failed to fill PDF form: {e}") from e


def _get_field_type(field_obj: dict) -> str:
    """Determine the type of a PDF form field.

    Args:
        field_obj: Field dictionary from pypdf

    Returns:
        Field type string
    """
    ft = field_obj.get("/FT", "")

    if ft == "/Tx":
        return "text"
    elif ft == "/Btn":
        # Check if checkbox or radio
        if field_obj.get("/Ff", 0) & (1 << 15):  # Radio flag
            return "radio"
        return "checkbox"
    elif ft == "/Ch":
        return "choice"
    elif ft == "/Sig":
        return "signature"

    return "unknown"


def _create_field_mapping(
    pdf_fields: list[str],
    data_fields: list[str],
) -> dict[str, str]:
    """Create mapping between PDF field names and data field names.

    Uses fuzzy matching to handle common variations:
    - Case differences: "PatientName" matches "patient_name"
    - Underscores vs spaces: "first_name" matches "first name"
    - Common prefixes: "txt_name" matches "name"

    Args:
        pdf_fields: Field names from the PDF
        data_fields: Field names from extracted data

    Returns:
        Dictionary mapping PDF field names to data field names
    """
    mapping = {}

    # Normalize field names for comparison
    def normalize(name: str) -> str:
        return name.lower().replace("_", "").replace(" ", "").replace("-", "")

    # Remove common prefixes
    def strip_prefix(name: str) -> str:
        prefixes = ["txt", "chk", "rad", "cmb", "field", "frm"]
        normalized = normalize(name)
        for prefix in prefixes:
            if normalized.startswith(prefix):
                return normalized[len(prefix) :]
        return normalized

    # Create normalized lookup for data fields
    data_lookup = {normalize(f): f for f in data_fields}
    data_lookup_stripped = {strip_prefix(f): f for f in data_fields}

    for pdf_field in pdf_fields:
        normalized = normalize(pdf_field)
        stripped = strip_prefix(pdf_field)

        # Try exact normalized match
        if normalized in data_lookup:
            mapping[pdf_field] = data_lookup[normalized]
        # Try stripped prefix match
        elif stripped in data_lookup_stripped:
            mapping[pdf_field] = data_lookup_stripped[stripped]
        # Try data field stripped
        elif normalized in data_lookup_stripped:
            mapping[pdf_field] = data_lookup_stripped[normalized]

    return mapping


def _format_field_value(value: Any, field_obj: dict | None) -> str:
    """Format a value for PDF form field.

    Args:
        value: Value to format
        field_obj: PDF field object (optional, for type hints)

    Returns:
        Formatted string value
    """
    if value is None:
        return ""

    # Handle booleans (for checkboxes)
    if isinstance(value, bool):
        return "Yes" if value else "Off"

    # Handle lists (join with newlines for multiline fields)
    if isinstance(value, list):
        return "\n".join(str(v) for v in value)

    # Handle dictionaries (convert to readable format)
    if isinstance(value, dict):
        return ", ".join(f"{k}: {v}" for k, v in value.items())

    return str(value)
