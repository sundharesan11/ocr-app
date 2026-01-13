"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src import __version__
from src.api.router import router
from src.config import get_settings
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Static files directory
STATIC_DIR = Path(__file__).parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    settings = get_settings()
    logger.info(
        "Starting Medical OCR Pipeline",
        version=__version__,
        environment=settings.environment.value,
    )

    # Log configured providers
    providers_status = {
        "mistral_ocr": "configured" if settings.mistral_api_key else "not configured",
        "gemini": "configured" if settings.gemini_api_key else "not configured",
        "openai": "configured" if settings.openai_api_key else "not configured",
    }
    logger.info("Provider status", **providers_status)

    yield

    # Shutdown
    logger.info("Shutting down Medical OCR Pipeline")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    settings = get_settings()

    app = FastAPI(
        title="Medical OCR Pipeline",
        description="""
        FastAPI-based OCR → LLM → PDF Filling Pipeline for medical forms.

        ## Features

        - **Multi-format support**: PDF, JPEG, PNG, HEIC
        - **Dual OCR backends**: Mistral Document AI and Gemini Vision
        - **Dual LLM backends**: Gemini and OpenAI GPT-4
        - **AcroForm filling**: Automatically fills PDF form fields
        - **Confidence scoring**: Per-field and overall confidence scores
        - **HIPAA-ready**: PHI-safe logging, abstracted API interfaces

        ## Usage

        1. Upload a medical form (PDF or image)
        2. Select OCR and LLM providers
        3. Receive structured JSON data and filled PDF
        """,
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if not settings.is_production else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API router
    app.include_router(router)

    # Serve static files
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # Root serves the UI
    @app.get("/", include_in_schema=False)
    async def root():
        """Serve the main UI."""
        index_file = STATIC_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {
            "message": "Medical OCR Pipeline API",
            "version": __version__,
            "docs": "/docs",
            "health": "/api/v1/health",
        }

    return app


# Create app instance
app = create_app()
