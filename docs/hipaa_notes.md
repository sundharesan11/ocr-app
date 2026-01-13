# HIPAA Compliance Notes

This document outlines current security measures and recommendations for achieving HIPAA compliance in production deployment.

## Current Security Measures

### PHI-Safe Logging

The application uses a custom logging wrapper (`src/utils/logging.py`) that automatically redacts potential PHI patterns:

- Social Security Numbers
- Phone numbers
- Email addresses
- Dates of birth
- Medical Record Numbers (MRN)
- Patient names (basic patterns)

**Example:**
```python
logger.info("Processing for patient", name="John Doe")
# Logs: "Processing for patient | name=[REDACTED-NAME]"
```

### No Persistent PHI Storage

- Extracted data is never written to disk
- No database storage of PHI
- All processing is in-memory only
- Uploaded files are not cached

### HTTPS Communication

All API calls to external providers use HTTPS:
- Mistral API
- Google AI (Gemini)
- OpenAI API

### Abstracted Provider Interfaces

Provider implementations are abstracted behind interfaces, allowing easy swapping to HIPAA-compliant endpoints:

```python
# Easy to swap providers
from src.ocr import create_ocr_provider, OCRProvider

# Current
ocr = create_ocr_provider(OCRProvider.MISTRAL)

# Future HIPAA-compliant
ocr = create_ocr_provider(OCRProvider.GOOGLE_DOCAI)
```

## Required Steps for HIPAA Compliance

### 1. Business Associate Agreements (BAAs)

Sign BAAs with all API providers handling PHI:

| Provider | BAA Available | Notes |
|----------|---------------|-------|
| Google Cloud (Gemini via Vertex AI) | ✅ Yes | Use Vertex AI endpoints |
| OpenAI | ✅ Yes | Enterprise tier required |
| Mistral | ⚠️ Check | Contact sales |

### 2. Use HIPAA-Eligible Endpoints

Replace standard API endpoints with HIPAA-eligible versions:

**Google:**
- Switch from `generativeai` SDK to Vertex AI
- Use US-region only processing
- Enable VPC Service Controls

**OpenAI:**
- Use Azure OpenAI Service (HIPAA-eligible)
- Or OpenAI Enterprise tier

### 3. Encryption at Rest

If any storage is added:
- Use encrypted volumes
- Implement key management
- Regular key rotation

### 4. Audit Logging

Implement audit logging for:
- All API access
- User authentication events
- PHI access attempts
- System configuration changes

Recommended: Use structured JSON logging with immutable storage.

### 5. Access Controls

- Implement authentication (JWT, API keys)
- Role-based access control (RBAC)
- Principle of least privilege

### 6. Network Security

- Deploy in private VPC
- Use VPN for administrative access
- Enable WAF for public endpoints
- Rate limiting

### 7. Data Residency

- Use US-region only for all services
- Verify data does not leave US boundaries
- Document data flow

## Deployment Checklist

- [ ] Sign BAAs with all providers
- [ ] Switch to HIPAA-eligible API endpoints
- [ ] Enable TLS 1.2+ only
- [ ] Implement authentication
- [ ] Enable audit logging
- [ ] Deploy in private VPC
- [ ] Configure WAF
- [ ] Document data flow
- [ ] Conduct security assessment
- [ ] Train staff on HIPAA requirements

## Environment Variables for Production

```env
# Set to production to disable docs endpoint
ENVIRONMENT=production

# Use HIPAA-eligible endpoints
# (Update SDK initialization in code)
GEMINI_API_KEY=your_vertex_ai_key
OPENAI_API_KEY=your_azure_openai_key

# Enable strict logging
LOG_LEVEL=INFO
```

## Google Document AI Integration

For maximum HIPAA compliance, implement Google Document AI:

1. Enable Document AI API in Google Cloud Console
2. Create a form parser processor in US region
3. Sign Google Cloud BAA
4. Implement processor in `src/ocr/google_docai_stub.py`

```python
# Example implementation outline
from google.cloud import documentai_v1 as documentai

class GoogleDocAI(BaseOCR):
    def __init__(self, project_id: str, location: str = "us", processor_id: str):
        self._client = documentai.DocumentProcessorServiceClient()
        self._processor_name = f"projects/{project_id}/locations/{location}/processors/{processor_id}"

    async def extract_text(self, images: list[bytes]) -> OCRResult:
        # Implementation here
        pass
```

## References

- [HHS HIPAA Security Rule](https://www.hhs.gov/hipaa/for-professionals/security/index.html)
- [Google Cloud HIPAA Compliance](https://cloud.google.com/security/compliance/hipaa)
- [Azure OpenAI Service HIPAA](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/hipaa-phi)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
