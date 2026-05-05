"""
Text Summarization Module
Uses OpenRouter GPT-4 API for abstractive summarization.
"""

import os
import re
from pathlib import Path
from typing import Optional

import requests


MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
MISTRAL_API_KEY_ENV = "MISTRAL_API_KEY"
MISTRAL_MODEL = "mistral-large-latest"


def _read_env_file_var(var_name: str) -> Optional[str]:
    root_env = Path(__file__).resolve().parents[2] / ".env"
    backend_env = Path(__file__).resolve().parents[1] / ".env"

    for env_path in (root_env, backend_env):
        if not env_path.exists():
            continue

        try:
            for raw_line in env_path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()

                if not line or line.startswith("#") or "=" not in line:
                    continue

                key, value = line.split("=", 1)
                key = key.strip()
                if key != var_name:
                    continue

                value = value.strip().strip('"').strip("'")
                return value or None
        except Exception:
            continue

    return None


def _get_mistral_api_key() -> Optional[str]:
    env_value = os.getenv(MISTRAL_API_KEY_ENV)
    if env_value:
        return env_value

    file_value = _read_env_file_var(MISTRAL_API_KEY_ENV)
    if file_value:
        os.environ[MISTRAL_API_KEY_ENV] = file_value
        return file_value

    return None


def initialize_summarizer() -> None:
    """
    Validate Mistral AI summarization configuration at app startup.
    """
    from backend.utils.logger import get_logger

    logger = get_logger("OmniAI")
    model_name = MISTRAL_MODEL
    api_key = _get_mistral_api_key()

    if api_key:
        logger.info(f"Summarization configured with Mistral AI model: {model_name}")
    else:
        logger.warning(
            f"{MISTRAL_API_KEY_ENV} not found. Summarization will return fallback messages."
        )


def _clean_text(text: str) -> str:
    """
    Clean text - remove metadata, keep actual content.
    """
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)

    lines = text.split("\n")
    clean_lines = []

    for line in lines:
        line = line.strip()

        if len(line) < 8:
            continue

        if len(re.findall(r"[A-Za-z0-9]", line)) < 4:
            continue

        if re.match(r"^(ISBN|Copyright|Page \d+|Printed in|www\.|http|Contents|Chapter \d+)", line, re.I):
            continue

        if re.search(r"(thank you|acknowledgment|dedication|about the author)", line, re.I):
            continue

        clean_lines.append(line)

    return " ".join(clean_lines)


def _build_fallback_summary(text: str, max_chars: int = 420) -> str:
    """
    Build a lightweight extractive summary when model output is unavailable.
    """
    normalized = re.sub(r"\s+", " ", (text or "")).strip()
    if not normalized:
        return "Could not generate summary."

    sentences = re.split(r"(?<=[.!?])\s+", normalized)
    selected = []
    current_len = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        projected = current_len + len(sentence) + (1 if selected else 0)
        if projected > max_chars and selected:
            break
        selected.append(sentence)
        current_len = projected
        if len(selected) >= 3:
            break

    if not selected:
        words = normalized.split()
        selected_text = " ".join(words[: min(80, len(words))])
        return selected_text.strip()

    return " ".join(selected).strip()


def _sanitize_summary_output(summary: str) -> str:
    """
    Normalize model output so UI gets plain summary text.
    """
    cleaned = summary.strip()

    cleaned = re.sub(r"^\s*#{1,6}\s*", "", cleaned)
    cleaned = re.sub(
        r"^\s*(?:summary|brief summary|in summary)\s*[:\-–—]*\s*",
        "",
        cleaned,
        flags=re.I,
    )

    cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"\*(.*?)\*", r"\1", cleaned)
    cleaned = re.sub(r"__(.*?)__", r"\1", cleaned)
    cleaned = re.sub(r"_(.*?)_", r"\1", cleaned)
    cleaned = re.sub(r"^\s*[-*+]\s+", "", cleaned, flags=re.M)

    return cleaned.strip()


def generate_summary(text: str, max_length: int = 150) -> str:
    """
    Generate summary using Mistral AI model.

    Args:
        text: Full document text
        max_length: Approximate maximum output tokens

    Returns:
        Summary text
    """
    if not text or len(text.strip()) < 100:
        return "Document too short to summarize."

    from backend.utils.logger import get_logger

    logger = get_logger("OmniAI")

    clean_text = _clean_text(text)
    if len(clean_text.strip()) < 100:
        fallback_input = re.sub(r"\s+", " ", text).strip()
        if len(fallback_input) < 100:
            return "No meaningful content found to summarize."
        clean_text = fallback_input

    api_key = _get_mistral_api_key()
    if not api_key:
        return _build_fallback_summary(clean_text)

    model_name = MISTRAL_MODEL

    system_prompt = (
        "You are an expert summarizer. Create a comprehensive yet concise summary in one paragraph. "
        "Include all key points, main ideas, and important details. Be thorough but avoid unnecessary repetition."
    )
    user_prompt = (
        "Summarize the following text and focus only on the most important points.\n\n"
        f"Text:\n{clean_text[:12000]}"
    )

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
        "max_tokens": max(150, min(max_length, 500)),
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            MISTRAL_URL,
            headers=headers,
            json=payload,
            timeout=90,
        )
        response.raise_for_status()
        data = response.json()

        summary = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )

        summary = _sanitize_summary_output(summary)

        if not summary:
            return _build_fallback_summary(clean_text)

        return summary

    except Exception as error:
        logger.error(f"Summarization error (Mistral AI): {str(error)}")
        return _build_fallback_summary(clean_text)
