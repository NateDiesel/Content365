# utils/provider_router.py
import os
from typing import Any, Dict, Optional

# Optional deps
try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None
try:
    import requests
except Exception:  # pragma: no cover
    requests = None

# Reuse your existing OpenRouter util
from utils.openrouter import call_openrouter

"""
Provider Router
---------------
Purpose: Select the generator via env only—no code changes.

Supported Providers:
- "gemini":     Google AI Studio REST (no extra SDK needed)
- "openrouter": Uses utils.openrouter (model from env)
- "local":      LM Studio/Ollama (OpenAI-compatible)
- "nanobanana": OpenAI-compatible (disabled until launch)

Environment:
PREFERRED_PROVIDER=gemini | openrouter | local | nanobanana

# Gemini (recommended now)
GOOGLE_API_KEY=...
GEMINI_MODEL=gemini-1.5-flash-002  # or gemini-1.5-pro-002

# OpenRouter (optional backup)
OPENROUTER_API_KEY=...
OPENROUTER_MODEL=meta-llama/llama-3.1-70b-instruct  # example

# Local (optional)
LLM_API_URL=http://127.0.0.1:1234/v1/chat/completions
LLM_MODEL=mistral-7b-instruct-v0.2

# Nano Banana (not live yet)
NANOBANANA_ENABLED=false
NANOBANANA_BASE_URL=
NANOBANANA_API_KEY=
NANOBANANA_MODEL=
"""

PREFERRED_PROVIDER = os.getenv("PREFERRED_PROVIDER", "gemini").strip().lower()

# ---- OpenAI-compatible helper (shared by Nano Banana & Local) ----
def _openai_compatible_chat(url: str, api_key: Optional[str], model: str, prompt: str, timeout: int = 60) -> Optional[str]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Follow instructions exactly. Output ONLY valid JSON."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.6,
        "top_p": 0.9,
        "max_tokens": 1200,
        "stream": False,
        "stop": ["```"]
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        if httpx is not None:
            r = httpx.post(url, headers=headers, json=payload, timeout=timeout)
            r.raise_for_status()
            data = r.json()
        elif requests is not None:
            r = requests.post(url, headers=headers, json=payload, timeout=timeout)
            r.raise_for_status()
            data = r.json()
        else:
            return None

        return data.get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception:
        return None

# ---- Provider adapters ----

def _use_gemini(prompt: str) -> Optional[str]:
    """
    Minimal REST call to Google AI Studio (no SDK).
    """
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    model   = os.getenv("GEMINI_MODEL", "gemini-1.5-flash-002").strip()
    if not api_key or not model:
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    body = {
        "contents": [
            {
                "parts": [
                    {"text": "Follow instructions exactly. Output ONLY valid JSON.\n\n" + prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.6,
            "topP": 0.9,
            "maxOutputTokens": 1200
        }
    }
    headers = {"Content-Type": "application/json"}

    try:
        if httpx is not None:
            r = httpx.post(url, headers=headers, json=body, timeout=60)
            r.raise_for_status()
            data = r.json()
        elif requests is not None:
            r = requests.post(url, headers=headers, json=body, timeout=60)
            r.raise_for_status()
            data = r.json()
        else:
            return None

        return (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )
    except Exception:
        return None

def _use_openrouter(prompt: str) -> Optional[str]:
    try:
        return call_openrouter(prompt)
    except Exception:
        return None

def _use_local(prompt: str) -> Optional[str]:
    url = os.getenv("LLM_API_URL", "").strip()
    model = os.getenv("LLM_MODEL", "").strip()
    if not url or not model:
        return None
    return _openai_compatible_chat(url, None, model, prompt)

def _use_nanobanana(prompt: str) -> Optional[str]:
    if os.getenv("NANOBANANA_ENABLED", "false").strip().lower() != "true":
        return None
    base_url = os.getenv("NANOBANANA_BASE_URL", "").strip()
    api_key  = os.getenv("NANOBANANA_API_KEY", "").strip()
    model    = os.getenv("NANOBANANA_MODEL", "").strip()
    if not base_url or not model:
        return None
    return _openai_compatible_chat(base_url, api_key, model, prompt)

# ---- Public entrypoint ----

async def generate_pack_with_provider(prompt: str, context: Dict[str, Any]) -> Optional[str]:
    """
    Returns a JSON string (or None on failure).
    """
    provider = (context.get("provider") or PREFERRED_PROVIDER).strip().lower()

    # Try the chosen provider first
    first_attempt = {
        "gemini": _use_gemini,
        "openrouter": _use_openrouter,
        "local": _use_local,
        "nanobanana": _use_nanobanana,
    }.get(provider)

    if first_attempt:
        res = first_attempt(prompt)
        if res:
            return res

    # Fallback order (best available today)
    for fn in (_use_gemini, _use_openrouter, _use_local, _use_nanobanana):
        res = fn(prompt)
        if res:
            return res

    return None
