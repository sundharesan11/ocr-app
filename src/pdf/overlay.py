"""PDF text overlay for regular PDFs without AcroForm fields.

This module uses PyMuPDF (fitz) to overlay typed text on regular PDFs
at specified coordinates, enabling filling of non-fillable forms.
"""

import io
from dataclasses import dataclass

import fitz  # PyMuPDF

from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class FieldPosition:
    """Position and value for a field to overlay.

    Attributes:
        name: Field name/identifier
        value: Text value to overlay
        x: X coordinate (from left, in points - 1 point = 1/72 inch)
        y: Y coordinate (from top, in points)
        width: Optional width constraint for text wrapping
        height: Optional height constraint
        page: Page number (0-indexed)
        font_size: Font size in points (default 10)
    """

    name: str
    value: str
    x: float
    y: float
    width: float | None = None
    height: float | None = None
    page: int = 0
    font_size: float = 10


class TextOverlayError(Exception):
    """Exception raised when text overlay fails."""

    pass


def overlay_text_on_pdf(
    pdf_content: bytes,
    fields: list[FieldPosition],
    font_name: str = "helv",
    font_color: tuple[float, float, float] = (0, 0, 0),  # Black
) -> bytes:
    """Overlay typed text on a regular PDF at specified positions.

    Args:
        pdf_content: Original PDF bytes
        fields: List of FieldPosition objects with values and coordinates
        font_name: Font name (helv, tiro, cour, etc.)
        font_color: RGB color tuple (0-1 range)

    Returns:
        Modified PDF bytes with overlaid text

    Raises:
        TextOverlayError: If overlay fails
    """
    if not pdf_content:
        raise TextOverlayError("Empty PDF content provided")

    if not fields:
        logger.warning("No fields to overlay, returning original PDF")
        return pdf_content

    try:
        # Open the PDF
        doc = fitz.open(stream=pdf_content, filetype="pdf")

        for field in fields:
            if field.page >= len(doc):
                logger.warning(
                    f"Field {field.name} specifies page {field.page} but PDF only has {len(doc)} pages"
                )
                continue

            if not field.value:
                continue

            page = doc[field.page]

            # Create text insertion point
            point = fitz.Point(field.x, field.y)

            # Insert text
            try:
                # Use insert_text for simple single-line text
                if field.width is None or len(field.value) < 50:
                    page.insert_text(
                        point,
                        field.value,
                        fontname=font_name,
                        fontsize=field.font_size,
                        color=font_color,
                    )
                else:
                    # Use text box for multiline/wrapped text
                    rect = fitz.Rect(
                        field.x,
                        field.y,
                        field.x + (field.width or 200),
                        field.y + (field.height or 50),
                    )
                    page.insert_textbox(
                        rect,
                        field.value,
                        fontname=font_name,
                        fontsize=field.font_size,
                        color=font_color,
                    )

                logger.debug(
                    f"Overlaid field {field.name} at ({field.x}, {field.y}) on page {field.page}"
                )

            except Exception as e:
                logger.warning(f"Failed to overlay field {field.name}: {e}")

        # Save to bytes
        output = io.BytesIO()
        doc.save(output)
        doc.close()

        logger.info(f"Text overlay complete, overlaid {len(fields)} fields")
        return output.getvalue()

    except TextOverlayError:
        raise
    except Exception as e:
        logger.error(f"Text overlay failed: {e}")
        raise TextOverlayError(f"Failed to overlay text: {e}") from e


def overlay_text_from_extracted_data(
    pdf_content: bytes,
    extracted_data: dict,
    field_positions: dict[str, dict],
) -> bytes:
    """Overlay text using extracted data and a field position mapping.

    Args:
        pdf_content: Original PDF bytes
        extracted_data: Dictionary of extracted field values
        field_positions: Mapping of field names to position dicts with keys:
                        x, y, page (optional), font_size (optional), width (optional)

    Returns:
        Modified PDF bytes

    Example:
        field_positions = {
            "patient_name": {"x": 150, "y": 100, "page": 0},
            "date_of_birth": {"x": 150, "y": 130, "page": 0},
            "phone": {"x": 150, "y": 160, "page": 0},
        }
        filled_pdf = overlay_text_from_extracted_data(pdf, data, field_positions)
    """
    fields = []

    for field_name, value in extracted_data.items():
        if field_name not in field_positions:
            continue

        pos = field_positions[field_name]

        # Convert value to string
        if isinstance(value, bool):
            str_value = "Yes" if value else "No"
        elif isinstance(value, list):
            str_value = ", ".join(str(v) for v in value)
        elif value is None:
            continue
        else:
            str_value = str(value)

        fields.append(
            FieldPosition(
                name=field_name,
                value=str_value,
                x=pos.get("x", 0),
                y=pos.get("y", 0),
                width=pos.get("width"),
                height=pos.get("height"),
                page=pos.get("page", 0),
                font_size=pos.get("font_size", 10),
            )
        )

    return overlay_text_on_pdf(pdf_content, fields)


def get_pdf_dimensions(pdf_content: bytes) -> list[dict]:
    """Get dimensions of each page in a PDF.

    Args:
        pdf_content: PDF bytes

    Returns:
        List of dicts with page dimensions: {width, height, page}
    """
    doc = fitz.open(stream=pdf_content, filetype="pdf")
    dimensions = []

    for i, page in enumerate(doc):
        rect = page.rect
        dimensions.append(
            {
                "page": i,
                "width": rect.width,
                "height": rect.height,
            }
        )

    doc.close()
    return dimensions
