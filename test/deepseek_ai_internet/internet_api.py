import requests
from bs4 import BeautifulSoup
import json

def search_web(query, num_results = 5):
    """
    perform a web search using search API.
    Args:
        query (str): the query to search for.
        num_results (int): the number of results to return.
    
    Returns:
        list: a list of search results.
    
    """
    #Option 1 : Use a seaerch API like google search api or any other search api like bing api or serpAPI

    engin_id= "f23e5206f6f7e4286"

    api_key = "AIzaSyAozAnezuAdzjVBtvibZnEAv5NvSVR47vs"
    
    search_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "q": query,
        "key": api_key,
        "cx": engin_id,
        "num": num_results  # Max 10 results per request
    }

    try:
        response = requests.get(search_url, params=params, timeout=10)
        response.raise_for_status()
        search_results = response.json().get("items", [])
        return search_results
    except Exception as e:
        print(f"Google search error: {str(e)}")
        return []

    
def fetch_webpage(url):
    """fetch and parse content from a webpage."""

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        if "enable Javascript" in response.text:
            print(f"skipping Javascript-dependent webpage: {url}")
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        #extract main content ( this is simplified - real implimentation would be more robust)
        main_text = soup.get_text(separator="\n", strip=True)
        return main_text
    except Exception as e:
        print(f"Error fetching webpage: {str(e)}")
        return None
    

if __name__ == "__main__":
    # Test search_web
    query = "what time is it in tunisia?"
    results = search_web(query, num_results=5)
    print(f"Found {len(results)} results for '{query}':")
    for idx, result in enumerate(results, 1):
        print(f"{idx}. {result.get('title')} - {result.get('link')}")

    # Test fetch_webpage with the first result
    if results:
        test_url = results[0].get("link")
        print(f"\nFetching content from: {test_url}")
        content = fetch_webpage(test_url)
        if content:
            print("\nSample content (first 500 characters):\n")
            print(content[:500])