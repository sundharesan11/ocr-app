"""Factory for creating LLM provider instances."""

from src.config import LLMProvider, get_settings
from src.llm.base import BaseLLM
from src.llm.gemini_llm import GeminiLLM
from src.llm.openai_llm import OpenAILLM


def create_llm_provider(provider: LLMProvider | str) -> BaseLLM:
    """Create an LLM provider instance based on the provider type.

    Args:
        provider: LLM provider type (enum or string)

    Returns:
        Configured LLM provider instance

    Raises:
        ValueError: If provider type is unknown or not configured

    Example:
        llm = create_llm_provider(LLMProvider.GEMINI)
        result = await llm.parse_to_json(ocr_text)
    """
    settings = get_settings()

    # Convert string to enum if needed
    if isinstance(provider, str):
        provider = LLMProvider(provider.lower())

    # Validate the provider has required configuration
    settings.validate_llm_provider(provider)

    if provider == LLMProvider.GEMINI:
        return GeminiLLM(api_key=settings.gemini_api_key)
    elif provider == LLMProvider.OPENAI:
        return OpenAILLM(api_key=settings.openai_api_key)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
