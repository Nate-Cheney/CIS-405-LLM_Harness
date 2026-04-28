from agent_framework import tool
import numpy as np
from pathlib import Path
import os
from sentence_transformers import SentenceTransformer
import sqlite3
import sqlite_vec


try:
    embedding_model
except NameError:
    embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

@tool
def search_tools(keyword: str, top_k: int = 5, tools_directory: str = "tools") -> list:
    """
    Searches the vector database for available tools based on a keyword.
    
    Args:
        keyword: The keyword to search for related tools.
        top_k: The maximum number of tools to return.
        tools_directory: The relative path to the tools directory.
    """
    # Init necessary variables
    # Assumes file is at project_root/tools/search_tools/main.py
    tools_dir = Path(__file__).parent.parent.parent / tools_directory
    db_path = tools_dir / "tools.db"
    
    connection = sqlite3.connect(db_path)
    connection.enable_load_extension(True)
    sqlite_vec.load(connection)
    connection.enable_load_extension(False)
    cursor = connection.cursor()
    
    # Embed search query - using 'keyword' consistently
    query_vector = embedding_model.encode(keyword)
    query_bytes = np.array(query_vector, dtype=np.float32).tobytes()
        
    # Query description 
    cursor.execute("""
        SELECT 
            t.tool_name, 
            t.is_core,
            t.description, 
            v.distance 
        FROM vec_tools v
        JOIN tools t ON t.id = v.id
        WHERE v.description_embedding MATCH ? AND k = ?
    """, (query_bytes, top_k))
    description_results = cursor.fetchall()
        
    # Query keywords 
    cursor.execute("""
        SELECT 
            t.tool_name, 
            t.is_core,
            t.description, 
            v.distance 
        FROM vec_tools v
        JOIN tools t ON t.id = v.id
        WHERE v.keywords_embedding MATCH ? AND k = ?
    """, (query_bytes, top_k))
    keyword_results = cursor.fetchall()

    # Combine, deduplicate, and format
    unique_tools = {}
    for row in description_results + keyword_results:
        tool_name = row[0]
        distance = row[3]
            
        if tool_name in unique_tools:
            unique_tools[tool_name]["distance"] = min(unique_tools[tool_name]["distance"], distance)
        else:
            unique_tools[tool_name] = {
                "tool_name": tool_name,
                "is_core": bool(row[1]),
                "description": row[2],
                "distance": distance
            }
        
    matched_tools = list(unique_tools.values())        
    matched_tools.sort(key=lambda x: x["distance"])
    
    connection.close() 
    print(f"Found {len(matched_tools)} tools.")

    return "\n".join([f"- {t['tool_name']}: {t['description']}" for t in matched_tools])

