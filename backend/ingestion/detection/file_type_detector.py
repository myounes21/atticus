from pathlib import Path

SUPPORTED_EXTENSIONS = {"pdf", "docx", "eml", "txt"}

def get_file_extension(file_path: str | Path) -> str:
    extension = Path(file_path).suffix.lower().lstrip(".")
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file extension for '{file_path}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )
    return extension

