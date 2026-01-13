"""Unit tests for PDF filler."""

import pytest

from src.pdf.filler import _create_field_mapping, _format_field_value


class TestFieldMapping:
    """Tests for field name mapping logic."""

    def test_exact_match(self):
        """Test exact field name matching."""
        pdf_fields = ["patient_name", "date_of_birth"]
        data_fields = ["patient_name", "date_of_birth"]

        mapping = _create_field_mapping(pdf_fields, data_fields)

        assert mapping["patient_name"] == "patient_name"
        assert mapping["date_of_birth"] == "date_of_birth"

    def test_case_insensitive_match(self):
        """Test case-insensitive matching."""
        pdf_fields = ["PatientName", "DateOfBirth"]
        data_fields = ["patient_name", "date_of_birth"]

        mapping = _create_field_mapping(pdf_fields, data_fields)

        assert mapping["PatientName"] == "patient_name"
        assert mapping["DateOfBirth"] == "date_of_birth"

    def test_prefix_stripping(self):
        """Test that common prefixes are stripped."""
        pdf_fields = ["txtPatientName", "chkHasDiabetes"]
        data_fields = ["patient_name", "has_diabetes"]

        mapping = _create_field_mapping(pdf_fields, data_fields)

        assert mapping["txtPatientName"] == "patient_name"
        assert mapping["chkHasDiabetes"] == "has_diabetes"

    def test_no_match_returns_empty(self):
        """Test that unmatched fields are not in mapping."""
        pdf_fields = ["field_a"]
        data_fields = ["completely_different"]

        mapping = _create_field_mapping(pdf_fields, data_fields)

        assert "field_a" not in mapping


class TestFieldValueFormatting:
    """Tests for field value formatting."""

    def test_format_string(self):
        """Test string formatting."""
        assert _format_field_value("John Doe", None) == "John Doe"

    def test_format_boolean_true(self):
        """Test boolean True formatting for checkboxes."""
        assert _format_field_value(True, None) == "Yes"

    def test_format_boolean_false(self):
        """Test boolean False formatting for checkboxes."""
        assert _format_field_value(False, None) == "Off"

    def test_format_list(self):
        """Test list formatting for multiline fields."""
        result = _format_field_value(["Item 1", "Item 2"], None)
        assert "Item 1" in result
        assert "Item 2" in result
        assert "\n" in result

    def test_format_dict(self):
        """Test dict formatting."""
        result = _format_field_value({"key": "value"}, None)
        assert "key: value" in result

    def test_format_none(self):
        """Test None formatting."""
        assert _format_field_value(None, None) == ""

    def test_format_number(self):
        """Test number formatting."""
        assert _format_field_value(42, None) == "42"
        assert _format_field_value(3.14, None) == "3.14"
