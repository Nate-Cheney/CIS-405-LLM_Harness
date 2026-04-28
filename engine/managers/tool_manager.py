import importlib.util 
import json
import numpy as np
import os
import sqlite3
import sqlite_vec

from pathlib import Path
from sentence_transformers import SentenceTransformer


class ToolManager:
    def __init__(self, tools_directory: str = "tools"):
        self.tools_dir = Path(__file__).parent.parent.parent / tools_directory
        self.db_path = Path(f"{self.tools_dir}/tools.db")

        self.embedding_model = SentenceTransformer(
            os.getenv("EMBEDDING_MODEL"),
            token=os.getenv("HF_TOKEN")
        )

        self.core_tools = [] 
        self.loaded_tools = {}

        self._init_database()  # Init db and create self.connection object
        self._load_tools()

    def close_db_connection(self):
        if self.connection:
            self.connection.close()

    def search_tools(self, tool_keyword: str, top_k: int = 5):
        """
        Function to query tool database by keyword using semantic vector search.
        """
        # Embed search query
        query_vector = self.embedding_model.encode(tool_keyword)
        query_bytes = np.array(query_vector, dtype=np.float32).tobytes()
       
        # Query description 
        self.cursor.execute("""
            SELECT 
                t.tool_name, 
                t.is_core,
                t.description, 
                v.distance 
            FROM vec_tools v
            JOIN tools t ON t.id = v.id
            WHERE v.description_embedding MATCH ? AND k = ?
        """, (query_bytes, top_k))
        description_results = self.cursor.fetchall()
        
        # Query description 
        self.cursor.execute("""
            SELECT 
                t.tool_name, 
                t.is_core,
                t.description, 
                v.distance 
            FROM vec_tools v
            JOIN tools t ON t.id = v.id
            WHERE v.keywords_embedding MATCH ? AND k = ?
        """, (query_bytes, top_k))
        keyword_results = self.cursor.fetchall()

        # Combine, deduplicate, and format
        unique_tools = {}
        for row in description_results + keyword_results:
            tool_name = row[0]
            distance = row[3]
            
            if tool_name in unique_tools:
                # If tool already exists, update to the lower distance
                unique_tools[tool_name]["distance"] = min(unique_tools[tool_name]["distance"], distance)
            else:
                unique_tools[tool_name] = {
                    "tool_name": tool_name,
                    "is_core": bool(row[1]),
                    "description": row[2],
                    "distance": distance
                }
        
        matched_tools = list(unique_tools.values())        
        matched_tools.sort(key=lambda x: x["distance"])  # Re-sort by distance
        
        return matched_tools[:top_k]

    def _init_database(self, dimensions: int = 384) -> None:
        """
        Helper function to initialize the tools database.
        """
        self.connection = sqlite3.connect(self.db_path)

        self.connection.enable_load_extension(True)
        sqlite_vec.load(self.connection)
        self.connection.enable_load_extension(False)

        self.cursor = self.connection.cursor()
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS tools (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tool_name TEXT UNIQUE NOT NULL,
                is_core BOOLEAN,
                description TEXT,
                keywords TEXT
            )
        """)

        self.cursor.execute(f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS vec_tools USING vec0(
                id INTEGER PRIMARY KEY, 
                description_embedding FLOAT[{dimensions}],
                keywords_embedding FLOAT[{dimensions}]
            )
        """)

        self.connection.commit()
    
    def _load_tools(self) -> None:
        """
        Function to load tools into a SQLite database for searching.
        """
        if not self.tools_dir.exists():
            print("The tools directory does not exist.")
            return 

        # Iterate through all subdirectories in the tools folder
        for tool_folder in self.tools_dir.iterdir():
            if not tool_folder.is_dir():
                continue
            self._load_tool(tool_folder)

    def _load_tool(self, tool_folder: str) -> None:
        """
        Helper function to load a single tool.
        Tool is: 
        - Opened & parsed
        - Added to the tool db
        - Imported into the Python runtime
        """
        config_path = tool_folder / "config.json"
        main_path = tool_folder / "main.py"

        # Skip folders that don't conform to the manifest structure
        if not config_path.exists() or not main_path.exists():
            return 

        # Read config file
        try:
            with open(config_path, "r") as f:
                manifest = json.load(f)
        except json.JSONDecodeError:
            print(f"Invalid JSON in {config_path}")
            return

        tool_name = manifest.get("name", tool_folder.name)
        is_core = manifest.get("is_core", False)
        description = manifest.get("description", "")
        keywords = manifest.get("keywords", [])
        
        # Embed description and keywords
        description_vector = self.embedding_model.encode(description)
    
        keywords_joined = ", ".join(keywords)
        keyword_vector = self.embedding_model.encode(keywords_joined)
        keywords_str = json.dumps(keywords)

        # Save data to database
        # UPSERT into the tools table
        self.cursor.execute("""
            INSERT INTO tools (tool_name, is_core, description, keywords)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(tool_name) DO UPDATE SET 
                is_core = excluded.is_core,
                description = excluded.description,
                keywords = excluded.keywords
            RETURNING id; 
        """, (tool_name, is_core, description, keywords_str))
        
        actual_id = self.cursor.fetchone()[0]
        
        # Convert both vectors to float32 bytes
        description_bytes = np.array(description_vector, dtype=np.float32).tobytes()
        keyword_bytes = np.array(keyword_vector, dtype=np.float32).tobytes()
        
        # UPSERT into the vec_tools table
        self.cursor.execute("""
            DELETE FROM vec_tools WHERE id = ?;
        """, (actual_id,))
        
        self.cursor.execute("""
            INSERT INTO vec_tools (id, description_embedding, keywords_embedding) 
            VALUES (?, ?, ?);
        """, (actual_id, description_bytes, keyword_bytes))

        self.connection.commit()

        # Dynamically import the main.py module
        try:
            # Create a specification for the module based on its file location
            module_name = f"dynamic_tools.{tool_name}"
            spec = importlib.util.spec_from_file_location(module_name, main_path)
                
            # Create the actual module from the spec
            module = importlib.util.module_from_spec(spec)
            
            # Inject the embedding_model into search_tools
            if tool_name == "search_tools":
                module.embedding_model = self.embedding_model

            # Execute the module (runs the code in main.py, applying the @tool decorators)
            spec.loader.exec_module(module)

            # Extract the tool function
            tool_function = getattr(module, tool_name, None) 

            if tool_function:
                print(f"Successfully loaded tool: {tool_name}")
                
                if is_core:
                    self.core_tools.append(tool_function)

                self.loaded_tools[tool_name] = tool_function

            else:
                print(f"Could not find a valid entry function in {main_path}.")

        except Exception as e:
            print(f"Failed to load tool {tool_name} from {main_path}: {e}")

