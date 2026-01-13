"""Application configuration using pydantic-settings."""

from enum import Enum
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Application environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class OCRProvider(str, Enum):
    """Available OCR providers."""

    MISTRAL = "mistral"
    GEMINI = "gemini"
    GOOGLE_DOCAI = "google_docai"


class LLMProvider(str, Enum):
    """Available LLM providers for parsing."""

    GEMINI = "gemini"
    OPENAI = "openai"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    environment: Environment = Environment.DEVELOPMENT
    log_level: str = "INFO"

    # OCR Providers
    mistral_api_key: str = ""
    gemini_api_key: str = ""
    google_docai_project_id: str = ""
    google_docai_location: str = "us"
    google_docai_processor_id: str = ""

    # LLM Providers
    openai_api_key: str = ""
    # Note: gemini_api_key is shared with OCR

    # Default providers
    default_ocr_provider: OCRProvider = OCRProvider.MISTRAL
    default_llm_provider: LLMProvider = LLMProvider.GEMINI

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == Environment.PRODUCTION

    def validate_ocr_provider(self, provider: OCRProvider) -> None:
        """Validate that the required API keys are set for the OCR provider."""
        if provider == OCRProvider.MISTRAL and not self.mistral_api_key:
            raise ValueError("MISTRAL_API_KEY is required for Mistral OCR")
        if provider == OCRProvider.GEMINI and not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required for Gemini OCR")
        if provider == OCRProvider.GOOGLE_DOCAI:
            if not self.google_docai_project_id or not self.google_docai_processor_id:
                raise ValueError(
                    "GOOGLE_DOCAI_PROJECT_ID and GOOGLE_DOCAI_PROCESSOR_ID are required"
                )

    def validate_llm_provider(self, provider: LLMProvider) -> None:
        """Validate that the required API keys are set for the LLM provider."""
        if provider == LLMProvider.GEMINI and not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required for Gemini LLM")
        if provider == LLMProvider.OPENAI and not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI LLM")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
