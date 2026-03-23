from pathlib import Path
from backend.core.constants import DOCUMENT_TYPES

_SUPPORTED_EXTENSIONS = set(DOCUMENT_TYPES)

def get_file_extension(file_path: str | Path) -> str:
    extension = Path(file_path).suffix.lower().lstrip(".")
    if extension not in _SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file extension for '{file_path}'. Supported: {', '.join(sorted(_SUPPORTED_EXTENSIONS))}"
        )
    return extension

