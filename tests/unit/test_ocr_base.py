"""Unit tests for OCR base classes and interfaces."""

import pytest

from src.ocr.base import BaseOCR, OCRError, OCRResult


class TestOCRResult:
    """Tests for OCRResult dataclass."""

    def test_create_valid_result(self):
        """Test creating a valid OCR result."""
        result = OCRResult(
            text="Sample text",
            pages=["Page 1", "Page 2"],
            confidence=0.85,
            page_confidences=[0.80, 0.90],
            metadata={"provider": "test"},
        )

        assert result.text == "Sample text"
        assert len(result.pages) == 2
        assert result.confidence == 0.85
        assert result.metadata["provider"] == "test"

    def test_invalid_confidence_raises(self):
        """Test that invalid confidence raises ValueError."""
        with pytest.raises(ValueError, match="Confidence must be between"):
            OCRResult(text="test", confidence=1.5)

        with pytest.raises(ValueError, match="Confidence must be between"):
            OCRResult(text="test", confidence=-0.1)

    def test_default_values(self):
        """Test default values are set correctly."""
        result = OCRResult(text="test", confidence=0.5)

        assert result.pages == []
        assert result.page_confidences == []
        assert result.metadata == {}
        assert result.raw_response is None


class TestOCRError:
    """Tests for OCRError exception."""

    def test_error_creation(self):
        """Test creating an OCR error."""
        error = OCRError("Test error", "mistral", {"code": 500})

        assert error.message == "Test error"
        assert error.provider == "mistral"
        assert error.details["code"] == 500
        assert "mistral" in str(error)
        assert "Test error" in str(error)


class TestBaseOCRInterface:
    """Tests for BaseOCR abstract interface."""

    def test_cannot_instantiate_base(self):
        """Test that BaseOCR cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseOCR()

    def test_subclass_must_implement_methods(self):
        """Test that subclass must implement abstract methods."""

        class IncompleteOCR(BaseOCR):
            pass

        with pytest.raises(TypeError):
            IncompleteOCR()

    def test_valid_subclass(self):
        """Test that a valid subclass can be created."""

        class MockOCR(BaseOCR):
            @property
            def provider_name(self) -> str:
                return "mock"

            async def extract_text(self, images: list[bytes]) -> OCRResult:
                return OCRResult(text="mock text", confidence=0.9)

        ocr = MockOCR()
        assert ocr.provider_name == "mock"
