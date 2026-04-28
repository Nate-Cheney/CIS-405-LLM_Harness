from pathlib import Path
from agent_framework import tool


@tool
def read_file(path: str) -> str:
    """
    Reads the contents of a file.

    Args:
        path: Absolute or relative path to the file.

    Returns:
        Numbered contents of a file.
    """
    file_path = Path(path)
    
    if not file_path.exists():
        return f"ERROR: File not found: {path}"

    content = file_path.read_text(encoding="utf-8")
    numbered = "\n".join(
        f"{i + 1}\t{line}" for i, line in enumerate(content.splitlines())
    )
    return f"File: {path}\n\n{numbered}"

