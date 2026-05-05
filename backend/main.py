from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Tuple
from dotenv import load_dotenv
load_dotenv()
from flask import Flask, jsonify, render_template, request
from langdetect import detect

from backend.agent.auto_selector import analyze_input, auto_model_selector, is_animal_image
from backend.utils.file_utils import save_uploaded_file, delete_file
from backend.utils.logger import get_logger

from backend.modules.image_classification import classify_image
from backend.modules.object_detection import detect_objects
from backend.modules.wildlife_detection import detect_wildlife
from backend.modules.ocr_paddle import extract_text_paddle, initialize_ocr_engines
from backend.modules.document_ai import process_document
from backend.modules.text_analytics import analyze_text
from backend.modules.translation_ai import translate_text
from backend.modules.blip_vision_language import generate_image_caption, initialize_blip_model
from backend.modules.summarization import initialize_summarizer
from backend.modules.explainability import generate_explanation
from backend.utils.pdf_utils import validate_pdf_file
from backend.utils.docx_utils import validate_docx_file

logger = get_logger("OmniAI")
app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024

LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "ja": "Japanese",
    "ko": "Korean",
    "zh-cn": "Chinese (Simplified)",
    "zh-tw": "Chinese (Traditional)",
    "ar": "Arabic",
    "te": "Telugu",
    "ta": "Tamil",
    "ml": "Malayalam",
    "bn": "Bengali",
    "pa": "Punjabi",
    "ur": "Urdu",
    "th": "Thai",
    "vi": "Vietnamese",
    "id": "Indonesian",
    "tr": "Turkish",
    "pl": "Polish",
    "nl": "Dutch",
    "sv": "Swedish",
    "unknown": "Unknown",
}

TRANSLATION_LANGUAGE_CODES = [
    "en", "hi", "te", "ta", "ml", "bn", "pa", "ur",
    "es", "fr", "de", "it", "pt", "ru", "ja", "ko",
    "zh-cn", "zh-tw", "ar", "th", "vi", "id", "tr", "pl", "nl", "sv"
]

_models_initialized = False


def ensure_models_initialized() -> None:
    global _models_initialized
    if _models_initialized:
        return

    logger.info("OmniAI Cloud (Flask) starting up...")
    initialize_ocr_engines()
    initialize_blip_model()
    initialize_summarizer()
    _models_initialized = True
    logger.info("OmniAI Cloud (Flask) ready for requests")


def _json_error(message: str, status_code: int = 400):
    return jsonify({"detail": message}), status_code


def _to_upload_file(file_storage):
    return SimpleNamespace(filename=file_storage.filename, file=file_storage.stream)


def _run_file_analysis(file_path: Path) -> Dict[str, Any]:
    metadata = analyze_input(file_path=str(file_path))
    if metadata["input_type"] == "unknown":
        raise ValueError("Unsupported input type")

    if metadata["input_type"] == "document":
        if metadata.get("file_extension") == ".pdf":
            validate_pdf_file(str(file_path))
        elif metadata.get("file_extension") == ".docx":
            validate_docx_file(str(file_path))
        else:
            raise ValueError("Unsupported document type. Only PDF and DOCX are allowed")

    decision = auto_model_selector(metadata)
    results: Dict[str, Any] = {}
    selected_modules = []

    for model in decision["models"]:
        logger.info(f"Running model: {model}")

        if model == "image_classification":
            results["image_classification"] = classify_image(str(file_path))
            selected_modules.append(model)

        elif model == "object_detection":
            if "ocr" in results:
                ocr_word_count = results["ocr"].get("word_count", 0)
                ocr_text_len = len(results["ocr"].get("text", "") or "")
                if ocr_word_count >= 10 and ocr_text_len >= 50:
                    logger.info("Skipping object detection - OCR found substantial text")
                    continue

            if "image_classification" in results:
                label = results["image_classification"].get("label", "")
                confidence = results["image_classification"].get("confidence", 0)

                if is_animal_image(label):
                    logger.info(f"Using wildlife detection for: {label}")
                    detection_result = detect_wildlife(str(file_path))

                    if detection_result.get("detections"):
                        detection_result["detections"] = correct_generic_labels(
                            detection_result["detections"], label, confidence
                        )

                    results["object_detection"] = detection_result
                    selected_modules.append("wildlife_detection")
                else:
                    results["object_detection"] = detect_objects(str(file_path))
                    selected_modules.append(model)
            else:
                results["object_detection"] = detect_objects(str(file_path))
                selected_modules.append(model)

        elif model == "ocr_paddle":
            should_run_ocr = True
            if "image_classification" in results:
                label = results["image_classification"].get("label", "")
                if is_animal_image(label):
                    logger.info(f"Skipping OCR for wildlife image: {label}")
                    should_run_ocr = False

            if should_run_ocr:
                ocr_result = extract_text_paddle(str(file_path))
                if ocr_result.get("has_text"):
                    extracted_text = (ocr_result.get("text") or "").strip()
                    word_count = len([word for word in extracted_text.split() if word])

                    if len(extracted_text) >= 50 and word_count >= 10:
                        ocr_result["word_count"] = word_count
                        results["ocr"] = ocr_result
                        selected_modules.append(model)
                        logger.info(f"OCR extracted {word_count} words")

                        try:
                            detected_lang = detect(extracted_text)
                            metadata["language"] = detected_lang
                        except Exception:
                            pass
                    else:
                        logger.info(
                            f"Skipping OCR - insufficient text ({word_count} words, {len(extracted_text)} chars)"
                        )
            else:
                logger.info("OCR skipped based on image content analysis")

        elif model == "blip_vision_language":
            prompt = None
            if "image_classification" in results:
                label = results["image_classification"].get("label", "")
                if is_animal_image(label):
                    prompt = f"a photo of {label}"

            caption_result = generate_image_caption(str(file_path), prompt=prompt)

            if "image_classification" in results and "object_detection" in results:
                label = results["image_classification"].get("label", "")
                detections = results["object_detection"].get("detections", [])

                if is_animal_image(label) and detections:
                    original_caption = caption_result.get("caption", "")
                    unique_animals = list(set([det["label"] for det in detections]))

                    if len(unique_animals) == 1:
                        enhanced_caption = f"{original_caption} [Scene: {unique_animals[0]} in action]"
                    elif len(unique_animals) > 1:
                        animals_str = ", ".join(unique_animals[:-1]) + f" and {unique_animals[-1]}"
                        enhanced_caption = f"{original_caption} [Scene: {animals_str} interaction]"
                    else:
                        enhanced_caption = original_caption

                    caption_result["enhanced_caption"] = enhanced_caption
                    caption_result["original_caption"] = original_caption
                    caption_result["caption"] = enhanced_caption
                    logger.info("Enhanced caption with species context")

            results["caption"] = caption_result
            selected_modules.append(model)

        elif model == "document_ai":
            doc_result = process_document(str(file_path))

            if doc_result.get("language"):
                metadata["language"] = doc_result["language"]

            extracted_text = doc_result.get("extracted_text", "")
            ocr_was_used = "OCR using" in doc_result.get("extraction_method", "")

            if not ocr_was_used:
                extracted_text = ""

            results["document"] = {
                "type": doc_result["document_type"],
                "extraction_method": doc_result["extraction_method"],
                "extracted_text": extracted_text,
                "summary": doc_result["summary"],
                "text_preview": doc_result["summary"][:1000],
            }
            selected_modules.append(model)

            if ocr_was_used:
                selected_modules.append("ocr_paddle")

    explanation = generate_explanation(
        input_type=metadata["input_type"],
        selected_models=selected_modules,
        results=results,
    )

    return {
        "metadata": metadata,
        "selected_modules": selected_modules,
        "results": results,
        "explanation": explanation["explanation"],
    }


def _run_text_analysis(
    text: str,
    source_language: str = "auto",
    target_language: str = "en",
    auto_detect_source: bool = True,
) -> Dict[str, Any]:
    metadata = analyze_input(text=text)
    decision = auto_model_selector(metadata)

    results: Dict[str, Any] = {}
    selected_modules = []

    source_language = (source_language or "auto").lower()
    target_language = (target_language or "en").lower()

    detected_language = metadata.get("language") or "unknown"

    if source_language == "auto" or auto_detect_source:
        effective_source_language = detected_language
    else:
        effective_source_language = source_language

    should_translate = (
        target_language != ""
        and effective_source_language not in ["", "unknown"]
        and effective_source_language != target_language
    )

    if should_translate:
        translation = translate_text(
            text,
            source_lang=effective_source_language,
            target_lang=target_language,
        )
        results["translation"] = translation
        selected_modules.append("translation_ai")

    metadata["source_language"] = effective_source_language
    metadata["target_language"] = target_language

    if "text_analytics" in decision["models"]:
        results["text_analytics"] = analyze_text(text)
        selected_modules.append("text_analytics")

    explanation = generate_explanation(
        input_type="text",
        selected_models=selected_modules,
        results=results,
    )

    return {
        "metadata": metadata,
        "selected_modules": selected_modules,
        "results": results,
        "explanation": explanation["explanation"],
    }


# ================= SMART LABEL CORRECTION =================
def correct_generic_labels(detections: list, classification_label: str, confidence: float) -> list:
    """
    Correct generic YOLO labels using image classification results.
    
    YOLO limitation: Trained on COCO dataset with generic labels (dog, cat, bird)
    Solution: Use ResNet50 ImageNet classification for species-specific labels
    
    Example: YOLO says "dog" but ResNet50 says "lion" → correct to "lion"
    """
    
    # Generic YOLO labels that need correction (COCO dataset limitation)
    GENERIC_LABELS = {
        # Big cats often detected as "dog" or "cat"
        "dog": [
            "lion", "tiger", "cheetah", "leopard", "jaguar", "cougar", "puma",
            "wolf", "timber wolf", "red wolf", "coyote", "dingo", "fox", "red fox",
            "hyena", "wild dog", "african wild dog"
        ],
        "cat": [
            "lion", "tiger", "cheetah", "leopard", "snow leopard", "jaguar",
            "cougar", "puma", "lynx", "bobcat", "serval", "caracal", "ocelot",
            "panther", "black panther"
        ],
        # Birds - extremely generic in YOLO
        "bird": [
            "eagle", "bald eagle", "golden eagle", "hawk", "falcon", "owl",
            "peacock", "parrot", "macaw", "flamingo", "ostrich", "penguin",
            "pelican", "swan", "crane", "heron", "stork", "vulture", "toucan",
            "cockatoo", "woodpecker", "hummingbird", "kingfisher", "albatross"
        ],
        # Hoofed animals - CRITICAL for antelope/gazelle detection
        "horse": ["zebra", "donkey", "mule", "pony"],
        "cow": [
            "buffalo", "bison", "ox", "yak", "water buffalo", "wildebeest", "gnu",
            "antelope", "gazelle", "impala", "springbok", "kudu", "eland"  # Added antelope species
        ],
        "sheep": [
            "ram", "bighorn", "goat", "ibex", "mountain goat",
            "gazelle", "impala", "antelope", "springbok"  # Added - sometimes detected as sheep
        ],
        # Large animals
        "elephant": ["african elephant", "indian elephant", "asian elephant"],
        "bear": ["brown bear", "polar bear", "black bear", "panda", "giant panda", "grizzly"],
        "giraffe": ["giraffe", "okapi"],
        # Deer family - VERY IMPORTANT
        "deer": [
            "elk", "moose", "reindeer", "caribou", 
            "antelope", "gazelle", "impala", "springbok", "gemsbok", "oryx"  # All antelope types
        ],
        # Primates
        "monkey": ["gorilla", "orangutan", "chimpanzee", "baboon", "macaque", "lemur"],
        # Marine
        "whale": ["killer whale", "orca", "blue whale", "humpback whale"],
        "seal": ["sea lion", "walrus", "fur seal"],
    }
    
    # Check if classification label should override generic YOLO label
    classification_lower = classification_label.lower()
    
    corrected_detections = []
    primary_animal_corrected = False
    
    for detection in detections:
        yolo_label = detection["label"].lower()
        
        # Check if YOLO label is generic and classification is more specific
        if yolo_label in GENERIC_LABELS:
            # First detection with matching category gets the classification label
            if not primary_animal_corrected and classification_lower in GENERIC_LABELS[yolo_label]:
                detection_copy = detection.copy()
                detection_copy["label"] = classification_label
                detection_copy["original_yolo_label"] = detection["label"]
                detection_copy["corrected"] = True
                corrected_detections.append(detection_copy)
                primary_animal_corrected = True
                logger.info(f"Corrected primary animal: {yolo_label} → {classification_label}")
            else:
                # Keep other detections as-is (might be prey/other animals)
                corrected_detections.append(detection)
                logger.info(f"Keeping detection: {yolo_label} (confidence: {detection['confidence']}%)")
        else:
            # Keep non-generic detections
            corrected_detections.append(detection)
    
    return corrected_detections


# ================= WEB UI =================
@app.get("/")
def home():
    ensure_models_initialized()
    return render_template(
        "index.html",
        app_title="OmniAI Cloud",
        app_subtitle="Unified AI Agent System",
        language_names=LANGUAGE_NAMES,
        translation_language_codes=TRANSLATION_LANGUAGE_CODES,
    )


# ================= API: FILE ANALYSIS =================
@app.post("/api/analyze/file")
def analyze_file_api():
    ensure_models_initialized()

    file = request.files.get("file")
    if file is None:
        return _json_error("File is required", 400)

    logger.info(f"Received file: {file.filename}")
    incoming_name = (file.filename or "").strip()
    if not incoming_name:
        return _json_error("Filename is required", 400)

    extension = Path(incoming_name).suffix.lower()
    allowed_extensions = {".jpg", ".jpeg", ".png", ".webp", ".pdf", ".docx"}
    if extension not in allowed_extensions:
        return _json_error("Unsupported file type. Allowed: .jpg, .jpeg, .png, .webp, .pdf, .docx", 415)

    file_path = None
    try:
        _, file_path = save_uploaded_file(_to_upload_file(file))
        result = _run_file_analysis(file_path)
        return jsonify(result)
    except ValueError as error:
        return _json_error(str(error), 400)
    except UnicodeError as error:
        return _json_error(str(error), 400)
    except Exception as error:
        logger.error(f"File analysis error: {error}")
        return _json_error("Internal server error during file analysis", 500)
    finally:
        if file_path is not None:
            delete_file(file_path)
            logger.info("Temporary file deleted")


# ================= API: TEXT ANALYSIS =================
@app.post("/api/analyze/text")
def analyze_text_api():
    ensure_models_initialized()
    logger.info("Received text input")

    text = (request.form.get("text") or "").strip()
    if not text:
        return _json_error("Text is required", 400)

    source_language = request.form.get("source_language", "auto")
    target_language = request.form.get("target_language", "en")
    auto_detect_source_raw = (request.form.get("auto_detect_source", "true") or "true").lower()
    auto_detect_source = auto_detect_source_raw in ["true", "1", "yes", "on"]

    try:
        result = _run_text_analysis(
            text=text,
            source_language=source_language,
            target_language=target_language,
            auto_detect_source=auto_detect_source,
        )
        return jsonify(result)
    except Exception as error:
        logger.error(f"Text analysis error: {error}")
        return _json_error("Internal server error during text analysis", 500)


# ================= API: HEALTH =================
@app.get("/api/health")
def health():
    return jsonify({"status": "OmniAI Cloud Flask backend is running"})


if __name__ == "__main__":
    ensure_models_initialized()
    app.run(host="0.0.0.0", port=8000, debug=False)
