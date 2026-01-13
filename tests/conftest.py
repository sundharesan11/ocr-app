"""Pytest configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_image_bytes():
    """Generate minimal valid PNG bytes for testing."""
    # Minimal 1x1 white PNG
    return bytes(
        [
            0x89,
            0x50,
            0x4E,
            0x47,
            0x0D,
            0x0A,
            0x1A,
            0x0A,  # PNG signature
            0x00,
            0x00,
            0x00,
            0x0D,
            0x49,
            0x48,
            0x44,
            0x52,  # IHDR chunk
            0x00,
            0x00,
            0x00,
            0x01,
            0x00,
            0x00,
            0x00,
            0x01,  # 1x1
            0x08,
            0x02,
            0x00,
            0x00,
            0x00,
            0x90,
            0x77,
            0x53,
            0xDE,
            0x00,
            0x00,
            0x00,
            0x0C,
            0x49,
            0x44,
            0x41,  # IDAT chunk
            0x54,
            0x08,
            0xD7,
            0x63,
            0xF8,
            0xFF,
            0xFF,
            0x3F,
            0x00,
            0x05,
            0xFE,
            0x02,
            0xFE,
            0xDC,
            0xCC,
            0x59,
            0xE7,
            0x00,
            0x00,
            0x00,
            0x00,
            0x49,
            0x45,
            0x4E,  # IEND chunk
            0x44,
            0xAE,
            0x42,
            0x60,
            0x82,
        ]
    )


@pytest.fixture
def sample_pdf_bytes():
    """Generate minimal valid PDF bytes for testing."""
    # Minimal valid PDF with no form fields
    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
trailer
<< /Size 4 /Root 1 0 R >>
startxref
196
%%EOF
"""
    return pdf_content


@pytest.fixture
def mock_ocr_result():
    """Create a mock OCR result."""
    from src.ocr.base import OCRResult

    return OCRResult(
        text="Patient Name: John Doe\nDate of Birth: 01/15/1990\nPhone: 555-123-4567",
        pages=["Patient Name: John Doe\nDate of Birth: 01/15/1990\nPhone: 555-123-4567"],
        confidence=0.85,
        page_confidences=[0.85],
        metadata={"provider": "mock"},
    )


@pytest.fixture
def mock_parse_result():
    """Create a mock parse result."""
    from src.llm.base import ParseResult

    return ParseResult(
        data={
            "patient_name": "John Doe",
            "date_of_birth": "1990-01-15",
            "phone": "555-123-4567",
        },
        field_confidences={
            "patient_name": 0.95,
            "date_of_birth": 0.88,
            "phone": 0.92,
        },
        overall_confidence=0.91,
        metadata={"provider": "mock"},
    )
