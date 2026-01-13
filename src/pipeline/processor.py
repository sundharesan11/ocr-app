"""Pipeline processor - Orchestrates OCR → LLM → PDF filling."""

import time
from dataclasses import dataclass, field
from typing import Any

from src.config import LLMProvider, OCRProvider
from src.llm import create_llm_provider
from src.llm.vision_extractor import VisionPositionExtractor, convert_positions_to_points
from src.ocr import create_ocr_provider
from src.pdf.converter import convert_to_images
from src.pdf.filler import fill_pdf_form, get_form_fields
from src.pdf.overlay import FieldPosition, overlay_text_on_pdf
from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ProcessResult:
    """Result from pipeline processing.

    Attributes:
        extracted_data: Structured data extracted from the document
        filled_pdf: Filled PDF as bytes (None if input wasn't a PDF)
        ocr_confidence: Confidence score from OCR
        llm_confidence: Confidence score from LLM parsing
        field_confidences: Per-field confidence scores
        processing_time_ms: Total processing time in milliseconds
        metadata: Additional processing metadata
    """

    extracted_data: dict[str, Any]
    filled_pdf: bytes | None = None
    ocr_confidence: float = 0.0
    llm_confidence: float = 0.0
    field_confidences: dict[str, float] = field(default_factory=dict)
    processing_time_ms: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def overall_confidence(self) -> float:
        """Calculate overall confidence as weighted average."""
        # Weight OCR higher as it's the foundation
        return (self.ocr_confidence * 0.6) + (self.llm_confidence * 0.4)


class PipelineError(Exception):
    """Exception raised when pipeline processing fails."""

    def __init__(self, message: str, stage: str, details: dict[str, Any] | None = None):
        self.message = message
        self.stage = stage
        self.details = details or {}
        super().__init__(f"[{stage}] {message}")


class PipelineProcessor:
    """Orchestrates the OCR → LLM → PDF filling pipeline.

    Usage:
        processor = PipelineProcessor()
        result = await processor.process(
            file_content=pdf_bytes,
            filename="form.pdf",
            ocr_provider=OCRProvider.MISTRAL,
            llm_provider=LLMProvider.GEMINI,
        )

    The processor:
    1. Converts input file to images
    2. Extracts text using selected OCR provider
    3. Parses text into structured JSON using selected LLM
    4. Fills PDF form fields with extracted data (if input is PDF)
    """

    async def process(
        self,
        file_content: bytes,
        filename: str,
        ocr_provider: OCRProvider = OCRProvider.MISTRAL,
        llm_provider: LLMProvider = LLMProvider.GEMINI,
        field_hints: list[str] | None = None,
        template_pdf: bytes | None = None,
    ) -> ProcessResult:
        """Process a document through the full pipeline.

        Args:
            file_content: Raw file bytes (PDF or image) - the source document to OCR
            filename: Original filename (for format detection)
            ocr_provider: OCR provider to use (toggle selection)
            llm_provider: LLM provider to use (toggle selection)
            field_hints: Optional list of expected field names
            template_pdf: Optional blank PDF template with AcroForm fields to fill.
                         If provided, extracted data will be filled into this template
                         instead of the source document.

        Returns:
            ProcessResult with extracted data and filled PDF

        Raises:
            PipelineError: If any stage of processing fails
        """
        start_time = time.time()

        logger.info(
            "Starting pipeline processing",
            filename=filename,
            ocr_provider=ocr_provider.value,
            llm_provider=llm_provider.value,
            file_size=len(file_content),
            has_template=template_pdf is not None,
        )

        metadata: dict[str, Any] = {
            "ocr_provider": ocr_provider.value,
            "llm_provider": llm_provider.value,
            "filename": filename,
            "template_mode": template_pdf is not None,
        }

        try:
            # Stage 1: Convert to images
            logger.info("Stage 1: Converting file to images")
            images = convert_to_images(file_content, filename)
            metadata["page_count"] = len(images)
            logger.info("Conversion complete", page_count=len(images))

            # Stage 2: OCR extraction
            logger.info("Stage 2: Extracting text with OCR")
            ocr = create_ocr_provider(ocr_provider)
            ocr_result = await ocr.extract_text(images)
            metadata["ocr_model"] = ocr_result.metadata.get("model", "unknown")
            logger.info("OCR complete", confidence=f"{ocr_result.confidence:.2f}")

            # Stage 3: LLM parsing
            logger.info("Stage 3: Parsing text with LLM")
            llm = create_llm_provider(llm_provider)
            parse_result = await llm.parse_to_json(ocr_result.text, field_hints)
            metadata["llm_model"] = parse_result.metadata.get("model", "unknown")
            logger.info(
                "Parsing complete",
                field_count=len(parse_result.data),
                confidence=f"{parse_result.overall_confidence:.2f}",
            )

            # Stage 4: Fill PDF form
            filled_pdf = None

            # Determine which PDF to fill: template (if provided) or source (if PDF)
            pdf_to_fill = (
                template_pdf
                if template_pdf
                else (file_content if filename.lower().endswith(".pdf") else None)
            )

            if pdf_to_fill:
                fill_type = "template" if template_pdf else "source"
                logger.info(f"Stage 4: Filling PDF form ({fill_type})")

                # First, try AcroForm filling
                try:
                    form_fields = get_form_fields(pdf_to_fill)
                    if form_fields:
                        # PDF has AcroForm fields - use standard filling
                        logger.info(
                            f"PDF has {len(form_fields)} AcroForm fields, using field filling"
                        )
                        filled_pdf = fill_pdf_form(pdf_to_fill, parse_result.data)
                        metadata["pdf_filled"] = True
                        metadata["pdf_fill_type"] = f"{fill_type}_acroform"
                        metadata["pdf_fill_method"] = "acroform"
                        logger.info(f"PDF form filled successfully via AcroForm ({fill_type})")
                    else:
                        # No AcroForm fields - use text overlay with vision extraction
                        logger.info("PDF has no AcroForm fields, using text overlay")
                        metadata["pdf_fill_method"] = "overlay"

                        # Use vision extraction to get field positions
                        logger.info("Extracting field positions with vision...")
                        vision_extractor = VisionPositionExtractor()
                        position_result = await vision_extractor.extract_with_positions(images)

                        if position_result.fields:
                            # Convert percentage positions to PDF points
                            field_positions = convert_positions_to_points(
                                position_result.fields,
                                position_result.page_dimensions,
                            )

                            # Create FieldPosition objects for overlay
                            overlay_fields = [
                                FieldPosition(
                                    name=fp["name"],
                                    value=str(fp["value"]),
                                    x=fp["x"],
                                    y=fp["y"],
                                    width=fp.get("width"),
                                    height=fp.get("height"),
                                    page=fp.get("page", 0),
                                    font_size=fp.get("font_size", 10),
                                )
                                for fp in field_positions
                                if fp.get("value")
                            ]

                            filled_pdf = overlay_text_on_pdf(pdf_to_fill, overlay_fields)
                            metadata["pdf_filled"] = True
                            metadata["pdf_fill_type"] = f"{fill_type}_overlay"
                            metadata["overlay_field_count"] = len(overlay_fields)
                            logger.info(
                                f"PDF filled via text overlay ({len(overlay_fields)} fields)"
                            )
                        else:
                            logger.warning("No field positions extracted, cannot overlay")
                            metadata["pdf_filled"] = False
                            metadata["pdf_fill_error"] = "No field positions detected"

                except Exception as e:
                    logger.warning(f"Could not fill PDF form: {e}")
                    metadata["pdf_filled"] = False
                    metadata["pdf_fill_error"] = str(e)
            else:
                metadata["pdf_filled"] = False
                logger.info("Skipping PDF filling (no template provided and input is not PDF)")

            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)

            result = ProcessResult(
                extracted_data=parse_result.data,
                filled_pdf=filled_pdf,
                ocr_confidence=ocr_result.confidence,
                llm_confidence=parse_result.overall_confidence,
                field_confidences=parse_result.field_confidences,
                processing_time_ms=processing_time_ms,
                metadata=metadata,
            )

            logger.info(
                "Pipeline processing complete",
                overall_confidence=f"{result.overall_confidence:.2f}",
                processing_time_ms=processing_time_ms,
            )

            return result

        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            logger.error("Pipeline processing failed", error=str(e), stage="unknown")

            # Determine which stage failed
            stage = "unknown"
            if "convert" in str(e).lower():
                stage = "conversion"
            elif "ocr" in str(e).lower():
                stage = "ocr"
            elif "parse" in str(e).lower() or "llm" in str(e).lower():
                stage = "parsing"
            elif "fill" in str(e).lower() or "pdf" in str(e).lower():
                stage = "pdf_filling"

            raise PipelineError(
                str(e),
                stage,
                {"processing_time_ms": processing_time_ms, **metadata},
            ) from e
