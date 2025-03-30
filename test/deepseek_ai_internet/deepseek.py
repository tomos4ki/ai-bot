import requests
import json
from bs4 import BeautifulSoup
import re

class EricaAI:
    def __init__(self):
        # Cloudflare AI Configuration
        self.ACCOUNT_ID = "db5d0abbbab31174a76149945ff13959"
        self.AUTH_TOKEN = "2xsmQlhaHey5Z7TaZzXOiw3QP-7R1N37fdye7-Lf"
        self.AI_ENDPOINT = f"https://api.cloudflare.com/client/v4/accounts/{self.ACCOUNT_ID}/ai/run/@cf/deepseek-ai/deepseek-r1-distill-qwen-32b"
        
        # Google Search Configuration
        self.search_engine_id = "f23e5206f6f7e4286"
        self.google_api_key = "AIzaSyAozAnezuAdzjVBtvibZnEAv5NvSVR47vs"
        
        # Conversation History
        self.conversation_history = [
            {"role": "system", 
             "content": "You are Erica, a cheerful anime girl assistant. Use cute emoticons and anime mannerisms. Be helpful but maintain your character."
                        "when you need real time inforation, use <search>query</search> tags."
                        "keep internal thinking in <think></think> tags."},     
        ]

    def search_web(self, query, num_results=5):
        """Perform web search using Google Custom Search API"""
        params = {
            "q": query,
            "key": self.google_api_key,
            "cx": self.search_engine_id,
            "num": num_results
        }
        try:
            response = requests.get("https://www.googleapis.com/customsearch/v1", 
                                   params=params, 
                                   timeout=15)
            response.raise_for_status()
            return response.json().get("items", [])
        except Exception as e:
            print(f"🔍 Search error: {str(e)}")
            return []

    def fetch_webpage(self, url):
        """Fetch and clean webpage content"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            if "enable Javascript" in response.text:
                return None
                
            soup = BeautifulSoup(response.text, "html.parser")
            return soup.get_text(separator="\n", strip=True)
        except Exception as e:
            print(f"🌐 Fetch error: {str(e)}")
            return None

    def _clean_response(self, response_text):
        """Remove internal tags and process search requests"""
        # Remove thinking blocks first
        cleaned = re.sub(r'<think>.*?</think>', '', response_text, flags=re.DOTALL)
        
        # Process search tags
        search_performed = False
        while '<search>' in cleaned and '</search>' in cleaned:
            search_performed = True
            start = cleaned.index('<search>') + len('<search>')
            end = cleaned.index('</search>', start)
            search_query = cleaned[start:end].strip()
            
            # Perform search and update context
            search_results = self.search_web(search_query)
            if search_results:
                content = self.fetch_webpage(search_results[0].get("link"))
                if content:
                    self.conversation_history.append({
                        "role": "system",
                        "content": f"Search results for '{search_query}':\n{content[:2000]}"
                    })
            
            # Remove the search tags
            cleaned = cleaned[:start-len('<search>')] + cleaned[end+len('</search>'):]

        return cleaned.strip(), search_performed

    def chat(self, user_input, max_searches=2):
        """Main chat interface with search capabilities"""
        self.conversation_history.append({"role": "user", "content": user_input})
        
        searches_performed = 0
        final_response = ""
        
        while searches_performed <= max_searches:
            # Generate AI response
            response = requests.post(
                self.AI_ENDPOINT,
                headers={
                    "Authorization": f"Bearer {self.AUTH_TOKEN}",
                    "Accept": "text/event-stream"
                },
                json={
                    "messages": self.conversation_history,
                    "max_tokens": 4096,
                    "temperature": 0.7,
                    "stream": True
                },
                stream=True
            )

            if response.status_code != 200:
                print(f"❌ Error: {response.status_code}\n{response.text}")
                return None

            # Process streaming response
            full_response = ""
            print("\n🎀 Erica: ", end="", flush=True)

            buffer=""
            for chunk in response.iter_lines():
                if chunk:
                    # Decode the chunk and handle the stream(SSE Format)
                    decoded_chunk = chunk.decode('utf-8').strip()

                    if decoded_chunk == "Data: [DONE]":
                        break
                    
                    if decoded_chunk.startswith("data: "):
                        try:
                            data = json.loads(decoded_chunk[6:])# Remove "data: " prefix
                            if "response" in data:
                                print(data["response"], end="", flush=True)
                                full_response += data["response"]
                        except json.JSONDecodeError:
                            continue
                            #print("�", end='', flush=True)  # Handle invalid JSON

            # Process search tags and update history
            cleaned_response, did_search = self._clean_response(full_response)
            
            if did_search:
                searches_performed += 1
                # Add cleaned response to history
                self.conversation_history.append({
                    "role": "assistant",
                    "content": cleaned_response
                })
            else:
                # Final response
                self.conversation_history.append({
                    "role": "assistant",
                    "content": cleaned_response
                })
                return cleaned_response

        return cleaned_response

if __name__ == "__main__":
    erica = EricaAI()
    
    print("🌸 Welcome to Erica Chat! Type 'exit' to end the conversation.\n")
    
    while True:
        try:
            user_input = input("\n💬 You: ")
            if user_input.lower() in ['exit', 'quit']:
                print("\n🌸 Erica: Bye-bye! Let's chat again soon! (≧◡≦) ♡")
                break
                
            response = erica.chat(user_input)
            
        except KeyboardInterrupt:
            print("\n\n🌸 Erica: O-oh! Did I do something wrong? (๑•́ ₃ •̀๑)")
            break