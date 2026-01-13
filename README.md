# Medical OCR Pipeline

A production-grade FastAPI-based OCR → LLM → PDF Filling Pipeline for medical forms.

## Features

- **Multi-format support**: PDF (single/multi-page, scanned), JPEG, PNG, HEIC
- **Dual OCR backends**: Mistral Document AI (primary), Gemini Vision (secondary)
- **Dual LLM backends**: Gemini and OpenAI GPT-4 for structured parsing
- **AcroForm filling**: Automatically fills PDF form fields with extracted data
- **Confidence scoring**: Per-field and overall confidence scores
- **HIPAA-ready**: PHI-safe logging, abstracted API interfaces

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- Poppler (for PDF to image conversion)

```bash
# macOS
brew install poppler

# Ubuntu/Debian
sudo apt-get install poppler-utils
```

### Installation

```bash
# Clone and navigate to project
cd ocr-app

# Install dependencies
uv sync

# Copy environment template
cp .env.example .env
```

### Configuration

Edit `.env` with your API keys:

```env
# Required for Mistral OCR (primary)
MISTRAL_API_KEY=your_mistral_key

# Required for Gemini OCR/LLM
GEMINI_API_KEY=your_gemini_key

# Required for OpenAI LLM (optional)
OPENAI_API_KEY=your_openai_key
```

### Running the Server

```bash
# Development mode
uv run uvicorn src.main:app --reload --port 8000

# Production mode
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### API Usage

**Process a document:**

```bash
curl -X POST http://localhost:8000/api/v1/process \
  -F "file=@medical_form.pdf" \
  -F "ocr_provider=mistral" \
  -F "llm_provider=gemini"
```

**Response:**

```json
{
  "extracted_data": {
    "patient_first_name": "John",
    "patient_last_name": "Doe",
    "date_of_birth": "1990-01-15",
    "has_diabetes": true,
    ...
  },
  "filled_pdf_base64": "JVBERi0xLjQK...",
  "confidence_score": 0.87,
  "ocr_confidence": 0.90,
  "llm_confidence": 0.82,
  "field_confidences": {
    "patient_first_name": 0.95,
    "date_of_birth": 0.88,
    ...
  },
  "processing_time_ms": 3420
}
```

**Check available providers:**

```bash
curl http://localhost:8000/api/v1/providers
```

## Project Structure

```
ocr-app/
├── src/
│   ├── main.py              # FastAPI app entry
│   ├── config.py            # Environment & settings
│   ├── api/                 # API routes & models
│   ├── ocr/                 # OCR provider implementations
│   │   ├── base.py          # BaseOCR interface
│   │   ├── mistral_ocr.py   # Mistral Document AI
│   │   ├── gemini_ocr.py    # Gemini Vision
│   │   └── google_docai_stub.py  # Placeholder
│   ├── llm/                 # LLM parser implementations
│   │   ├── base.py          # BaseLLM interface
│   │   ├── gemini_llm.py    # Gemini parser
│   │   └── openai_llm.py    # OpenAI GPT-4 parser
│   ├── pdf/                 # PDF processing
│   │   ├── converter.py     # PDF/image → images
│   │   └── filler.py        # AcroForm filling
│   ├── pipeline/            # Pipeline orchestration
│   └── utils/               # Utilities (logging, etc.)
├── tests/                   # Test suite
├── docs/                    # Documentation
└── pyproject.toml           # Project configuration
```

## OCR Providers

| Provider | Status | Notes |
|----------|--------|-------|
| Mistral Document AI | ✅ Active | Primary, uses pixtral-12b |
| Gemini Vision | ✅ Active | Secondary, uses gemini-2.0-flash |
| Google Document AI | 🔲 Placeholder | Future HIPAA-compliant option |

## LLM Providers

| Provider | Status | Notes |
|----------|--------|-------|
| Gemini | ✅ Active | Default, JSON mode |
| OpenAI GPT-4 | ✅ Active | Alternative, JSON mode |

## Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html
```

## Railway Deployment

1. Create a new Railway project
2. Add environment variables from `.env.example`
3. Set start command:
   ```
   uvicorn src.main:app --host 0.0.0.0 --port $PORT
   ```

## HIPAA Compliance Notes

See [docs/hipaa_notes.md](docs/hipaa_notes.md) for detailed HIPAA deployment guidance.

**Current security measures:**
- PHI-safe logging (automatic redaction)
- No PHI stored to disk
- HTTPS API calls to all providers
- Abstracted provider interfaces for easy endpoint swapping

**For full HIPAA compliance, additional steps required:**
- Sign BAAs with API providers
- Enable encryption at rest
- Implement audit logging
- Use VPC/private networking

## License

Private - All rights reserved.
