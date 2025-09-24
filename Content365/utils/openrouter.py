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
        raise 2ed0c2a (chore: wire Gemini provider + provider_router)
=======
# utils/openrouter.py
# -*- coding: utf-8 -*-
import os, httpx

OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct")
OPENROUTER_BASE  = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
APP_URL          = os.getenv("APP_URL", "http://127.0.0.1:8001")

def _friendly_http_error(status: int, body_preview: str) -> str:
    if status == 402:
        return ("OpenRouter 402: Insufficient credits. "
                "Buy credits or switch to Gemini (set AI_PROVIDER=gemini and GOOGLE_API_KEY). "
                f"Server said: {body_preview}")
    if status == 401:
        return ("OpenRouter 401: Unauthorized. Check OPENROUTER_API_KEY and org access. "
                f"Server said: {body_preview}")
    if status == 429:
        return ("OpenRouter 429: Rate limited. Slow down requests or increase limits. "
                f"Server said: {body_preview}")
    return f"OpenRouter HTTP {status}: {body_preview}"

async def generate_text(prompt: str) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY missing")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": APP_URL,
        "X-Title": "Content365",
    }
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": "You are a senior marketing copywriter. Output ONLY valid JSON matching the requested schema. No markdown, no code fences."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
    }

    async with httpx.AsyncClient(timeout=90) as client:
        r = await client.post(f"{OPENROUTER_BASE}/chat/completions", headers=headers, json=payload)
        if r.status_code != 200:
            preview = r.text[:400].replace("\n", " ")
            raise RuntimeError(_friendly_http_error(r.status_code, preview))

        try:
            data = r.json()
            content = (data.get("choices") or [{}])[0].get("message", {}).get("content", "") or ""
        except Exception as e:
            raise RuntimeError(f"OpenRouter parse error: {e}; body={r.text[:400]}")

        content = content.strip()
        if not content:
            raise RuntimeError("OpenRouter returned empty content")
        return content
>>>>>>> 5a37524 (Initial commit of Content365 project)

