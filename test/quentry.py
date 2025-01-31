# import os
# import requests

# ACCOUNT_ID = "db5d0abbbab31174a76149945ff13959"
# AUTH_TOKEN = os.environ.get("Bearer RnU0Af-Df_KTu7i8d1h9k_-5vEz-4ZqYNIEX4RWp")

# prompt = "hi."
# response = requests.post(
#   f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/run/@cf/qwen/qwen1.5-14b-chat-awq",
#     headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
#     json={
#       "messages": [
#         {"role": "system", "content": "You are a friendly assistant"},
#         {"role": "user", "content": prompt}
#       ]
#     }
# )
# result = response.json()
# print(result)

import os
import requests

ACCOUNT_ID = "db5d0abbbab31174a76149945ff13959"
AUTH_TOKEN = os.environ.get("Bearer blAvZjZolf3Cq7Vs8sSVOiRV6Xz4WlucT-cSBpMD")

prompt = "Tell me all about PEP-8"
response = requests.post(
  f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/run/@hf/thebloke/neural-chat-7b-v3-1-awq",
    headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
    json={
      "messages": [
        {"role": "system", "content": "You are a friendly assistant"},
        {"role": "user", "content": prompt}
      ]
    }
)
result = response.json()
print(result)