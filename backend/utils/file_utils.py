from pathlib import Path
import shutil
import uuid
import re
from typing import Tuple

# Base temp directory
TEMP_DIR = Path("temp_uploads")
TEMP_DIR.mkdir(exist_ok=True)


def save_uploaded_file(upload_file) -> Tuple[str, Path]:
    """
    Save uploaded file safely to temp directory.

    Returns:
    - filename (str)
    - file_path (Path)
    """
    original_name = Path(upload_file.filename or "").name
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", original_name).strip("._")

    if not safe_name:
        raise ValueError("Invalid filename")

    unique_name = f"{uuid.uuid4()}_{safe_name}"
    file_path = TEMP_DIR / unique_name

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)

    return unique_name, file_path


def delete_file(file_path: Path) -> None:
    """
    Delete temp file safely.
    """
    try:
        if file_path.exists():
            file_path.unlink()
    except Exception:
        pass


def get_file_extension(filename: str) -> str:
    """
    Get file extension in lowercase.
    """
    return Path(filename).suffix.lower()
