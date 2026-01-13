"""Simplified pipeline using Mistral's dedicated Document OCR API.

This pipeline is much simpler:
1. Upload document to Mistral OCR API
2. Get structured data with positions in single call
3. Overlay on template PDF

No need for: PDF-to-image conversion, page-by-page OCR, separate LLM parsing.
"""

import time
from dataclasses import dataclass, field
from typing import Any

from src.ocr.mistral_document_ocr import MistralDocumentOCR, MistralOCRResult
from src.pdf.overlay import FieldPosition, overlay_text_on_pdf
from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SimplePipelineResult:
    """Result from simplified pipeline."""

    extracted_data: dict[str, Any]
    filled_pdf: bytes | None = None
    raw_text: str = ""
    confidence: float = 0.0
    processing_time_ms: int = 0
    page_count: int = 0
    field_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class SimplePipeline:
    """Simplified OCR → Fill pipeline using Mistral Document OCR.

    Usage:
        pipeline = SimplePipeline()
        result = await pipeline.process(
            source_document=source_bytes,
            source_filename="filled_form.pdf",
            template_pdf=blank_template_bytes,
        )
    """

    def __init__(self):
        """Initialize the pipeline."""
        self._ocr = MistralDocumentOCR()

    async def process(
        self,
        source_document: bytes,
        source_filename: str,
        template_pdf: bytes | None = None,
    ) -> SimplePipelineResult:
        """Process a document through the simplified pipeline.

        Args:
            source_document: PDF or image to extract data from
            source_filename: Filename of source document
            template_pdf: Optional blank PDF to fill with extracted data

        Returns:
            SimplePipelineResult with extracted data and filled PDF
        """
        start_time = time.time()

        logger.info(
            "Starting simplified pipeline",
            filename=source_filename,
            file_size=len(source_document),
            has_template=template_pdf is not None,
        )

        metadata: dict[str, Any] = {
            "filename": source_filename,
            "pipeline": "simplified",
        }

        try:
            # Step 1: Process with Mistral OCR API (single call!)
            logger.info("Step 1: Calling Mistral OCR API")
            ocr_result = await self._ocr.process_document(
                file_content=source_document,
                filename=source_filename,
            )

            metadata["ocr_model"] = "mistral-ocr-latest"
            metadata["page_count"] = ocr_result.page_count
            metadata["field_count"] = len(ocr_result.fields_with_positions)

            logger.info(
                "OCR complete",
                page_count=ocr_result.page_count,
                field_count=len(ocr_result.fields_with_positions),
            )

            # Step 2: Fill template PDF if provided
            filled_pdf = None
            if template_pdf and ocr_result.fields_with_positions:
                logger.info("Step 2: Filling template PDF with extracted data")

                # Convert field positions to FieldPosition objects
                # PDF points: 612 x 792 for US Letter
                pdf_width = 612
                pdf_height = 792

                overlay_fields = []
                for fp in ocr_result.fields_with_positions:
                    if not fp.get("value"):
                        continue

                    overlay_fields.append(
                        FieldPosition(
                            name=fp["name"],
                            value=str(fp["value"]),
                            x=(fp["x"] / 100) * pdf_width,
                            y=(fp["y"] / 100) * pdf_height,
                            width=(fp.get("width", 20) / 100) * pdf_width,
                            height=(fp.get("height", 3) / 100) * pdf_height,
                            page=fp.get("page", 0),
                            font_size=10,
                        )
                    )

                if overlay_fields:
                    filled_pdf = overlay_text_on_pdf(template_pdf, overlay_fields)
                    metadata["pdf_filled"] = True
                    metadata["overlay_field_count"] = len(overlay_fields)
                    logger.info(f"Template filled with {len(overlay_fields)} fields")
                else:
                    metadata["pdf_filled"] = False
                    logger.warning("No fields with values to overlay")

            elif template_pdf:
                metadata["pdf_filled"] = False
                logger.warning("No field positions extracted, cannot fill template")
            else:
                metadata["pdf_filled"] = False
                logger.info("No template provided, skipping PDF filling")

            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)

            result = SimplePipelineResult(
                extracted_data=ocr_result.extracted_data,
                filled_pdf=filled_pdf,
                raw_text=ocr_result.raw_text,
                confidence=ocr_result.confidence,
                processing_time_ms=processing_time_ms,
                page_count=ocr_result.page_count,
                field_count=len(ocr_result.fields_with_positions),
                metadata=metadata,
            )

            logger.info(
                "Pipeline complete",
                processing_time_ms=processing_time_ms,
            )

            return result

        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            logger.error("Pipeline failed", error=str(e))
            raise RuntimeError(f"Pipeline failed: {e}") from e
