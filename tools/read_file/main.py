from agent_framework import tool
import os


@tool
def read_file(filepath: str) -> str:
    """
    Reads the contents of a file.
    """
    if not os.path.exists(filepath):
        return "File not found."
    with open(filepath, "r") as f:
        return f.read()

