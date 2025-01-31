import google.generativeai as genai

genai.configure(api_key="AIzaSyD8Pq-pGies5M5M3wmQy55Jsufp_tPDTW4")
model = genai.GenerativeModel("gemini-1.5-flash")

def genetate_ai_message(prompt):
    responce = gemini_model.generate_content(prompt)
    return responce.text

prompt = "hello, how are you?"
ai_message = genetate_ai_message(prompt)
print(ai_message)