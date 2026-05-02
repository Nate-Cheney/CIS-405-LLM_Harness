import importlib.util
import json
import os

from pathlib import Path


class ToolManager:
    def __init__(self, tools_directory: str = "tools"):
        self.tools_dir = Path(__file__).parent.parent.parent / tools_directory
        self.tools = []
        self.loaded_tools = {}
        self._load_tools()

    def _load_tools(self) -> None:
        """
        Function to load tools into a SQLite database for searching.
        """
        if not self.tools_dir.exists():
            print("The tools directory does not exist.")
            return

        # Iterate through all subdirectories in the tools folder
        for tool_folder in sorted(self.tools_dir.iterdir()):
            if not tool_folder.is_dir():
                continue
            self._load_tool(tool_folder)

    def _load_tool(self, tool_folder: str) -> None:
        """
        Helper function to load a single tool.
        Tool is:
        - Opened & parsed
        - Imported into the Python runtime
        """
        config_path = tool_folder / "config.json"
        main_path = tool_folder / "main.py"

        # Skip folders that don't conform to the manifest structure
        if not config_path.exists() or not main_path.exists():
            print(f"Skipping {tool_folder.name}: missing config.json or main.py")
            return

        # Read config file
        try:
            with open(config_path, "r") as f:
                manifest = json.load(f)
        except json.JSONDecodeError:
            print(f"Invalid JSON in {config_path}")
            return

        tool_name = manifest.get("name", tool_folder.name)

        # Dynamically import the main.py module
        try:
            # Create a specification for the module based on its file location
            module_name = f"dynamic_tools.{tool_name}"
            spec = importlib.util.spec_from_file_location(module_name, main_path)

            # Create the actual module from the spec
            module = importlib.util.module_from_spec(spec)

            # Execute the module (runs the code in main.py, applying the @tool decorators)
            spec.loader.exec_module(module)

            # Extract the tool function
            tool_function = getattr(module, tool_name, None)

            if tool_function:
                print(f"Successfully loaded tool: {tool_name}")
                self.tools.append(tool_function)
                self.loaded_tools[tool_name] = tool_function

            else:
                print(f"Could not find a valid entry function in {main_path}.")

        except Exception as e:
            print(f"Failed to load tool {tool_name} from {main_path}: {e}")

