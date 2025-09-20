<<<<<<< HEAD
# utils/gemini.py
# -*- coding: utf-8 -*-
"""
Minimal Gemini REST helper for Content365.

Usage:
    from utils.gemini import call_gemini
    text = call_gemini(prompt_json_string, model="gemini-1.5-flash-002")

Env:
    GOOGLE_API_KEY=...
    GEMINI_MODEL=gemini-1.5-flash-002  (optional default)
    GEMINI_API_HOST=https://generativelanguage.googleapis.com  (optional)
"""

from __future__ import annotations
import os, json, re
from typing import Optional, List, Dict

# Optional deps
try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None
try:
    import requests
except Exception:  # pragma: no cover
    requests = None


GEMINI_API_KEY  = (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or "").strip()
GEMINI_MODEL    = os.getenv("GEMINI_MODEL", "gemini-1.5-flash-002").strip()
GEMINI_API_HOST = os.getenv("GEMINI_API_HOST", "https://generativelanguage.googleapis.com").strip()


class GeminiError(RuntimeError):
    pass


def _post(url: str, payload: dict, timeout: int = 60) -> dict:
    headers = {"Content-Type": "application/json"}
    if httpx is not None:
        r = httpx.post(url, headers=headers, json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json()
    if requests is not None:
        r = requests.post(url, headers=headers, json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json()
    raise GeminiError("Neither httpx nor requests is available")


def _extract_text(data: dict) -> str:
    """
    Gemini v1beta response -> first candidate text (joined parts if needed).
    """
    cands = data.get("candidates") or []
    if not cands:
        return ""
    content = cands[0].get("content") or {}
    parts = content.get("parts") or []
    if not parts and isinstance(content, dict):
        # Some variants put text directly (defensive)
        return content.get("text", "") or ""
    texts = []
    for p in parts:
        if isinstance(p, dict) and "text" in p:
            texts.append(p["text"])
    return "\n".join(texts).strip()


_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*([\s\S]*?)\s*```$", re.MULTILINE)


def strip_code_fences(text: str) -> str:
    """
    If the model wrapped JSON in ```json fences, return the inside.
    Otherwise return original.
    """
    m = _CODE_FENCE_RE.search(text or "")
    return m.group(1).strip() if m else (text or "")


def call_gemini(
    prompt: str,
    model: Optional[str] = None,
    *,
    temperature: float = 0.6,
    top_p: float = 0.9,
    max_tokens: int = 1200,
    system: Optional[str] = "Follow instructions exactly. Output ONLY valid JSON."
) -> str:
    """
    Call Gemini with a single string prompt.
    Returns the raw text Gemini produced (you can json.loads() it upstream if desired).

    Raises GeminiError on configuration or transport issues; returns "" if API responds but no text.
    """
    api_key = GEMINI_API_KEY
    mdl = (model or GEMINI_MODEL).strip()
    if not api_key:
        raise GeminiError("GOOGLE_API_KEY is not set")
    if not mdl:
        raise GeminiError("GEMINI_MODEL is not set")

    url = f"{GEMINI_API_HOST}/v1beta/models/{mdl}:generateContent?key={api_key}"

    # Prefer systemInstruction when present; otherwise prepend to user text.
    body: Dict = {
        "generationConfig": {
            "temperature": temperature,
            "topP": top_p,
            "maxOutputTokens": max_tokens,
        },
        "contents": [
            {"role": "user", "parts": [{"text": (f"{system}\n\n{prompt}" if not system else f"{system}\n\n{prompt}")}]}
        ],
    }
    if system:
        body["systemInstruction"] = {"role": "system", "parts": [{"text": system}]}

    try:
        data = _post(url, body, timeout=60)
    except Exception as e:
        raise GeminiError(f"Gemini request failed: {e}") from e

    text = _extract_text(data)
    return strip_code_fences(text)


def call_gemini_chat(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    *,
    temperature: float = 0.6,
    top_p: float = 0.9,
    max_tokens: int = 1200,
) -> str:
    """
    Chat-style helper.
    messages = [{"role":"system|user|assistant", "content":"..."}, ...]

    System messages are merged into systemInstruction.
    Assistant -> role 'model', User -> role 'user'.
    """
    api_key = GEMINI_API_KEY
    mdl = (model or GEMINI_MODEL).strip()
    if not api_key:
        raise GeminiError("GOOGLE_API_KEY is not set")
    if not mdl:
        raise GeminiError("GEMINI_MODEL is not set")

    url = f"{GEMINI_API_HOST}/v1beta/models/{mdl}:generateContent?key={api_key}"

    system_buf: List[str] = []
    contents: List[Dict] = []

    for m in messages:
        role = (m.get("role") or "").lower()
        text = m.get("content") or ""
        if role == "system":
            system_buf.append(text)
        elif role in ("assistant", "model"):
            contents.append({"role": "model", "parts": [{"text": text}]})
        else:
            contents.append({"role": "user", "parts": [{"text": text}]})

    body = {
        "generationConfig": {
            "temperature": temperature,
            "topP": top_p,
            "maxOutputTokens": max_tokens,
        },
        "contents": contents or [{"role": "user", "parts": [{"text": ""}]}],
    }
    if system_buf:
        body["systemInstruction"] = {"role": "system", "parts": [{"text": "\n\n".join(system_buf)}]}

    try:
        data = _post(url, body, timeout=60)
    except Exception as e:
        raise GeminiError(f"Gemini chat failed: {e}") from e

    text = _extract_text(data)
    return strip_code_fences(text)
=======
﻿# utils/gemini.py
# -*- coding: utf-8 -*-
import os, httpx

API_URL_TMPL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

def _friendly_http_error(status: int, body_preview: str) -> str:
    if status == 401:
        return ("Gemini 401: Unauthorized. Check GOOGLE_API_KEY or restrictions. "
                f"Server said: {body_preview}")
    if status == 403:
        return ("Gemini 403: Forbidden. Ensure the Generative Language API is enabled for this key "
                "and the key isn't domain- or IP-restricted. "
                f"Server said: {body_preview}")
    if status == 429:
        return ("Gemini 429: Rate limited / quota exceeded. Slow down or raise quota. "
                f"Server said: {body_preview}")
    return f"Gemini HTTP {status}: {body_preview}"

async def generate_text(prompt: str) -> str:
    key = os.getenv("GOOGLE_API_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash-latest")
    if not key:
        raise RuntimeError("GOOGLE_API_KEY missing")

    url = API_URL_TMPL.format(model=model, key=key)
    body = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ]
        # You can add safety settings here if needed
        # "safetySettings": [...]
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(url, json=body)
    if r.status_code != 200:
        preview = r.text[:400].replace("\n", " ")
        raise RuntimeError(_friendly_http_error(r.status_code, preview))

    data = r.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        if not text:
            raise RuntimeError("Gemini returned empty content")
        return text
    except Exception as e:
        raise RuntimeError(f"Gemini parse error: {e}; body={r.text[:400]}")
>>>>>>> 5a37524 (Initial commit of Content365 project)
