from pathlib import Path

from langdetect import detect, LangDetectException

from backend.utils.pdf_utils import normalize_utf8_text, process_pdf, validate_pdf_file
from backend.utils.docx_utils import extract_text_from_docx, validate_docx_file
from backend.modules.ocr_paddle import extract_text_paddle
from backend.modules.summarization import generate_summary


def process_document(pdf_path: str) -> dict:
    """
    Intelligent Document AI pipeline.

    Handles:
    - Text-based PDFs
    - Scanned PDFs
    - Mixed PDFs (text + images)

    Returns:
    {
        document_type,
        extraction_method,
        text_length,
        summary,
        insights
    }
    """

    file_ext = Path(pdf_path).suffix.lower()
    extracted_text = ""
    image_paths = []
    source_type = ""

    # --------------------------------------------------
    # STEP 1: Strict document validation + extraction
    # --------------------------------------------------
    if file_ext == ".pdf":
        validate_pdf_file(pdf_path)
        source_type, extracted_text, image_paths = process_pdf(pdf_path)

        # --------------------------------------------------
        # STEP 2: OCR for scanned / mixed PDFs
        # --------------------------------------------------
        if source_type in ["scanned_pdf", "mixed_pdf"]:
            ocr_text_blocks = []

            for img_path in image_paths:
                ocr_result = extract_text_paddle(str(img_path))
                if ocr_result.get("has_text"):
                    normalized_block = normalize_utf8_text(ocr_result["text"])
                    ocr_text_blocks.append(normalized_block)

            extracted_text = "\n\n".join(ocr_text_blocks)
            document_type = "Scanned or Image-based PDF"
            extraction_method = "OCR using PaddleOCR"
        else:
            document_type = "Text-based PDF"
            extraction_method = "Embedded text (no OCR)"

    elif file_ext == ".docx":
        validate_docx_file(pdf_path)
        extracted_text = extract_text_from_docx(pdf_path)
        source_type = "docx"
        document_type = "Word Document (.docx)"
        extraction_method = "Embedded DOCX text"

    else:
        raise ValueError("Unsupported document type. Only PDF and DOCX are allowed")

    extracted_text = normalize_utf8_text(extracted_text)

    # --------------------------------------------------
    # STEP 3: Validate extracted text
    # --------------------------------------------------
    normalized_text = (extracted_text or "").strip()
    if not normalized_text:
        result = {
            "document_type": document_type,
            "extraction_method": extraction_method,
            "text_length": 0,
            "summary": "No meaningful text detected in the document.",
            "insights": [],
            "language": "unknown",
        }
        if source_type in ["scanned_pdf", "mixed_pdf", "docx"]:
            result["extracted_text"] = extracted_text
        return result

    # --------------------------------------------------
    # STEP 4: Detect language
    # --------------------------------------------------
    try:
        language = detect(extracted_text)
    except LangDetectException:
        language = "unknown"

    # --------------------------------------------------
    # STEP 5: Generate intelligent summary
    # --------------------------------------------------
    # For short OCR snippets we still return a summary string instead of skipping.
    if len(normalized_text) < 50:
        summary = "Document content is short, but key text was extracted successfully."
    else:
        summary = generate_summary(extracted_text, max_length=200)

    if not (summary or "").strip():
        summary = "Summary unavailable for this document, but extracted text is shown above."

    # --------------------------------------------------
    # STEP 6: Lightweight semantic insights
    # --------------------------------------------------
    insights = []

    lowered = extracted_text.lower()

    if "resume" in lowered or "curriculum vitae" in lowered:
        insights.append("This document appears to be a resume.")

    if "invoice" in lowered or "total amount" in lowered:
        insights.append("This document appears to be an invoice or bill.")

    if "semester" in lowered or "sgpa" in lowered:
        insights.append("This document appears to be an academic result or marksheet.")

    if not insights:
        insights.append("This document contains structured informational content.")

    # --------------------------------------------------
    # STEP 7: Return results (text-based PDFs only get summary, not raw text)
    # --------------------------------------------------
    result = {
        "document_type": document_type,
        "extraction_method": extraction_method,
        "text_length": len(extracted_text),
        "summary": summary,
        "insights": insights,
        "language": language
    }

    # Only include extracted_text for scanned/OCR PDFs where user might need it
    # For text-based PDFs, summary is sufficient
    if source_type in ["scanned_pdf", "mixed_pdf", "docx"]:
        result["extracted_text"] = extracted_text

    return result


# --------------------------------------------------
# LOCAL TEST
# --------------------------------------------------
if __name__ == "__main__":
    result = process_document("sample.pdf")
    print(result)
