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
        On failure, returns a string starting with "ERROR:" describing the issue.

    Notes:
        - `path` is treated as a literal filesystem path (not a shell command).
        - `~` is expanded to the current user's home directory.
        - On Windows, prefer forward slashes (e.g., `C:/Users/Alice/.bashrc`) to avoid JSON backslash escaping issues.
    """
    file_path = Path(path).expanduser()

    try:
        if not file_path.exists():
            return f"ERROR: File not found at path: {path}"

        if file_path.is_dir():
            return f"ERROR: Path is a directory, not a file: {path}"

        content = file_path.read_text(encoding="utf-8")
        numbered = "\n".join(
            f"{i + 1}\t{line}" for i, line in enumerate(content.splitlines())
        )
        return f"File: {str(file_path)}\n\n{numbered}"
    except PermissionError:
        return f"ERROR: Permission denied reading file: {path}"
    except UnicodeDecodeError:
        return f"ERROR: File is not valid UTF-8 text: {path}"

