"""Unit tests for LLM base classes and interfaces."""

import pytest

from src.llm.base import BaseLLM, LLMError, ParseResult


class TestParseResult:
    """Tests for ParseResult dataclass."""

    def test_create_valid_result(self):
        """Test creating a valid parse result."""
        result = ParseResult(
            data={"name": "John", "age": 30},
            field_confidences={"name": 0.95, "age": 0.88},
            overall_confidence=0.91,
            metadata={"provider": "test"},
        )

        assert result.data["name"] == "John"
        assert result.field_confidences["name"] == 0.95
        assert result.overall_confidence == 0.91

    def test_get_low_confidence_fields(self):
        """Test getting fields with low confidence."""
        result = ParseResult(
            data={"name": "John", "dob": "1990-01-01", "phone": "555"},
            field_confidences={"name": 0.95, "dob": 0.65, "phone": 0.45},
            overall_confidence=0.68,
        )

        low_conf = result.get_low_confidence_fields(threshold=0.7)
        assert "dob" in low_conf
        assert "phone" in low_conf
        assert "name" not in low_conf

    def test_default_values(self):
        """Test default values are set correctly."""
        result = ParseResult(data={"test": "value"})

        assert result.field_confidences == {}
        assert result.overall_confidence == 0.0
        assert result.metadata == {}
        assert result.raw_response is None


class TestLLMError:
    """Tests for LLMError exception."""

    def test_error_creation(self):
        """Test creating an LLM error."""
        error = LLMError("Parse failed", "gemini", {"tokens": 1000})

        assert error.message == "Parse failed"
        assert error.provider == "gemini"
        assert error.details["tokens"] == 1000
        assert "gemini" in str(error)


class TestBaseLLMInterface:
    """Tests for BaseLLM abstract interface."""

    def test_cannot_instantiate_base(self):
        """Test that BaseLLM cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseLLM()

    def test_valid_subclass(self):
        """Test that a valid subclass can be created."""

        class MockLLM(BaseLLM):
            @property
            def provider_name(self) -> str:
                return "mock"

            async def parse_to_json(
                self, ocr_text: str, field_hints: list[str] | None = None
            ) -> ParseResult:
                return ParseResult(
                    data={"parsed": True},
                    overall_confidence=0.9,
                )

        llm = MockLLM()
        assert llm.provider_name == "mock"
