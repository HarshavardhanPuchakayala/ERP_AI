import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    raise SystemExit("OPENROUTER_API_KEY not found. Check your .env file.")

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)

try:
    response = client.chat.completions.create(
        model="openrouter/free",
        messages=[{"role": "user", "content": "In one sentence, what is an invoice?"}],
    )
    print("Model used:", response.model)
    print("Answer:", response.choices[0].message.content)
except Exception as e:
    print("Call failed:", type(e).__name__)
    print(e)