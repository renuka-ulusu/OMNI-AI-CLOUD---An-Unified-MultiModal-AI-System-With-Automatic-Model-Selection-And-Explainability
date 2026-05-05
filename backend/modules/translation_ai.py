from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from typing import Dict
import re
from pathlib import Path

# Use NLLB-200 distilled for all languages (200+ language support, balanced speed/quality)
MODEL_NAME = "facebook/nllb-200-distilled-600M"

# Language code mapping (langdetect -> NLLB codes)
LANG_CODE_MAP = {
    "en": "eng_Latn",      # English
    "hi": "hin_Deva",      # Hindi
    "es": "spa_Latn",      # Spanish
    "fr": "fra_Latn",      # French
    "de": "deu_Latn",      # German
    "it": "ita_Latn",      # Italian
    "pt": "por_Latn",      # Portuguese
    "ru": "rus_Cyrl",      # Russian
    "ja": "jpn_Jpan",      # Japanese
    "ko": "kor_Hang",      # Korean
    "zh-cn": "zho_Hans",   # Chinese (Simplified)
    "zh-tw": "zho_Hant",   # Chinese (Traditional)
    "ar": "arb_Arab",      # Arabic
    "te": "tel_Telu",      # Telugu
    "ta": "tam_Taml",      # Tamil
    "ml": "mal_Mlym",      # Malayalam
    "bn": "ben_Beng",      # Bengali
    "pa": "pan_Guru",      # Punjabi
    "ur": "urd_Arab",      # Urdu
    "th": "tha_Thai",      # Thai
    "vi": "vie_Latn",      # Vietnamese
    "id": "ind_Latn",      # Indonesian
    "tr": "tur_Latn",      # Turkish
    "pl": "pol_Latn",      # Polish
    "nl": "nld_Latn",      # Dutch
    "sv": "swe_Latn",      # Swedish
}

# Cache for model
_tokenizer = None
_model = None
_translation_available = True
_translation_error = None


def _local_model_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "models" / "downloaded_models" / "nllb-200-distilled-600M"


def _get_model():
    global _tokenizer, _model, _translation_available, _translation_error

    if not _translation_available:
        raise RuntimeError(_translation_error or "Translation model unavailable")

    if _tokenizer is None:
        local_model_path = _local_model_dir()
        load_target = str(local_model_path) if local_model_path.exists() else MODEL_NAME

        try:
            _tokenizer = AutoTokenizer.from_pretrained(load_target, local_files_only=True)
            _model = AutoModelForSeq2SeqLM.from_pretrained(load_target, local_files_only=True)
        except Exception as error:
            _translation_available = False
            _translation_error = (
                "Translation model is not available locally. "
                "Download model first or enable internet access."
            )
            raise RuntimeError(_translation_error) from error

    return _tokenizer, _model


def _normalize_text(text: str) -> str:
    """Clean up text before translation"""
    text = text.replace("\ufeff", " ")  # Remove BOM
    text = re.sub(r"\s+", " ", text)    # Normalize whitespace
    return text.strip()


def _to_nllb_code(lang_code: str, default: str = "eng_Latn") -> str:
    if not lang_code:
        return default
    return LANG_CODE_MAP.get(lang_code.lower(), default)


def translate_text(text: str, source_lang: str = None, target_lang: str = "en") -> Dict:
    """
    Translate text from source language to target language using NLLB-200.

    Returns:
    {
        "translated_text": str,
        "source_language": str,
        "target_language": str
    }
    """

    cleaned_text = _normalize_text(text)

    try:
        tokenizer, model = _get_model()
    except RuntimeError as error:
        return {
            "translated_text": cleaned_text,
            "source_language": (source_lang or "unknown").lower(),
            "target_language": (target_lang or "en").lower(),
            "translation_applied": False,
            "translation_error": str(error),
        }

    src_lang = (source_lang or "en").lower()
    tgt_lang = (target_lang or "en").lower()

    src_lang_code = _to_nllb_code(src_lang, default="eng_Latn")
    tgt_lang_code = _to_nllb_code(tgt_lang, default="eng_Latn")

    tokenizer.src_lang = src_lang_code

    inputs = tokenizer(
        cleaned_text,
        return_tensors="pt",
        truncation=True,
        max_length=512,
        padding=True
    )

    translated_tokens = model.generate(
        **inputs,
        forced_bos_token_id=tokenizer.convert_tokens_to_ids(tgt_lang_code),
        max_length=512
    )

    translated_text = tokenizer.batch_decode(
        translated_tokens,
        skip_special_tokens=True
    )[0]

    return {
        "translated_text": translated_text,
        "source_language": src_lang,
        "target_language": tgt_lang,
        "translation_applied": True,
    }


def translate_to_english(text: str, source_lang: str = None) -> Dict:
    """
    Translate text from any language to English using NLLB-200.

    Returns:
    {
        "translated_text": str
    }
    """

    result = translate_text(text, source_lang=source_lang, target_lang="en")
    return {
        "translated_text": result["translated_text"]
    }


# ---------------- LOCAL TEST ----------------
if __name__ == "__main__":
    # Test Hindi
    hindi_text = "नमस्ते, मैं एक छात्र हूं"
    result = translate_to_english(hindi_text, source_lang="hi")
    print(f"Hindi: {result['translated_text']}")
    
    # Test Spanish
    spanish_text = "Hola, soy estudiante"
    result = translate_to_english(spanish_text, source_lang="es")
    print(f"Spanish: {result['translated_text']}")
