from PIL import Image
import numpy as np
from typing import Tuple


def load_image(image_path: str) -> Image.Image:
    """
    Load image and convert to RGB.
    """
    image = Image.open(image_path)
    if image.mode != "RGB":
        image = image.convert("RGB")
    return image


def resize_image(
    image: Image.Image,
    size: Tuple[int, int] = (224, 224)
) -> Image.Image:
    """
    Resize image while keeping compatibility with CNN models.
    """
    return image.resize(size)


def image_to_numpy(image: Image.Image) -> np.ndarray:
    """
    Convert PIL Image to NumPy array.
    """
    return np.array(image)


def preprocess_for_ocr(image: Image.Image) -> Image.Image:
    """
    Light preprocessing for OCR:
    - Grayscale
    - Contrast normalization
    """
    gray = image.convert("L")
    return gray
