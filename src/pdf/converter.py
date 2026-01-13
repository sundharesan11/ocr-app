"""PDF and image conversion utilities."""

import io
from pathlib import Path
from typing import BinaryIO

import pillow_heif
from pdf2image import convert_from_bytes
from PIL import Image

from src.utils.logging import get_logger

logger = get_logger(__name__)

# Register HEIF opener with Pillow
pillow_heif.register_heif_opener()


class ConversionError(Exception):
    """Exception raised when file conversion fails."""

    pass


def convert_to_images(
    file_content: bytes,
    filename: str,
    dpi: int = 150,  # Reduced from 300 for faster processing
) -> list[bytes]:
    """Convert PDF or image file to list of image bytes.

    Handles:
    - Single/multi-page PDFs
    - Scanned PDFs
    - JPG, PNG, WEBP images
    - HEIC images (from iOS devices)

    Args:
        file_content: Raw file bytes
        filename: Original filename (used for format detection)
        dpi: Resolution for PDF rendering (default 150 for balanced speed/quality)

    Returns:
        List of image bytes (PNG format), one per page

    Raises:
        ConversionError: If file cannot be converted
    """
    if not file_content:
        raise ConversionError("Empty file content provided")

    # Determine file type from extension and magic bytes
    file_ext = Path(filename).suffix.lower()
    file_type = _detect_file_type(file_content, file_ext)

    logger.info(
        "Converting file to images",
        filename=filename,
        detected_type=file_type,
        size_bytes=len(file_content),
    )

    try:
        if file_type == "pdf":
            return _convert_pdf(file_content, dpi)
        elif file_type in ("jpeg", "png", "webp"):
            return _convert_standard_image(file_content)
        elif file_type == "heic":
            return _convert_heic(file_content)
        else:
            raise ConversionError(f"Unsupported file type: {file_type}")

    except ConversionError:
        raise
    except Exception as e:
        logger.error("File conversion failed", error=str(e))
        raise ConversionError(f"Failed to convert file: {e}") from e


def _detect_file_type(content: bytes, extension: str) -> str:
    """Detect file type from magic bytes and extension.

    Args:
        content: File content bytes
        extension: File extension (with dot)

    Returns:
        Detected file type string
    """
    # Check magic bytes first
    if content[:5] == b"%PDF-":
        return "pdf"
    if content[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if content[:2] == b"\xff\xd8":
        return "jpeg"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "webp"
    if b"ftypheic" in content[:20] or b"ftypmif1" in content[:20]:
        return "heic"

    # Fall back to extension
    ext_map = {
        ".pdf": "pdf",
        ".jpg": "jpeg",
        ".jpeg": "jpeg",
        ".png": "png",
        ".webp": "webp",
        ".heic": "heic",
        ".heif": "heic",
    }
    return ext_map.get(extension, "unknown")


def _convert_pdf(content: bytes, dpi: int) -> list[bytes]:
    """Convert PDF to list of PNG images.

    Args:
        content: PDF file bytes
        dpi: Rendering resolution

    Returns:
        List of PNG image bytes
    """
    logger.debug("Converting PDF pages to images", dpi=dpi)

    # Convert PDF pages to PIL Images
    images = convert_from_bytes(content, dpi=dpi, fmt="png")

    logger.info("PDF conversion complete", page_count=len(images))

    # Convert each PIL Image to bytes
    result = []
    for idx, img in enumerate(images):
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        result.append(buffer.getvalue())
        logger.debug(f"Converted page {idx + 1}")

    return result


def _convert_standard_image(content: bytes) -> list[bytes]:
    """Convert standard image formats to PNG.

    Args:
        content: Image file bytes

    Returns:
        List with single PNG image bytes
    """
    logger.debug("Converting standard image to PNG")

    # Open and convert to RGB if needed
    img = Image.open(io.BytesIO(content))

    # Convert to RGB if necessary (e.g., from RGBA or palette)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    # Save as PNG
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")

    return [buffer.getvalue()]


def _convert_heic(content: bytes) -> list[bytes]:
    """Convert HEIC/HEIF image to PNG.

    Args:
        content: HEIC file bytes

    Returns:
        List with single PNG image bytes
    """
    logger.debug("Converting HEIC image to PNG")

    # Open HEIC with pillow-heif
    heif_file = pillow_heif.read_heif(content)

    # Convert to PIL Image
    img = Image.frombytes(
        heif_file.mode,
        heif_file.size,
        heif_file.data,
        "raw",
    )

    # Convert to RGB if needed
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    # Save as PNG
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")

    return [buffer.getvalue()]


def get_page_count(file_content: bytes, filename: str) -> int:
    """Get the number of pages/images in a file.

    Args:
        file_content: Raw file bytes
        filename: Original filename

    Returns:
        Number of pages (1 for single images)
    """
    file_ext = Path(filename).suffix.lower()
    file_type = _detect_file_type(file_content, file_ext)

    if file_type == "pdf":
        # Use pypdfium2 for fast page counting
        try:
            import pypdfium2 as pdfium

            pdf = pdfium.PdfDocument(file_content)
            return len(pdf)
        except Exception:
            # Fall back to pdf2image
            from pdf2image import pdfinfo_from_bytes

            info = pdfinfo_from_bytes(file_content)
            return info.get("Pages", 1)

    return 1  # Single image
