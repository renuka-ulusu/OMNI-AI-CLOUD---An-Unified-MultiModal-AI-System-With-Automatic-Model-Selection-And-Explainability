from ultralytics import YOLO
import torch
import logging
import os

logger = logging.getLogger(__name__)
_model = None

def get_model():
    """Lazy load YOLOv8 model on first request"""
    global _model
    if _model is None:
        os.environ.setdefault("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD", "1")
        logger.info("Loading YOLOv8-nano model...")
        _model = YOLO("yolov8n.pt")
        logger.info("✅ YOLOv8-nano loaded")
    return _model

# ---------------- MAIN FUNCTION ----------------
def detect_objects(image_path: str) -> dict:
    """
    Detect objects in an image.

    Returns:
    {
        "object_count": int,
        "detections": [
            {
                "label": str,
                "confidence": float,
                "bbox": [x1, y1, x2, y2]
            }
        ]
    }
    """

    # Get lazy-loaded model
    model = get_model()
    
    # Adjust detection parameters for better multi-object detection
    results = model(
        image_path,
        conf=0.20,      # Lower threshold to catch more objects
        iou=0.5,        # Lower IOU for overlapping objects
        max_det=10,     # Allow multiple detections
        verbose=False
    )[0]

    detections = []

    if results.boxes is None:
        return {
            "object_count": 0,
            "detections": []
        }

    for box in results.boxes:
        detections.append({
            "label": model.names[int(box.cls)],
            "confidence": round(float(box.conf) * 100, 2),
            "bbox": [round(v, 2) for v in box.xyxy[0].tolist()]
        })

    return {
        "object_count": len(detections),
        "detections": detections
    }


# ---------------- LOCAL TEST ----------------
if __name__ == "__main__":
    output = detect_objects("test.jpg")
    print(output)
