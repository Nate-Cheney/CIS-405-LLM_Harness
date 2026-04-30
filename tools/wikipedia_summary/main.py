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
        resp = httpx.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{slug}",
            timeout=8,
        )
        if resp.status_code == 200:
            return resp.json().get("extract", "No summary available.")
        return f"Wikipedia returned status {resp.status_code} for '{query}'."
    except Exception as exc:
        return f"Wikipedia lookup failed: {exc}"
