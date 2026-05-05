from typing import Dict, List, Tuple
from pathlib import Path

from PyPDF2 import PdfReader
from pdf2image import convert_from_path


# 🔴 IMPORTANT: change this ONLY if poppler path changes
POPPLER_PATH = r"C:\Users\kotip\Downloads\Release-25.12.0-0\poppler-25.12.0\Library\bin"

MAX_PDF_SIZE_BYTES = 25 * 1024 * 1024
MAX_PDF_PAGES = 200


def normalize_utf8_text(text: str) -> str:
    """
    Enforce strict UTF-8 round-trip encoding for extracted text.
    Raises UnicodeError if text contains invalid surrogate data.
    """
    if not isinstance(text, str):
        raise TypeError("Document text must be a string")

    return text.encode("utf-8", "strict").decode("utf-8", "strict")


def validate_pdf_file(pdf_path: str) -> Dict[str, int]:
    """
    Strict PDF validation:
    - extension must be .pdf
    - file signature must start with %PDF-
    - size must be within max limit
    - encrypted PDFs are rejected
    - page count must be within limit

    Returns simple metadata for validated PDFs.
    """
    path = Path(pdf_path)

    if path.suffix.lower() != ".pdf":
        raise ValueError("Only .pdf documents are supported")

    if not path.exists() or not path.is_file():
        raise ValueError("Uploaded PDF file not found")

    file_size = path.stat().st_size
    if file_size <= 0:
        raise ValueError("Uploaded PDF is empty")

    if file_size > MAX_PDF_SIZE_BYTES:
        raise ValueError(
            f"PDF exceeds maximum allowed size of {MAX_PDF_SIZE_BYTES // (1024 * 1024)}MB"
        )

    with open(path, "rb") as file_obj:
        signature = file_obj.read(5)

    if signature != b"%PDF-":
        raise ValueError("Invalid PDF signature. Upload a valid PDF document")

    try:
        reader = PdfReader(str(path), strict=True)
    except Exception as error:
        raise ValueError(f"Invalid or corrupted PDF: {error}") from error

    if reader.is_encrypted:
        raise ValueError("Encrypted/password-protected PDFs are not supported")

    page_count = len(reader.pages)
    if page_count <= 0:
        raise ValueError("PDF has no readable pages")

    if page_count > MAX_PDF_PAGES:
        raise ValueError(f"PDF exceeds maximum page limit of {MAX_PDF_PAGES}")

    return {
        "file_size": file_size,
        "page_count": page_count,
    }


# --------------------------------------------------
# 1. TEXT EXTRACTION (TEXT-BASED PDFs)
# --------------------------------------------------
def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract selectable text from a text-based PDF.
    """
    reader = PdfReader(pdf_path)
    pages_text = []

    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages_text.append(text)

    combined_text = "\n".join(pages_text).strip()
    return normalize_utf8_text(combined_text)


# --------------------------------------------------
# 2. IMAGE EXTRACTION (SCANNED PDFs)
# --------------------------------------------------
def extract_images_from_pdf(pdf_path: str) -> List[Path]:
    """
    Convert PDF pages into images (for scanned PDFs).
    """
    output_dir = Path("temp_uploads/pdf_images")
    output_dir.mkdir(parents=True, exist_ok=True)

    images = convert_from_path(
        pdf_path,
        dpi=300,
        poppler_path=POPPLER_PATH
    )

    image_paths: List[Path] = []

    for idx, image in enumerate(images, start=1):
        img_path = output_dir / f"page_{idx}.png"
        image.save(img_path, "PNG")
        image_paths.append(img_path)

    return image_paths


# --------------------------------------------------
# 3. PDF TYPE DETECTION (CRITICAL LOGIC)
# --------------------------------------------------
def analyze_pdf_type(text: str) -> str:
    """
    Decide whether PDF is text-based or scanned.
    """
    if text and len(text) > 100:
        return "text_pdf"
    return "scanned_pdf"


# --------------------------------------------------
# 4. SINGLE ENTRY POINT (USE THIS EVERYWHERE)
# --------------------------------------------------
def process_pdf(pdf_path: str) -> Tuple[str, str, List[Path]]:
    """
    Unified PDF processor.

    Returns:
    - pdf_type: "text_pdf" | "scanned_pdf"
    - extracted_text
    - image_paths (empty if text-based)
    """
    extracted_text = extract_text_from_pdf(pdf_path)
    pdf_type = analyze_pdf_type(extracted_text)

    if pdf_type == "scanned_pdf":
        image_paths = extract_images_from_pdf(pdf_path)
    else:
        image_paths = []

    return pdf_type, extracted_text, image_paths
