from typing import List, Dict


def generate_explanation(
    input_type: str,
    selected_models: List[str],
    results: Dict
) -> Dict:
    """
    Generate a human-readable, truthful explanation of the AI decision process.
    """

    explanation = []

    # --------------------------------------------------
    # STEP 1: Input understanding
    # --------------------------------------------------
    explanation.append(f"The system received a {input_type} input.")

    # --------------------------------------------------
    # STEP 2: Model selection
    # --------------------------------------------------
    if not selected_models:
        explanation.append(
            "No AI models were executed because the input did not match any supported processing pipeline."
        )
        return {"explanation": "\n".join(explanation)}

    explanation.append(
        "Based on the input characteristics, the AI agent selected the following models:"
    )

    for model in selected_models:
        explanation.append(f"- {model.replace('_', ' ').title()}")

    explanation.append("")
    explanation.append("Each selected model contributed the following insights:")

    # --------------------------------------------------
    # IMAGE PIPELINE
    # --------------------------------------------------
    if "image_classification" in results:
        label = results["image_classification"].get("label", "unknown")
        confidence = results["image_classification"].get("confidence", 0.0)
        explanation.append(
            f"• Image Classification identified the overall scene as "
            f"'{label}' with {confidence:.2f}% confidence."
        )
        explanation.append("")

    if "object_detection" in results:
        detections = results["object_detection"].get("detections", [])
        explanation.append(
            f"• Object Detection located {len(detections)} object(s) within the image."
        )
        explanation.append("")

    if "ocr" in results:
        if results["ocr"].get("has_text"):
            char_count = len(results["ocr"].get("text", ""))
            explanation.append(
                f"• OCR successfully extracted readable text "
                f"({char_count} characters detected)."
            )
            explanation.append("")
        else:
            explanation.append(
                "• OCR was applied, but no readable text was found in the image."
            )
            explanation.append("")

    if "caption" in results:
        explanation.append(
            "• Vision–Language modeling generated a semantic description of the image content."
        )
        explanation.append("")

    # --------------------------------------------------
    # DOCUMENT PIPELINE (IMPORTANT FIX)
    # --------------------------------------------------
    if "document" in results:
        doc = results["document"]
        explanation.append(
            f"• Document AI analyzed the file as a {doc.get('type', 'document')} "
            f"using {doc.get('extraction_method', 'automatic analysis')}."
        )
        explanation.append("")

        if doc.get("summary"):
            explanation.append(
                "• A concise summary was generated to highlight the key content of the document."
            )
            explanation.append("")

    # --------------------------------------------------
    # TEXT PIPELINE
    # --------------------------------------------------
    if "translation" in results:
        explanation.append(
            "• Translation was applied  before further analysis."
        )
        explanation.append("")

    if "text_analytics" in results:
        sentiment = results["text_analytics"].get("sentiment", "unknown").lower()
        explanation.append(
            f"• Text Analytics identified an overall {sentiment} sentiment in the content."
        )
        explanation.append("")

    # --------------------------------------------------
    # FINAL TRUST STATEMENT
    # --------------------------------------------------
    explanation.append("")
    explanation.append("This transparent, step-by-step reasoning ensures interpretability.")
    explanation.append("It also builds trust in the AI system’s decisions.")

    return {
        "explanation": "\n".join(explanation)
    }


# ---------------- LOCAL TEST ----------------
if __name__ == "__main__":
    sample = generate_explanation(
        input_type="document",
        selected_models=["document_ai"],
        results={
            "document": {
                "type": "Text-based PDF",
                "extraction_method": "Direct Text Extraction",
                "summary": "This is a sample summary",
                "text_preview": "Lorem ipsum..."
            }
        }
    )

    print(sample["explanation"])
