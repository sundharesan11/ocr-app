"""API router - FastAPI endpoints."""

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from src import __version__
from src.api.models import ErrorResponse, HealthResponse, ProcessResponse
from src.config import LLMProvider, OCRProvider, get_settings
from src.ocr.mistral_document_ocr import MistralDocumentOCR
from src.pdf.generator import generate_pdf
from src.pdf.markdown_to_pdf import ocr_text_to_pdf
from src.pipeline.processor import PipelineError, PipelineProcessor
from src.pipeline.simple_processor import SimplePipeline
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Medical OCR Pipeline"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Check if the API is healthy and running",
)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    settings = get_settings()
    return HealthResponse(
        status="healthy",
        version=__version__,
        environment=settings.environment.value,
    )


@router.post(
    "/process",
    response_model=ProcessResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Processing error"},
    },
    summary="Process Document",
    description="""
    Process a medical form document through OCR and LLM parsing.

    **Supported formats for source file:**
    - PDF (single or multi-page, including scanned)
    - JPEG/JPG
    - PNG
    - HEIC (iOS photos)

    **Template mode:**
    Optionally provide a blank PDF template with AcroForm fields.
    The extracted data will be filled into the template instead of the source.

    **Returns:**
    - Extracted structured data as JSON
    - Filled PDF (from template if provided, or source if PDF)
    - Confidence scores for OCR, LLM, and individual fields
    """,
)
async def process_document(
    file: UploadFile = File(
        ..., description="Source document to extract data from (scanned form, image, or PDF)"
    ),
    template_pdf: UploadFile | None = File(
        default=None,
        description="Optional: Blank PDF template with AcroForm fields to fill with extracted data",
    ),
    ocr_provider: OCRProvider = Form(
        default=OCRProvider.MISTRAL,
        description="OCR provider: mistral, gemini, or google_docai",
    ),
    llm_provider: LLMProvider = Form(
        default=LLMProvider.GEMINI,
        description="LLM provider: gemini or openai",
    ),
) -> ProcessResponse:
    """Process a document through the OCR → LLM → PDF filling pipeline.

    Args:
        file: Uploaded source document to extract data from
        template_pdf: Optional blank PDF template to fill with extracted data
        ocr_provider: OCR provider to use (toggle)
        llm_provider: LLM provider to use (toggle)

    Returns:
        ProcessResponse with extracted data and confidence scores

    Raises:
        HTTPException: On validation or processing errors
    """
    # Validate source file
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    # Validate source file extension
    allowed_extensions = {".pdf", ".jpg", ".jpeg", ".png", ".heic", ".heif"}
    file_ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Allowed: {', '.join(allowed_extensions)}",
        )

    # Read source file content
    try:
        file_content = await file.read()
    except Exception as e:
        logger.error("Failed to read uploaded file", error=str(e))
        raise HTTPException(status_code=400, detail="Failed to read uploaded file")

    if not file_content:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    # Read template PDF if provided
    template_content: bytes | None = None
    if template_pdf and template_pdf.filename:
        if not template_pdf.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail="Template must be a PDF file with AcroForm fields",
            )
        try:
            template_content = await template_pdf.read()
            if not template_content:
                raise HTTPException(status_code=400, detail="Empty template file")
            logger.info("Template PDF provided", template_filename=template_pdf.filename)
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to read template file", error=str(e))
            raise HTTPException(status_code=400, detail="Failed to read template file")

    # Validate provider configuration
    settings = get_settings()
    try:
        settings.validate_ocr_provider(ocr_provider)
        settings.validate_llm_provider(llm_provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Process document
    logger.info(
        "Processing document",
        filename=file.filename,
        file_size=len(file_content),
        has_template=template_content is not None,
        ocr_provider=ocr_provider.value,
        llm_provider=llm_provider.value,
    )

    try:
        processor = PipelineProcessor()
        result = await processor.process(
            file_content=file_content,
            filename=file.filename,
            ocr_provider=ocr_provider,
            llm_provider=llm_provider,
            template_pdf=template_content,
        )

        return ProcessResponse.from_process_result(result)

    except PipelineError as e:
        logger.error("Pipeline processing failed", error=str(e), stage=e.stage)
        raise HTTPException(
            status_code=500,
            detail=f"Processing failed at {e.stage} stage: {e.message}",
        )
    except Exception as e:
        logger.exception("Unexpected error during processing")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}",
        )


@router.get(
    "/providers",
    summary="List Available Providers",
    description="Get list of available OCR and LLM providers",
)
async def list_providers() -> dict:
    """List available OCR and LLM providers."""
    settings = get_settings()

    return {
        "ocr_providers": [
            {
                "id": OCRProvider.MISTRAL.value,
                "name": "Mistral Document AI",
                "available": bool(settings.mistral_api_key),
            },
            {
                "id": OCRProvider.GEMINI.value,
                "name": "Gemini Vision",
                "available": bool(settings.gemini_api_key),
            },
            {
                "id": OCRProvider.GOOGLE_DOCAI.value,
                "name": "Google Document AI",
                "available": False,  # Placeholder
                "note": "Coming soon - HIPAA-compliant option",
            },
        ],
        "llm_providers": [
            {
                "id": LLMProvider.GEMINI.value,
                "name": "Gemini",
                "available": bool(settings.gemini_api_key),
            },
            {
                "id": LLMProvider.OPENAI.value,
                "name": "OpenAI GPT-4",
                "available": bool(settings.openai_api_key),
            },
        ],
    }


@router.post(
    "/process/download",
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Filled PDF file download",
        },
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Processing error"},
    },
    summary="Process and Download PDF",
    description="""
    Process a document and download the filled PDF directly.

    Same as /process but returns the filled PDF as a downloadable file
    instead of base64-encoded JSON.
    """,
)
async def process_and_download(
    file: UploadFile = File(..., description="Source document to extract data from"),
    template_pdf: UploadFile | None = File(
        default=None,
        description="Optional: Blank PDF template to fill with extracted data",
    ),
    ocr_provider: OCRProvider = Form(
        default=OCRProvider.MISTRAL,
        description="OCR provider: mistral, gemini, or google_docai",
    ),
    llm_provider: LLMProvider = Form(
        default=LLMProvider.GEMINI,
        description="LLM provider: gemini or openai",
    ),
) -> Response:
    """Process document and return filled PDF as download."""
    # Validate source file
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    allowed_extensions = {".pdf", ".jpg", ".jpeg", ".png", ".heic", ".heif"}
    file_ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}",
        )

    # Read source file
    file_content = await file.read()
    if not file_content:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    # Read template if provided
    template_content: bytes | None = None
    if template_pdf and template_pdf.filename:
        if not template_pdf.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Template must be a PDF file")
        template_content = await template_pdf.read()

    # Validate providers
    settings = get_settings()
    settings.validate_ocr_provider(ocr_provider)
    settings.validate_llm_provider(llm_provider)

    logger.info(
        "Processing document for download",
        filename=file.filename,
        has_template=template_content is not None,
    )

    try:
        processor = PipelineProcessor()
        result = await processor.process(
            file_content=file_content,
            filename=file.filename,
            ocr_provider=ocr_provider,
            llm_provider=llm_provider,
            template_pdf=template_content,
        )

        if not result.filled_pdf:
            raise HTTPException(
                status_code=400,
                detail="No PDF was generated. Provide a template PDF or a source PDF.",
            )

        # Generate output filename
        base_name = file.filename.rsplit(".", 1)[0] if "." in file.filename else file.filename
        output_filename = f"{base_name}_filled.pdf"

        logger.info("Returning filled PDF", filename=output_filename)

        return Response(
            content=result.filled_pdf,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{output_filename}"',
            },
        )

    except PipelineError as e:
        logger.error("Pipeline failed", error=str(e), stage=e.stage)
        raise HTTPException(status_code=500, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/process/fast",
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Filled PDF file download",
        },
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Processing error"},
    },
    summary="Fast Process and Download (Mistral OCR API)",
    description="""
    **FAST VERSION** - Uses Mistral's dedicated OCR API for much faster processing.

    Single API call instead of page-by-page processing.
    Recommended for multi-page documents.

    - Returns filled PDF as direct download
    - 10-30 seconds for 14 pages (vs 7+ minutes with old endpoint)
    """,
)
async def process_fast(
    file: UploadFile = File(..., description="Source document (PDF or image)"),
    template_pdf: UploadFile | None = File(
        default=None,
        description="Blank PDF template to fill with extracted data",
    ),
) -> Response:
    """Fast document processing using Mistral's dedicated OCR API."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    # Read source file
    file_content = await file.read()
    if not file_content:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    # Read template if provided
    template_content: bytes | None = None
    if template_pdf and template_pdf.filename:
        template_content = await template_pdf.read()

    logger.info(
        "Fast processing",
        filename=file.filename,
        file_size=len(file_content),
        has_template=template_content is not None,
    )

    try:
        pipeline = SimplePipeline()
        result = await pipeline.process(
            source_document=file_content,
            source_filename=file.filename,
            template_pdf=template_content,
        )

        if not result.filled_pdf:
            # Return JSON with extracted data if no PDF generated
            return Response(
                content=str(result.extracted_data).encode(),
                media_type="application/json",
                headers={
                    "X-Extracted-Fields": str(result.field_count),
                    "X-Processing-Time-Ms": str(result.processing_time_ms),
                },
            )

        # Generate output filename
        base_name = file.filename.rsplit(".", 1)[0] if "." in file.filename else file.filename
        output_filename = f"{base_name}_filled.pdf"

        logger.info(
            "Fast processing complete",
            filename=output_filename,
            processing_time_ms=result.processing_time_ms,
        )

        return Response(
            content=result.filled_pdf,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{output_filename}"',
                "X-Processing-Time-Ms": str(result.processing_time_ms),
                "X-Field-Count": str(result.field_count),
            },
        )

    except Exception as e:
        logger.exception("Fast processing failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/process/generate",
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Generated structured PDF",
        },
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Processing error"},
    },
    summary="Extract & Generate PDF",
    description="""
    **V1 SIMPLE FLOW** - Extract data and generate a clean, structured PDF.

    No template required. No overlay positioning needed.

    The output is a professionally formatted PDF with:
    - All extracted fields organized by section
    - Patient Info, Medical History, Symptoms, etc.
    - Clean table-based layout

    **Best for:** Quick digitization of handwritten forms.
    """,
)
async def process_and_generate(
    file: UploadFile = File(..., description="Scanned form (PDF or image)"),
) -> Response:
    """Extract data from form and generate a clean structured PDF."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    # Read source file
    file_content = await file.read()
    if not file_content:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    logger.info(
        "Generate PDF request",
        filename=file.filename,
        file_size=len(file_content),
    )

    try:
        # Step 1: Extract document using Mistral's basic OCR (preserves structure)
        ocr = MistralDocumentOCR()
        ocr_result = await ocr.process_with_basic_ocr(
            file_content=file_content,
            filename=file.filename,
        )

        logger.info(
            "OCR complete",
            page_count=ocr_result.page_count,
            text_length=len(ocr_result.raw_text),
        )

        if not ocr_result.raw_text.strip():
            raise HTTPException(
                status_code=400,
                detail="No content could be extracted from the document",
            )

        # Step 2: Convert markdown to PDF (preserves original structure)
        pdf_bytes = ocr_text_to_pdf(
            raw_text=ocr_result.raw_text,
            title="Medical Intake Form - Digitized",
        )

        # Generate output filename
        base_name = file.filename.rsplit(".", 1)[0] if "." in file.filename else file.filename
        output_filename = f"{base_name}_digitized.pdf"

        logger.info(
            "PDF generation complete",
            filename=output_filename,
            page_count=ocr_result.page_count,
        )

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{output_filename}"',
                "X-Page-Count": str(ocr_result.page_count),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("PDF generation failed")
        raise HTTPException(status_code=500, detail=str(e))
