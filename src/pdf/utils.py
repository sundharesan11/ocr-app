"""PDF utility functions."""

import io

from pypdf import PdfReader

from src.utils.logging import get_logger

logger = get_logger(__name__)


def is_pdf_fillable(pdf_content: bytes) -> bool:
    """Check if a PDF has fillable form fields.

    Args:
        pdf_content: PDF file bytes

    Returns:
        True if PDF has AcroForm fields
    """
    try:
        reader = PdfReader(io.BytesIO(pdf_content))
        fields = reader.get_fields()
        return bool(fields)
    except Exception as e:
        logger.warning("Could not check PDF for form fields", error=str(e))
        return False


def get_pdf_metadata(pdf_content: bytes) -> dict:
    """Extract metadata from a PDF.

    Args:
        pdf_content: PDF file bytes

    Returns:
        Dictionary with PDF metadata
    """
    try:
        reader = PdfReader(io.BytesIO(pdf_content))

        metadata = {
            "page_count": len(reader.pages),
            "is_encrypted": reader.is_encrypted,
            "has_form_fields": bool(reader.get_fields()),
            "form_field_count": len(reader.get_fields() or {}),
        }

        # Extract document info if available
        if reader.metadata:
            metadata.update(
                {
                    "title": reader.metadata.get("/Title", ""),
                    "author": reader.metadata.get("/Author", ""),
                    "creator": reader.metadata.get("/Creator", ""),
                    "producer": reader.metadata.get("/Producer", ""),
                }
            )

        return metadata

    except Exception as e:
        logger.error("Failed to extract PDF metadata", error=str(e))
        return {"error": str(e)}


def is_scanned_pdf(pdf_content: bytes) -> bool:
    """Check if a PDF appears to be a scanned document.

    A PDF is likely scanned if it has:
    - No extractable text
    - Contains images

    Args:
        pdf_content: PDF file bytes

    Returns:
        True if PDF appears to be scanned
    """
    try:
        reader = PdfReader(io.BytesIO(pdf_content))

        total_text = ""
        has_images = False

        for page in reader.pages:
            # Try to extract text
            text = page.extract_text() or ""
            total_text += text

            # Check for images
            if "/XObject" in page.get("/Resources", {}):
                xobjects = page["/Resources"]["/XObject"]
                for obj in xobjects.values():
                    if obj.get("/Subtype") == "/Image":
                        has_images = True
                        break

        # Consider it scanned if mostly images with little text
        is_scanned = has_images and len(total_text.strip()) < 100

        logger.debug(
            "Scanned PDF check",
            text_length=len(total_text),
            has_images=has_images,
            is_scanned=is_scanned,
        )

        return is_scanned

    except Exception as e:
        logger.warning("Could not check if PDF is scanned", error=str(e))
        return False
