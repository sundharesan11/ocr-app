"""Integration tests for the pipeline."""

import pytest


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_check(self, client):
        """Test health endpoint returns healthy status."""
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "environment" in data


class TestProvidersEndpoint:
    """Tests for the providers endpoint."""

    def test_list_providers(self, client):
        """Test providers endpoint returns available providers."""
        response = client.get("/api/v1/providers")

        assert response.status_code == 200
        data = response.json()

        assert "ocr_providers" in data
        assert "llm_providers" in data

        # Check OCR providers structure
        ocr_ids = [p["id"] for p in data["ocr_providers"]]
        assert "mistral" in ocr_ids
        assert "gemini" in ocr_ids
        assert "google_docai" in ocr_ids

        # Check LLM providers structure
        llm_ids = [p["id"] for p in data["llm_providers"]]
        assert "gemini" in llm_ids
        assert "openai" in llm_ids


class TestProcessEndpoint:
    """Tests for the process endpoint."""

    def test_process_rejects_no_file(self, client):
        """Test that process endpoint rejects requests without file."""
        response = client.post("/api/v1/process")

        assert response.status_code == 422  # Validation error

    def test_process_rejects_unsupported_format(self, client):
        """Test that process endpoint rejects unsupported file formats."""
        response = client.post(
            "/api/v1/process",
            files={"file": ("test.txt", b"Hello World", "text/plain")},
        )

        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]

    def test_process_rejects_empty_file(self, client):
        """Test that process endpoint rejects empty files."""
        response = client.post(
            "/api/v1/process",
            files={"file": ("test.pdf", b"", "application/pdf")},
        )

        assert response.status_code == 400
        assert "Empty file" in response.json()["detail"]

    @pytest.mark.skip(reason="Requires API keys for full integration test")
    def test_process_valid_image(self, client, sample_image_bytes):
        """Test processing a valid image (requires API keys)."""
        response = client.post(
            "/api/v1/process",
            files={"file": ("test.png", sample_image_bytes, "image/png")},
            data={"ocr_provider": "gemini", "llm_provider": "gemini"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "extracted_data" in data
        assert "confidence_score" in data


class TestRootEndpoint:
    """Tests for the root endpoint."""

    def test_root_returns_info(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "docs" in data
