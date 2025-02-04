import os
import requests
from dotenv import load_dotenv

load_dotenv()
token = os.getenv('CLOWDFLARE_TOEKN')
api_url = os.getenv('CLOWDFLARE_API_URL')
headers = {"Authorization": f"Bearer {token}"}



def run(model, inputs):
        input = { "messages": inputs }
        response = requests.post(f"{api_url}{model}", headers=headers, json=input)
        return response.json()



class AiCommandChat:
    
    def process_text(self, text):
        inputs = [
            { "role": "system", "content": "you are a helpful ai assistant." },
            { "role": "user", "content": text },
        ];
        output = run("@hf/thebloke/neural-chat-7b-v3-1-awq", inputs)

        if 'result' in output and 'response' in output['result']:
#)> 0 and 'message' in output['result'][0] and 'content' in output['result'][0]['message']:
            response = output['result']['response']
        else:
            response =" Error: unable to retreve responce from the ai"
        #sending to the console the message and the resault in raw
        print(f"Receved slash command")
        print(f"command message is : {text}")
        print(f"command output is {output}")
        
        return response


