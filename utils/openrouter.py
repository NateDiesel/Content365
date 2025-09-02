import os
import httpx

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
<<<<<<< HEAD
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
=======
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "mistral/mistral-7b-instruct")

headers = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "HTTP-Referer": "https://content365.xyz",
    "X-Title": "Content365 AI Pack Generator"
}

async def call_openrouter(prompt: str) -> str:
    if not OPENROUTER_API_KEY:
        raise ValueError("OpenRouter API key is missing")

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that formats content into blog + social captions + hashtags grouped by platform."},
            {"role": "user", "content": prompt}
        ]
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
>>>>>>> 2ed0c2a (chore: wire Gemini provider + provider_router)
