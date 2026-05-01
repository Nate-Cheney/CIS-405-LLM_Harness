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
        dict with 'path' and 'entries' keys

    Raises:
        NotADirectoryError: If the path exists but is not a directory
        FileNotFoundError: If the path does not exist
        PermissionError: If the process lacks permission to read the directory
    """
    path = Path(directory)

    if not path.exists():
        raise FileNotFoundError(f"Path does not exist: {directory}")

    if not path.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {directory}")

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

