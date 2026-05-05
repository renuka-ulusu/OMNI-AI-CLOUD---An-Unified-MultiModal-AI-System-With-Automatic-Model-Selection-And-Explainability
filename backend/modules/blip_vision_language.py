from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image
from typing import Dict

# ---------------- MODEL ----------------
# Lazy load - models will be initialized on first use
_processor = None
_model = None


def _get_blip_models():
    """
    Lazy load BLIP processor and model on first use.
    Prevents 24GB+ download on app import.
    """
    global _processor, _model
    if _processor is None or _model is None:
        _processor = BlipProcessor.from_pretrained(
            "Salesforce/blip-image-captioning-large"
        )
        _model = BlipForConditionalGeneration.from_pretrained(
            "Salesforce/blip-image-captioning-large"
        )
    return _processor, _model


def initialize_blip_model() -> None:
    """
    Pre-initialize BLIP model at app startup.
    This prevents 24+ minute delays on first request.
    """
    from backend.utils.logger import get_logger
    logger = get_logger("OmniAI")
    
    logger.info("Pre-initializing BLIP vision-language model...")
    _get_blip_models()
    logger.info("BLIP model initialized successfully")


# ---------------- MAIN FUNCTION ----------------
def generate_image_caption(image_path: str, prompt: str = None) -> Dict:
    """
    Generate a detailed human-readable caption for an image.

    Args:
        image_path: Path to the image
        prompt: Optional text prompt to guide caption generation
        
    Returns:
    {
        "caption": str
    }
    """
    
    processor, model = _get_blip_models()
    image = Image.open(image_path).convert("RGB")

    # Use conditional caption generation if prompt provided
    if prompt:
        inputs = processor(
            images=image,
            text=prompt,
            return_tensors="pt"
        )
    else:
        inputs = processor(
            images=image,
            return_tensors="pt"
        )

    # Generate with improved parameters for more detailed captions
    output = model.generate(
        **inputs,
        max_length=80,          # Longer captions
        min_length=20,          # More descriptive minimum
        num_beams=8,            # More beam search for better quality
        length_penalty=1.2,     # Encourage longer descriptions
        repetition_penalty=2.0, # Reduced to allow natural repetition
        no_repeat_ngram_size=2, # Allow some phrase repetition
        early_stopping=True,
        temperature=0.7,        # More creative descriptions
        do_sample=False         # Deterministic for consistency
    )

    caption = processor.decode(
        output[0],
        skip_special_tokens=True
    )

    # Post-processing: Remove consecutive repeated words
    caption = _remove_repeated_words(caption)
    
    # Capitalize first letter
    if caption:
        caption = caption[0].upper() + caption[1:] if len(caption) > 1 else caption.upper()

    return {
        "caption": caption
    }


def _remove_repeated_words(text: str) -> str:
    """
    Remove consecutive repeated words from text.
    E.g., "a bottle supplement supplement supplement" -> "a bottle supplement"
    """
    words = text.split()
    if not words:
        return text
    
    result = [words[0]]
    for word in words[1:]:
        if word.lower() != result[-1].lower():
            result.append(word)
    
    return " ".join(result)


# ---------------- LOCAL TEST ----------------
if __name__ == "__main__":
    result = generate_image_caption("test.jpg")
    print(result)
