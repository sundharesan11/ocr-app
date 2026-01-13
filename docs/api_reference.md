# API Reference

## Base URL

```
http://localhost:8000/api/v1
```

## Endpoints

### Health Check

```
GET /health
```

Check if the API is healthy and running.

**Response:**

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "environment": "development"
}
```

---

### Process Document

```
POST /process
Content-Type: multipart/form-data
```

Process a medical form document through OCR and LLM parsing.

**Request:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | File | Yes | Document file (PDF, JPEG, PNG, HEIC) |
| `ocr_provider` | String | No | OCR provider: `mistral`, `gemini`, `google_docai`. Default: `mistral` |
| `llm_provider` | String | No | LLM provider: `gemini`, `openai`. Default: `gemini` |

**Example:**

```bash
curl -X POST http://localhost:8000/api/v1/process \
  -F "file=@form.pdf" \
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
    "address_street": "123 Main St",
    "address_city": "Springfield",
    "address_state": "IL",
    "address_zip": "62701",
    "phone_cell": "555-123-4567",
    "has_diabetes": false,
    "has_hypertension": true,
    "current_medications": "Lisinopril 10mg daily",
    "allergies": "Penicillin",
    "chief_complaint": "Annual checkup"
  },
  "filled_pdf_base64": "JVBERi0xLjQK...",
  "confidence_score": 0.87,
  "ocr_confidence": 0.90,
  "llm_confidence": 0.82,
  "field_confidences": {
    "patient_first_name": 0.95,
    "patient_last_name": 0.95,
    "date_of_birth": 0.88,
    "has_diabetes": 0.92
  },
  "processing_time_ms": 3420,
  "metadata": {
    "ocr_provider": "mistral",
    "llm_provider": "gemini",
    "filename": "form.pdf",
    "page_count": 2,
    "ocr_model": "pixtral-12b-2409",
    "llm_model": "gemini-2.0-flash",
    "pdf_filled": true
  }
}
```

**Error Responses:**

| Code | Description |
|------|-------------|
| 400 | Invalid request (bad file, unsupported format, missing API key) |
| 422 | Validation error |
| 500 | Processing error |

---

### List Providers

```
GET /providers
```

Get list of available OCR and LLM providers.

**Response:**

```json
{
  "ocr_providers": [
    {
      "id": "mistral",
      "name": "Mistral Document AI",
      "available": true
    },
    {
      "id": "gemini",
      "name": "Gemini Vision",
      "available": true
    },
    {
      "id": "google_docai",
      "name": "Google Document AI",
      "available": false,
      "note": "Coming soon - HIPAA-compliant option"
    }
  ],
  "llm_providers": [
    {
      "id": "gemini",
      "name": "Gemini",
      "available": true
    },
    {
      "id": "openai",
      "name": "OpenAI GPT-4",
      "available": true
    }
  ]
}
```

## Data Types

### Confidence Scores

All confidence scores are floats between 0.0 and 1.0:

- `0.0 - 0.3`: Low confidence (likely errors)
- `0.3 - 0.7`: Medium confidence (may need review)
- `0.7 - 1.0`: High confidence (likely accurate)

### Filled PDF

The `filled_pdf_base64` field contains the filled PDF as a base64-encoded string. To use:

```python
import base64

pdf_bytes = base64.b64decode(response["filled_pdf_base64"])
with open("filled_form.pdf", "wb") as f:
    f.write(pdf_bytes)
```

```javascript
const pdfBytes = atob(response.filled_pdf_base64);
const blob = new Blob([new Uint8Array([...pdfBytes].map(c => c.charCodeAt(0)))], {type: 'application/pdf'});
```
