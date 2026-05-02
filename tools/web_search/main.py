from agent_framework import tool
from ddgs import DDGS

@tool
def web_search(query: str) -> str:
    """Search the web for the top 10 results."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=10))
            
            if not results:
                return f"No results found for '{query}'."
                
            results_text = []
            for idx, item in enumerate(results):
                results_text.append(f"Result {idx+1}:\nTitle: {item['title']}\nURL: {item['href']}\nSummary: {item['body']}\n")
                
            return "\n".join(results_text)
    except Exception as e:
        return f"Web search failed: {e}"