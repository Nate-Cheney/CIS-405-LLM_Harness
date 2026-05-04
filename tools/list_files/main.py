import os
from agent_framework import tool
from pathlib import Path


@tool
def list_files(directory: str = ".") -> dict:
    """
    List files and directories in the specified path.

    Args:
        directory: Path to list (defaults to current directory)

    Returns:
        dict with 'path' and 'entries' keys.
        On failure, returns the same structure plus an 'error' string.

    Notes:
        - `directory` is treated as a literal filesystem path (not a shell command).
        - `~` is expanded to the current user's home directory.
        - On Windows, prefer forward slashes (e.g., `C:/Users`) to avoid JSON backslash escaping issues.
    """
    path = Path(directory).expanduser()

    try:
        if not path.exists():
            return {
                "path": str(path),
                "entries": [],
                "error": f"Path does not exist: {directory}",
            }

        if not path.is_dir():
            return {
                "path": str(path.resolve()),
                "entries": [],
                "error": f"Path is not a directory: {directory}",
            }

        entries = []
        for entry in sorted(path.iterdir(), key=lambda e: (e.is_file(), e.name.lower())):
            stat = entry.stat()
            entries.append({
                "name": entry.name,
                "type": "file" if entry.is_file() else "directory",
                "size_bytes": stat.st_size if entry.is_file() else None,
                "modified": stat.st_mtime,
            })

        return {
            "path": str(path.resolve()),
            "entries": entries,
        }
    except PermissionError:
        return {
            "path": str(path),
            "entries": [],
            "error": f"Permission denied: {directory}",
        }

