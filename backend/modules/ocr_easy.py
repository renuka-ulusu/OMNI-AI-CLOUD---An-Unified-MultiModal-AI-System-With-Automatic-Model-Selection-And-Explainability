import easyocr
from typing import Dict


# ---------------- OCR ENGINE ----------------
reader = easyocr.Reader(
    ["en"],
    gpu=False  # works on CPU reliably
)


# ---------------- MAIN FUNCTION ----------------
def extract_text_easy(image_path: str) -> Dict:
    """
    Extract text from image using EasyOCR.

    Returns:
    {
        "text": str,
        "lines": list[str]
    }
    """

    results = reader.readtext(image_path)

    lines = [text for _, text, _ in results]

    return {
        "text": " ".join(lines),
        "lines": lines
    }


# ---------------- LOCAL TEST ----------------
if __name__ == "__main__":
    output = extract_text_easy("test.jpg")
    print(output["text"])
