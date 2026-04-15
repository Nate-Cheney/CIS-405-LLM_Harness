from agent_framework import tool
import os

@tool
def write_file(filepath: str, contents: str) -> str:
    """
    Writes a given string to a file.
    """
    if not os.path.exists(filepath):
        return "File not found."
    with open(filepath, "w") as f:
        f.write(contents)
        return "Contents written."

