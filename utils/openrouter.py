import os
import httpx

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = os.getenv("OPENROUTER_MODEL", "mistralai/mixtral-8x7b-instruct")

async def call_openrouter(prompt: str) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=data)
            response.raise_for_status()
            raw = response.json()
            return raw["choices"][0]["message"]["content"]
    except Exception as e:
        print("🔥 OpenRouter call failed:", e)
        print("⚠️ Full response (if available):", response.text if 'response' in locals() else "No response")
        raise
