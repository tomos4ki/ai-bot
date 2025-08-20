# --- assets/commands/tools/search_tool.py ---
import logging
try:
    from duckduckgo_search import DDGS
except ImportError:
    print("🔴 The 'duckduckgo-search' library is required for the search tool.")
    print("   Please install it by running: pip install duckduckgo-search")
    DDGS = None

logger = logging.getLogger("discord.bot.tools.search")

def search_the_web(query: str) -> str:
    """
    Performs a web search using DuckDuckGo and returns summarized results.
    """
    if not DDGS:
        return "Search library is not installed. Please contact the bot owner."

    logger.info(f"Executing web search with query: '{query}'")
    try:
        with DDGS() as ddgs:
            # Get 5 results for a good balance of context and speed
            results = list(ddgs.text(query, max_results=5))
        
        if not results:
            logger.warning(f"Search for '{query}' returned no results.")
            return "No results found for that query."

        # Format the results into a clean, readable string for the AI
        formatted_results = "\n\n".join(
            f"Title: {res['title']}\nLink: {res['href']}\nSnippet: {res['body']}"
            for res in results
        )
        logger.info(f"Search for '{query}' returned {len(results)} results.")
        return formatted_results
    except Exception as e:
        logger.error(f"Error during web search for query '{query}': {e}", exc_info=True)
        return f"An error occurred during the search: {e}"