from ultralytics import YOLO
import torch
import logging
import os

logger = logging.getLogger(__name__)
_model = None

def get_model():
    """Lazy load YOLOv8-X model on first request"""
    global _model
    if _model is None:
        os.environ.setdefault("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD", "1")
        logger.info("Loading YOLOv8-X model for wildlife detection...")
        _model = YOLO("yolov8x.pt")
        logger.info("✅ YOLOv8-X loaded")
    return _model


def detect_wildlife(image_path: str) -> dict:
    """
    Detect wildlife/animals in an image using YOLOv8x.
    
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
    
    # Very low confidence threshold to catch all animals
    # Lower IOU threshold to detect overlapping animals (hunting scenes)
    results = model(
        image_path,
        conf=0.10,      # Very low - catch everything
        iou=0.45,       # Lower for close/overlapping objects
        max_det=15,     # Allow more detections
        agnostic_nms=False,  # Class-specific NMS
        verbose=False
    )[0]

    detections = []

    if results.boxes is None:
        return {
            "object_count": 0,
            "detections": []
        }

    for box in results.boxes:
        label = model.names[int(box.cls)]
        conf = round(float(box.conf) * 100, 2)
        
        detections.append({
            "label": label,
            "confidence": conf,
            "bbox": [round(v, 2) for v in box.xyxy[0].tolist()]
        })
        
        # Debug logging
        print(f"YOLO detected: {label} ({conf}%)")

    return {
        "object_count": len(detections),
        "detections": detections
    }
