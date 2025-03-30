import requests
from bs4 import BeautifulSoup
import json
import re
from typing import List, Tuple

class EricaAI:
    def __init__(self):
        # API configurations
        self.ACCOUNT_ID = "db5d0abbbab31174a76149945ff13959"
        self.AUTH_TOKEN = "2xsmQlhaHey5Z7TaZzXOiw3QP-7R1N37fdye7-Lf"
        self.AI_ENDPOINT = f"https://api.cloudflare.com/client/v4/accounts/{self.ACCOUNT_ID}/ai/run/@cf/deepseek-ai/deepseek-r1-distill-qwen-32b"
        
        # Search configurations
        self.search_engine_id = "f23e5206f6f7e4286"
        self.google_api_key = "AIzaSyAozAnezuAdzjVBtvibZnEAv5NvSVR47vs"
        
        # Conversation management
        self.conversation_history = [
            {
                "role": "system",
                "content": "You are Erica, a cheerful anime girl assistant. Use cute emoticons and anime mannerisms. "
                           "When you need information, output <search>query</search>. Keep internal thinking in <think> tags "
                           "that are NEVER shown. Always end responses naturally and await user input."
            }
        ]
        self.max_search_depth = 3

    def search_web(self, query: str, num_results: int = 3) -> List[dict]:
        """Perform web search using Google Custom Search API"""
        params = {
            "q": query,
            "key": self.google_api_key,
            "cx": self.search_engine_id,
            "num": num_results
        }
        try:
            response = requests.get("https://www.googleapis.com/customsearch/v1", params=params, timeout=15)
            response.raise_for_status()
            return response.json().get("items", [])
        except Exception as e:
            print(f"🔍 Search error: {str(e)}")
            return []

    def fetch_webpage(self, url: str) -> str:
        """Fetch and clean webpage content"""
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"}
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            if "enable Javascript" in response.text:
                return ""
                
            soup = BeautifulSoup(response.text, "html.parser")
            return soup.get_text(separator="\n", strip=True)
        except Exception as e:
            print(f"🌐 Fetch error: {str(e)}")
            return ""

    def _clean_content(self, raw_content: str) -> str:
        """Simplify and clean webpage content"""
        # Basic cleaning - remove extra whitespace and truncate
        cleaned = re.sub(r'\n+', '\n', raw_content).strip()
        return cleaned[:2000]  # Keep within token limits

    def _process_response(self, raw_response: str) -> Tuple[str, List[str]]:
        """Extract search queries and clean the response"""
        # Remove all think tags and their content
        cleaned = re.sub(r'<think>.*?</think>', '', raw_response, flags=re.DOTALL)
        
        # Extract search queries
        search_queries = re.findall(r'<search>(.*?)</search>', cleaned, re.DOTALL)
        
        # Remove search tags from visible response
        cleaned = re.sub(r'</?search>', '', cleaned).strip()
        
        return cleaned, [q.strip() for q in search_queries]

    def _handle_search_round(self, query: str) -> str:
        """Process a single search query and return cleaned results"""
        results = self.search_web(query)
        if not results:
            return "No information found 😞"
        
        content = self.fetch_webpage(results[0].get("link"))
        if not content:
            return "Couldn't access the information 💦"
        
        return self._clean_content(content)

    def chat_round(self, user_input: str) -> str:
        """Handle one complete interaction cycle"""
        self.conversation_history.append({"role": "user", "content": user_input})
        
        search_depth = 0
        final_response = ""
        
        while search_depth < self.max_search_depth:
            # Generate AI response
            response = requests.post(
                self.AI_ENDPOINT,
                headers={"Authorization": f"Bearer {self.AUTH_TOKEN}", "Accept": "text/event-stream"},
                json={"messages": self.conversation_history, "max_tokens": 4096, "temperature": 0.7, "stream": True},
                stream=True
            )

            if response.status_code != 200:
                return f"❌ Error: {response.status_code} - {response.text}"

            # Process streaming response
            full_response = ""
            print("\n🎀 Erica: ", end="", flush=True)
            for chunk in response.iter_lines():
                if chunk:
                    decoded = chunk.decode('utf-8').strip()
                    if decoded == "data: [DONE]":
                        break
                    if decoded.startswith("data: "):
                        try:
                            data = json.loads(decoded[6:])
                            if "response" in data:
                                print(data["response"], end='', flush=True)
                                full_response += data["response"]
                        except json.JSONDecodeError:
                            continue

            # Process response and check for searches
            cleaned_response, search_queries = self._process_response(full_response)
            
            if not search_queries:
                # Final response
                self.conversation_history.append({"role": "assistant", "content": cleaned_response})
                return cleaned_response
            
            # Process all search queries
            search_results = []
            for query in search_queries:
                result = self._handle_search_round(query)
                search_results.append(f"Search results for '{query}':\n{result}")
                
                # Add results to context
                self.conversation_history.append({
                    "role": "system",
                    "content": f"Here's cleaned web information: {result}\nPlease use this to help the user!"
                })
                
                search_depth += 1
                
            # Regenerate response with search context
            continue
            
        return cleaned_response or "Hmm, let's try a different approach! 💡"

if __name__ == "__main__":
    erica = EricaAI()
    print("🌸 Welcome to Erica Chat! Type 'exit' to end the conversation.\n")
    
    while True:
        try:
            user_input = input("\n💬 You: ")
            if user_input.lower() in ['exit', 'quit']:
                print("\n🌸 Erica: See you later! Come back anytime! (´• ω •`)ﾉ")
                break
                
            response = erica.chat_round(user_input)
            
        except KeyboardInterrupt:
            print("\n🌸 Erica: Oops! Did I surprise you? (⁄ ⁄>⁄ ▽ ⁄<⁄ ⁄)")
            break