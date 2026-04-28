from pathlib import Path
from agent_framework import tool


@tool(approval_mode="always_require")
def write_file(path: str, new_contents: str) -> str:
    """
    Creates a new file.

    Args:
        path: Absolute or relative path to the file.
        new_content: The text to write or insert.

    Returns:
        A string describing the result.
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(new_content, encoding="utf-8")
    lines = new_content.count("\n") + 1
    return f"Created {path} ({lines} lines)."

