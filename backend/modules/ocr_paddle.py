from paddleocr import PaddleOCR
from typing import Dict, List, Optional, Tuple


# ---------------- OCR ENGINE ----------------
# Auto OCR across multiple language packs (cached).
AUTO_OCR_LANGS: List[str] = [
    "latin",       # English, Spanish, French, Indonesian, etc.
    "cyrillic",    # Russian, Ukrainian, etc.
    "arabic",      # Arabic
    "devanagari",  # Hindi, Marathi, etc.
    "ch",          # Chinese (Simplified/Traditional)
    "japan",       # Japanese
    "korean"       # Korean
]

_OCR_ENGINES: Dict[str, PaddleOCR] = {}


def _get_ocr_engine(lang: str) -> PaddleOCR:
    if lang not in _OCR_ENGINES:
        _OCR_ENGINES[lang] = PaddleOCR(
            use_angle_cls=True,  # handles rotated text
            lang=lang,
            show_log=False
        )
    return _OCR_ENGINES[lang]


def initialize_ocr_engines() -> None:
    """
    Pre-initialize all OCR engines at app startup.
    This prevents 40-50 second delays on first request.
    """
    from backend.utils.logger import get_logger
    logger = get_logger("OmniAI")
    
    logger.info("Pre-initializing OCR engines...")
    for lang in AUTO_OCR_LANGS:
        _get_ocr_engine(lang)
    logger.info("OCR engines initialized successfully")


def _run_ocr(image_path: str, engine: PaddleOCR) -> Tuple[Dict, int]:
    try:
        result = engine.ocr(image_path, cls=True)
    except Exception as e:
        return {
            "has_text": False,
            "text": "",
            "lines": [],
            "error": str(e)
        }, 0

    # PaddleOCR may return None / empty
    if not result or result == [None]:
        return {
            "has_text": False,
            "text": "",
            "lines": []
        }, 0

    lines: List[str] = []

    for block in result:
        if not block:
            continue

        for line in block:
            if line and len(line) >= 2:
                text = line[1][0]
                if text.strip():
                    lines.append(text.strip())

    if not lines:
        return {
            "has_text": False,
            "text": "",
            "lines": []
        }, 0

    text = "\n".join(lines)
    score = len(text.replace("\n", ""))

    return {
        "has_text": True,
        "text": text,
        "lines": lines
    }, score


# ---------------- MAIN FUNCTION ----------------
def extract_text_paddle(
    image_path: str,
    preferred_langs: Optional[List[str]] = None
) -> Dict:
    """
    Robust OCR extraction using PaddleOCR.

    Returns:
    {
        "has_text": bool,
        "text": str,
        "lines": list[str]
    }
    """

    langs = preferred_langs or AUTO_OCR_LANGS

    best_result: Optional[Dict] = None
    best_score = 0
    best_lang = None

    for lang in langs:
        engine = _get_ocr_engine(lang)
        result, score = _run_ocr(image_path, engine)

        if score > best_score:
            best_result = result
            best_score = score
            best_lang = lang

        # Early stop if we already got a strong result
        if best_score >= 300:
            break

    if not best_result:
        return {
            "has_text": False,
            "text": "",
            "lines": []
        }

    best_result["language_hint"] = best_lang
    return best_result


# ---------------- LOCAL TEST ----------------
if __name__ == "__main__":
    output = extract_text_paddle("test.jpg")
    print(output)
