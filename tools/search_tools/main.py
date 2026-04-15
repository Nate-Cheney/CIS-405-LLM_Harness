from agent_framework import tool
import os


@tool
def search_tools(keyword: str, top_k: int = 5) -> list:
    """
    Searches the vector database for available tools based on a keyword.
    
    Args:
        tool_keyword: The keyword to search for related tools.
        top_k: The maximum number of tools to return.
    """


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

