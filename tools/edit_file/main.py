import json
import re
from pathlib import Path
from agent_framework import tool


@tool(approval_mode="always_require")
def edit_file(
    path: str,
    command: str,
    old_str: str = "",
    new_str: str = "",
    insert_line: int = None,
    new_content: str = "",
) -> str:
    """
    Edit the contents of a file.

    Args:
        path: Absolute or relative path to the file.
        command:      Either: 'str_replace' or 'insert'
        old_str:      [str_replace] The exact string to find and replace.
        new_str:      [str_replace] The replacement string (empty = delete old_str).
        insert_line:  [insert] Line number AFTER which to insert new_content (0 = prepend).
        new_content:  [insert] The text to write or insert.

    Returns:
        A string describing the result, or file content for 'view'.
    """
    file_path = Path(path)
    
    if not file_path.exists():
        return f"ERROR: File not found: {path}"

    if command == "str_replace":
        if not old_str:
            return "ERROR: old_str must not be empty for str_replace."

        content = file_path.read_text(encoding="utf-8")
        occurrences = content.count(old_str)

        if occurrences == 0:
            return (
                f"ERROR: old_str not found in {path}.\n \
                Tip: use the 'read_file' tool to check the file content."
            )

        if occurrences > 1:
            return (
                f"ERROR: old_str found {occurrences} times in {path} — it must be unique.\n \
                Tip: expand old_str to include more surrounding context."
            )

        updated = content.replace(old_str, new_str, 1)
        file_path.write_text(updated, encoding="utf-8")
        action = "Replaced" if new_str else "Deleted"
        return f"{action} 1 occurrence in {path}."
    

    if command == "insert":
        if insert_line is None:
            return "ERROR: insert_line is required for the 'insert' command."

        lines = file_path.read_text(encoding="utf-8").splitlines(keepends=True)
        total = len(lines)

        if not (0 <= insert_line <= total):
            return (
                f"ERROR: insert_line {insert_line} is out of range (0–{total}). \
                Tip: use the 'read_file' tool to check the file content."
            )

        # Ensure new_content ends with a newline so it forms a complete line
        block = new_content if new_content.endswith("\n") else new_content + "\n"
        lines.insert(insert_line, block)
        file_path.write_text("".join(lines), encoding="utf-8")
        return f"Inserted content after line {insert_line} in {path}."

    return f"ERROR: Unknown command '{command}'. Valid commands: str_replace or insert."

