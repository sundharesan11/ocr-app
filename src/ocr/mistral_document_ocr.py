"""Mistral Document OCR implementation using the dedicated OCR API.

This uses Mistral's `client.ocr.process()` API which:
- Processes entire PDFs in a single call
- Extracts structured data with bounding boxes
- Much faster than page-by-page vision calls

Reference: https://docs.mistral.ai/capabilities/document_ai/annotations
"""

import base64
from dataclasses import dataclass
from typing import Any

import fitz  # PyMuPDF
from mistralai import Mistral
from pydantic import BaseModel, Field

from src.config import get_settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class FormField(BaseModel):
    """A single form field with its value and position."""

    field_name: str = Field(description="Name of the form field in snake_case")
    field_value: str = Field(description="The handwritten or filled value")
    x_percent: float = Field(description="X position as percentage 0-100 from left")
    y_percent: float = Field(description="Y position as percentage 0-100 from top")
    page_number: int = Field(description="Page number starting from 0")


class FormExtractionResult(BaseModel):
    """Result of extracting all fields from a form."""

    fields: list[FormField] = Field(description="List of all extracted form fields")


@dataclass
class MistralOCRResult:
    """Result from Mistral OCR processing."""

    extracted_data: dict[str, Any]
    fields_with_positions: list[dict]
    raw_text: str
    confidence: float
    page_count: int
    metadata: dict[str, Any]


class MistralDocumentOCR:
    """OCR implementation using Mistral's dedicated OCR API.

    This processes entire documents in a single API call, extracting
    structured data with bounding box positions for text overlay.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Mistral OCR client.

        Args:
            api_key: Mistral API key. If None, reads from environment.
        """
        settings = get_settings()
        self._api_key = api_key or settings.mistral_api_key
        if not self._api_key:
            raise ValueError("Mistral API key is required")
        self._client = Mistral(api_key=self._api_key)
        logger.info("Initialized Mistral Document OCR client")

    async def process_document(
        self,
        file_content: bytes,
        filename: str,
    ) -> MistralOCRResult:
        """Process a document using Mistral OCR API.

        For documents over 8 pages, automatically splits into chunks.

        Args:
            file_content: Raw PDF or image bytes
            filename: Original filename

        Returns:
            MistralOCRResult with extracted data and positions
        """
        logger.info("Starting Mistral OCR processing", filename=filename)

        # Check if PDF and split if needed
        if filename.lower().endswith(".pdf"):
            try:
                import fitz  # PyMuPDF

                doc = fitz.open(stream=file_content, filetype="pdf")
                page_count = len(doc)

                if page_count > 8:
                    logger.info(f"PDF has {page_count} pages, processing in chunks of 8")
                    return await self._process_chunked_pdf(doc, filename)

                doc.close()
            except Exception as e:
                logger.warning(f"Could not check PDF page count: {e}")

        # Process normally for ≤8 pages or non-PDFs
        return await self._process_single_document(file_content, filename)

    async def _process_chunked_pdf(self, doc, filename: str) -> MistralOCRResult:
        """Process a large PDF in chunks of 8 pages.

        Args:
            doc: PyMuPDF document object
            filename: Original filename

        Returns:
            Combined MistralOCRResult from all chunks
        """
        all_fields = []
        all_extracted_data = {}
        all_raw_text = []
        total_pages = len(doc)

        # Process in chunks of 8 pages
        for start_page in range(0, total_pages, 8):
            end_page = min(start_page + 8, total_pages)
            logger.info(f"Processing pages {start_page + 1}-{end_page} of {total_pages}")

            # Create a new PDF with just this chunk
            chunk_doc = fitz.open()
            for page_num in range(start_page, end_page):
                chunk_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)

            # Save chunk to bytes
            chunk_bytes = chunk_doc.write()
            chunk_doc.close()

            # Process this chunk
            try:
                chunk_result = await self._process_single_document(
                    chunk_bytes,
                    f"{filename}_chunk_{start_page + 1}_{end_page}.pdf",
                )

                # Adjust page numbers and combine results
                for field in chunk_result.fields_with_positions:
                    field["page"] = field.get("page", 0) + start_page
                    all_fields.append(field)

                all_extracted_data.update(chunk_result.extracted_data)
                all_raw_text.append(chunk_result.raw_text)

            except Exception as e:
                logger.warning(f"Chunk {start_page + 1}-{end_page} failed: {e}")

        doc.close()

        logger.info(
            "Chunked processing complete",
            total_pages=total_pages,
            field_count=len(all_fields),
        )

        return MistralOCRResult(
            extracted_data=all_extracted_data,
            fields_with_positions=all_fields,
            raw_text="\n\n--- Page Break ---\n\n".join(all_raw_text),
            confidence=0.9,
            page_count=total_pages,
            metadata={"model": "mistral-ocr-latest", "provider": "mistral", "chunked": True},
        )

    async def _process_single_document(
        self,
        file_content: bytes,
        filename: str,
    ) -> MistralOCRResult:
        """Process a single document (max 8 pages) using Mistral OCR API."""
        try:
            # Encode file to base64 for API
            file_b64 = base64.b64encode(file_content).decode("utf-8")

            # Determine MIME type
            if filename.lower().endswith(".pdf"):
                mime_type = "application/pdf"
                data_url = f"data:{mime_type};base64,{file_b64}"
            else:
                # Image file
                ext = filename.lower().rsplit(".", 1)[-1]
                mime_map = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png"}
                img_type = mime_map.get(ext, "jpeg")
                data_url = f"data:image/{img_type};base64,{file_b64}"

            # Import the response format helper
            from mistralai.extra import response_format_from_pydantic_model

            # Call Mistral OCR API with structured extraction
            logger.info("Calling Mistral OCR API...")
            response = await self._client.ocr.process_async(
                model="mistral-ocr-latest",
                document={"type": "document_url", "document_url": data_url},
                document_annotation_format=response_format_from_pydantic_model(
                    FormExtractionResult
                ),
                include_image_base64=False,
            )

            logger.info("Mistral OCR API response received")

            # Parse the response
            pages = response.pages if hasattr(response, "pages") else []
            page_count = len(pages)

            # Extract text from all pages
            raw_text_parts = []
            for page in pages:
                if hasattr(page, "markdown"):
                    raw_text_parts.append(page.markdown)
                elif hasattr(page, "text"):
                    raw_text_parts.append(page.text)

            raw_text = "\n\n--- Page Break ---\n\n".join(raw_text_parts)

            # Get structured annotation if available
            fields_with_positions = []
            extracted_data = {}

            # Debug: Log document_annotation
            if hasattr(response, "document_annotation"):
                logger.info(f"document_annotation type: {type(response.document_annotation)}")
                ann_str = str(response.document_annotation)[:500]
                logger.info(f"document_annotation preview: {ann_str}")

            if hasattr(response, "document_annotation") and response.document_annotation:
                annotation = response.document_annotation

                # Handle string annotation (JSON string)
                if isinstance(annotation, str):
                    import json

                    try:
                        annotation = json.loads(annotation)
                    except json.JSONDecodeError:
                        logger.warning("Could not parse annotation as JSON")

                if isinstance(annotation, dict):
                    if "fields" in annotation:
                        for field in annotation["fields"]:
                            fields_with_positions.append(
                                {
                                    "name": field.get("field_name", "unknown"),
                                    "value": field.get("field_value"),
                                    "x": field.get("x_percent", 0),
                                    "y": field.get("y_percent", 0),
                                    "width": 20,
                                    "height": 3,
                                    "page": field.get("page_number", 0),
                                }
                            )
                            if field.get("field_value"):
                                extracted_data[field["field_name"]] = field["field_value"]
                    else:
                        logger.warning(f"No 'fields' key. Keys found: {list(annotation.keys())}")
                else:
                    logger.warning(f"Annotation is type: {type(annotation)}")

            logger.info(
                "Mistral OCR complete",
                page_count=page_count,
                field_count=len(fields_with_positions),
            )

            return MistralOCRResult(
                extracted_data=extracted_data,
                fields_with_positions=fields_with_positions,
                raw_text=raw_text,
                confidence=0.9,
                page_count=page_count,
                metadata={"model": "mistral-ocr-latest", "provider": "mistral"},
            )

        except Exception as e:
            logger.error("Mistral OCR failed", error=str(e))
            raise RuntimeError(f"Mistral OCR failed: {e}") from e

    async def process_with_basic_ocr(
        self,
        file_content: bytes,
        filename: str,
    ) -> MistralOCRResult:
        """Process using basic OCR without structured extraction.

        Fallback method that just extracts text without positions.
        """
        logger.info("Using basic Mistral OCR", filename=filename)

        try:
            file_b64 = base64.b64encode(file_content).decode("utf-8")

            if filename.lower().endswith(".pdf"):
                data_url = f"data:application/pdf;base64,{file_b64}"
            else:
                ext = filename.lower().rsplit(".", 1)[-1]
                mime_map = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png"}
                img_type = mime_map.get(ext, "jpeg")
                data_url = f"data:image/{img_type};base64,{file_b64}"

            response = await self._client.ocr.process_async(
                model="mistral-ocr-latest",
                document={"type": "document_url", "document_url": data_url},
            )

            pages = response.pages if hasattr(response, "pages") else []
            page_count = len(pages)

            raw_text_parts = []
            for page in pages:
                if hasattr(page, "markdown"):
                    raw_text_parts.append(page.markdown)

            raw_text = "\n\n--- Page Break ---\n\n".join(raw_text_parts)

            logger.info("Basic OCR complete", page_count=page_count)

            return MistralOCRResult(
                extracted_data={},
                fields_with_positions=[],
                raw_text=raw_text,
                confidence=0.9,
                page_count=page_count,
                metadata={"model": "mistral-ocr-latest", "provider": "mistral"},
            )

        except Exception as e:
            logger.error("Basic OCR failed", error=str(e))
            raise RuntimeError(f"Basic Mistral OCR failed: {e}") from e
