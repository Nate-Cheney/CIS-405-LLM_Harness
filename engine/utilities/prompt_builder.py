import os
from pathlib import Path


class PromptBuilder:
    def __init__(self, studio_path: str = "workspace"):
        self.studio_path = Path(studio_path)

    def build_system_prompt(self) -> str:
        """
        Reads AGENT.md, MANDATE.md, and MEMORY.md and compiles them
        into a single system prompt.
        """
        system_instructions = []

        core_files = ["AGENT.md", "MANDATE.md", "MEMORY.md"]
        for filename in core_files:
            file_path = self.studio_path / filename
            if file_path.exists():
                with open(file_path, "r") as f:
                    content = f.read().strip()
                system_instructions.append(content)
        
        system_prompt = "\n\n".join(system_instructions).strip()
        
        return system_prompt

