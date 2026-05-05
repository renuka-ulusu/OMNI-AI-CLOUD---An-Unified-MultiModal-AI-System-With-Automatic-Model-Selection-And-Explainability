import spacy
from transformers import pipeline
from langdetect import detect
from typing import Dict, List
from backend.modules.translation_ai import translate_to_english


# ---------------- LOAD MODELS ----------------

# spaCy for NER
nlp = spacy.load("en_core_web_sm")

# Sentiment model (3-class: negative/neutral/positive)
sentiment_pipeline = pipeline(
    "sentiment-analysis",
    model="cardiffnlp/twitter-roberta-base-sentiment-latest"
)


def _normalize_sentiment_label(raw_label: str) -> str:
    label = (raw_label or "").strip().lower()

    if "negative" in label or label in {"label_0", "neg"}:
        return "SAD"
    if "neutral" in label or label in {"label_1", "neu"}:
        return "NEUTRAL"
    if "positive" in label or label in {"label_2", "pos"}:
        return "POSITIVE"

    return "NEUTRAL"


def _extract_sentiment_scores(result) -> Dict[str, float]:
    """
    Normalize transformer sentiment outputs into fixed keys:
    SAD, NEUTRAL, POSITIVE
    """
    scores = {"SAD": 0.0, "NEUTRAL": 0.0, "POSITIVE": 0.0}

    if not result:
        return scores

    # Some pipeline versions return [[...]] for single input with top_k=None
    if isinstance(result, list) and len(result) > 0 and isinstance(result[0], list):
        items = result[0]
    elif isinstance(result, list):
        items = result
    else:
        items = [result]

    for item in items:
        label = _normalize_sentiment_label(item.get("label", ""))
        score = float(item.get("score", 0.0))
        scores[label] = max(scores[label], score)

    return scores


def _calibrate_sentiment(text: str, model_label: str, model_confidence: float, scores: Dict[str, float]) -> tuple[str, float]:
    """
    Calibrate sentiment for poetic/grief-heavy text where base model often predicts neutral.
    """
    lowered = (text or "").lower()
    grief_terms = [
        "grief", "loss", "lost", "alone", "lonely", "broken", "hollow",
        "empty", "wound", "vanished", "missing", "gone", "dark", "tears",
        "sorrow", "sad", "hurt", "pain", "ache", "mourning", "shadow"
    ]
    grief_hits = sum(1 for term in grief_terms if term in lowered)

    sad_score = scores.get("SAD", 0.0)
    neutral_score = scores.get("NEUTRAL", 0.0)
    positive_score = scores.get("POSITIVE", 0.0)

    label = model_label
    confidence = model_confidence

    if label == "NEUTRAL" and grief_hits >= 2 and sad_score >= 0.20:
        label = "SAD"
        confidence = max(confidence, min(0.90, sad_score + 0.22))

    if label == "POSITIVE" and grief_hits >= 3 and positive_score < 0.75 and sad_score >= 0.22:
        label = "SAD"
        confidence = max(sad_score, min(0.88, sad_score + 0.18))

    if label != "SAD" and sad_score > neutral_score + 0.08 and sad_score > positive_score + 0.08:
        label = "SAD"
        confidence = max(confidence, sad_score)

    return label, confidence


# ---------------- MAIN FUNCTION ----------------
def analyze_text(text: str) -> Dict:
    """
    Intelligent text analysis with auto language handling.

    Returns:
    {
        "original_language": str,
        "translated_text": str | None,
        "sentiment": str,
        "sentiment_confidence": float,
        "entities": list,
        "explanation": str
    }
    """

    explanation_steps = []

    # 1. Detect language
    try:
        language = detect(text)
    except Exception:
        language = "unknown"

    explanation_steps.append(f"Detected input language as '{language}'.")

    processed_text = text
    translated_text = None

    # 2. Translate if not English
    if language != "en":
        explanation_steps.append(
            "Input is not English. Activating translation model to convert text to English."
        )

        translation_result = translate_to_english(text, source_lang=language)
        translated_text = translation_result["translated_text"]
        processed_text = translated_text

        explanation_steps.append(
            "Text successfully translated to English for downstream NLP tasks."
        )
    else:
        explanation_steps.append(
            "Input is already in English. Translation not required."
        )

    # 3. Named Entity Recognition
    doc = nlp(processed_text)
    entities: List[Dict] = [
        {
            "text": ent.text,
            "label": ent.label_
        }
        for ent in doc.ents
    ]

    explanation_steps.append(
        f"Extracted {len(entities)} named entities using spaCy NER."
    )

    # 4. Sentiment Analysis
    sentiment_distribution = sentiment_pipeline(processed_text[:512], top_k=None)
    sentiment_scores = _extract_sentiment_scores(sentiment_distribution)

    model_label = max(sentiment_scores, key=sentiment_scores.get)
    model_confidence = sentiment_scores.get(model_label, 0.0)
    sentiment_label, sentiment_confidence = _calibrate_sentiment(
        processed_text,
        model_label,
        model_confidence,
        sentiment_scores
    )

    explanation_steps.append(
        "Applied calibrated 3-class sentiment analysis (sad/neutral/positive) on processed text."
    )

    # 5. Final explanation
    explanation = " ".join(explanation_steps)

    return {
        "original_language": language,
        "translated_text": translated_text,
        "sentiment": sentiment_label,
        "sentiment_confidence": round(sentiment_confidence * 100, 2),
        "entities": entities,
        "explanation": explanation
    }


# ---------------- LOCAL TEST ----------------
if __name__ == "__main__":
    sample = "कृत्रिम बुद्धिमत्ता आज कई क्षेत्रों में उपयोग की जा रही है।"
    result = analyze_text(sample)

    for k, v in result.items():
        print(f"{k}: {v}")
