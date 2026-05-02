import sqlite3
import sqlite_vec

from pathlib import Path


class MemoryManager:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.db_path = self.project_root / "Workspace" / "memory.db"

        self.embedding_model = SentenceTransformer(
           os.getenv("EMBEDDING_MODEL"),
           token=os.getenv("HF_TOKEN")
        )

        self._init_database()  # Init db and create self.connection object


    def parse_memory(self):
        """
        Function to parse session json files and add them to a memory db.
        """
        # TODO


    def search_memory(self):
        """
        Function to semantically search memory for relevant information.
        """
        continue
:q
    def _init_database(self, dimensions: int = 384) -> None:
        """
        Function to initialize the messages database.
        """
        
        # TODO: Create table schema
        
        # TODO: Parse sessions and insert



#if __name__ == "__main__":
#    mem_man = MemoryManager()

