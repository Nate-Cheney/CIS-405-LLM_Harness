from agent_framework import tool
import httpx

@tool
def wikipedia_summary(query: str) -> str:
    """
    Return a short plain-text summary from Wikipedia for the given search query.
    Example query: 'Python programming language'
    """
    try:
        slug = query.strip().replace(" ", "_")
        
        # Wikipedia requires a descriptive User-Agent with contact info
        # Format: AppName/Version (Contact Info)
        headers = {
            "User-Agent": "CIS-405-LLM_Harness/1.0 (mailto:ncheney29@lakers.mercyhurst.edu) httpx"
        }
        
        # Pass the headers to httpx.get
        resp = httpx.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{slug}",
            headers=headers,
            timeout=10,
        )
        
        if resp.status_code == 200:
            return resp.json().get("extract", f"No summary available for '{query}'.")
        return f"Wikipedia returned status {resp.status_code} for '{query}'."
        
    except Exception as e:
        return f"Wikipedia lookup failed: {e}"