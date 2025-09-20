# -*- coding: utf-8 -*-
<<<<<<< HEAD
import json
<<<<<<< HEAD
from fastapi import FastAPI, Request, Form, Query
from typing import List
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
=======
import uuid
import os
import re
=======
import json, uuid, os, re
>>>>>>> 5a37524 (Initial commit of Content365 project)
from urllib.parse import quote
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, Request, Form, Query
<<<<<<< HEAD
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse
=======
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse, PlainTextResponse
>>>>>>> 5a37524 (Initial commit of Content365 project)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

<<<<<<< HEAD
>>>>>>> 2ed0c2a (chore: wire Gemini provider + provider_router)
from dotenv import load_dotenv
from utils.pdf_generator import generate_pdf
from utils.openrouter import call_openrouter
from utils.prompt_loader import load_prompt_template
<<<<<<< HEAD
from urllib.parse import quote
import stripe
import uuid
import os

load_dotenv()

app = FastAPI()
=======
from utils.prompt_builder import build_prompt  # optional, we fall back if missing
from utils.provider_router import generate_pack_with_provider  # optional, guarded
from utils.hashtag_rules import enforce_hashtag_rules
from utils.send_email import send_pdf_email  # email delivery
import stripe

# Optional deps: httpx preferred, fall back to requests if missing
try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None
try:
    import requests
except Exception:  # pragma: no cover
    requests = None

# --- ENV SETUP ---
load_dotenv()

# Safely initialize PDF engine/fonts (won't crash if helper missing)
try:
    import utils.pdf_generator as pdfgen
    if hasattr(pdfgen, "init_pdf_engine"):
        print("PDF init:", pdfgen.init_pdf_engine())
    else:
        print("PDF init: helper not found (skipping)")
except Exception as e:
    print("PDF init warning:", e)
>>>>>>> 2ed0c2a (chore: wire Gemini provider + provider_router)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
APP_URL = os.getenv("APP_URL", "http://localhost:8000")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")
<<<<<<< HEAD
ENABLE_PAYWALL = os.getenv("ENABLE_PAYWALL", "false").lower() == "true"

OUTPUT_FOLDER = "generated_pdfs"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

=======
ENABLE_PAYWALL = os.getenv("ENABLE_PAYWALL", "false").strip().lower() == "true"  # default OFF per your plan

# Local/hosted LLM settings (LM Studio / Ollama / OpenAI-compatible)
LLM_API_URL = os.getenv("LLM_API_URL", "").strip()
LLM_MODEL = os.getenv("LLM_MODEL", "").strip()

# Optional provider router flag (e.g., nano/flash/openrouter switching)
ENABLE_PROVIDER_ROUTER = os.getenv("ENABLE_PROVIDER_ROUTER", "false").strip().lower() == "true"

# --- APP INIT ---
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
=======
from dotenv import load_dotenv
import stripe

from utils.pdf_generator import generate_pdf
from utils.prompt_loader import load_prompt_template
from utils.prompt_builder import build_prompt
from utils.hashtag_rules import enforce_hashtag_rules
from utils.send_email import send_pdf_email

# optional deps
try:
    import httpx
except Exception:
    httpx = None
try:
    import requests
except Exception:
    requests = None

# --- AI casing normalization (keeps consistent 'AI' everywhere) ---
_AI_WORD_RX = re.compile(r"\bai\b", flags=re.IGNORECASE)

def _fix_ai_casing(s: Optional[str]) -> str:
    if not s:
        return ""
    # normalize NBSP and fix 'AI' as a standalone word
    s = s.replace("\u00A0", " ")
    return _AI_WORD_RX.sub("AI", s)

def _norm_platform(p: str) -> str:
    p = (p or "").strip().lower()
    if p == "twitter":
        return "x"
    return p

def _valid_platforms(seq):
    allowed = {"instagram","tiktok","linkedin","x","facebook"}
    out, seen = [], set()
    for s in seq or []:
        ss = _norm_platform(s)
        if ss in allowed and ss not in seen:
            seen.add(ss)
            out.append(ss)
    return out

# ---------------- ENV ----------------
load_dotenv(override=True)  # IMPORTANT
APP_VERSION     = "v4.3-release"

stripe.api_key   = os.getenv("STRIPE_SECRET_KEY")
APP_URL          = os.getenv("APP_URL", "http://127.0.0.1:8001")
STRIPE_PRICE_ID  = os.getenv("STRIPE_PRICE_ID")
ENABLE_PAYWALL   = os.getenv("ENABLE_PAYWALL", "false").strip().lower() == "true"

AI_PROVIDER      = (os.getenv("AI_PROVIDER", "openrouter") or "openrouter").strip().lower()
PROVIDER_ORDER   = [p.strip().lower() for p in os.getenv("PROVIDER_ORDER", AI_PROVIDER).split(",") if p.strip()]
DEBUG_AI         = True

LLM_API_URL      = os.getenv("LLM_API_URL", "").strip()
LLM_MODEL        = os.getenv("LLM_MODEL", "").strip()

# Presence flags for auto-rescue
HAS_OR_KEY       = bool(os.getenv("OPENROUTER_API_KEY"))
HAS_GEM_KEY      = bool(os.getenv("GOOGLE_API_KEY"))

# Strict JSON instruction used for *every* AI call
STRICT_JSON_PREFIX = (
    "IMPORTANT: Return ONLY valid JSON matching the requested schema. "
    "Do not include code fences, commentary, or markdown. "
)

# ---- Brand for PDF header/footer ----
BRAND_NAME    = os.getenv("BRAND_NAME", "Content365")
# Prefer an explicit website/domain for the PDF header (not the app host)
BRAND_WEBSITE = (os.getenv("BRAND_WEBSITE") or os.getenv("APP_DOMAIN") or "content365.xyz").strip()
LOGO_PATH     = os.getenv("LOGO_PATH", "static/logo.png")

# ---------------- APP ----------------
app = FastAPI(title="Content365", version=APP_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in (os.getenv("CORS_ALLOW_ORIGINS") or "*").split(",") if o.strip()],
>>>>>>> 5a37524 (Initial commit of Content365 project)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

<<<<<<< HEAD
OUTPUT_FOLDER = "generated_pdfs"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# ---------- Helpers: LLM + JSON safety ----------

def _strip_code_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        if "\n" in t:
            first_line, rest = t.split("\n", 1)
            if first_line.lower().strip() in ("json", "javascript"):
                t = rest
    return t.strip()

def _extract_json_blob(text: str) -> str:
    # Best-effort: grab from first '{' to last '}'.
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end+1]
    return text  # fallback: return original

def _coerce_hashtags(parsed: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Ensure top-level 'hashtags' exists.
    If missing, derive from captions/captions_by_platform if available.
    Accepts either:
      captions = { "Instagram": {...} } OR captions_by_platform = {...}
    """
    if "hashtags" in parsed and isinstance(parsed["hashtags"], dict):
        return parsed["hashtags"]

=======
OUTPUT_FOLDER = os.getenv("OUTPUT_DIR", "generated_pdfs")
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

templates = Jinja2Templates(directory="templates")
templates.env.globals["now"] = lambda: datetime.now()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

# ---------- helpers ----------
def _strip_code_fences(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("```"):
        t = t[3:]
        if "\n" in t:
            _first, rest = t.split("\n", 1)
            t = rest
        if t.endswith("```"):
            t = t[:-3]
    return t.strip()

def _extract_json_blob(text: str) -> str:
    start = text.find("{"); end = text.rfind("}")
    return text[start:end+1] if (start != -1 and end != -1 and end > start) else text

def _coerce_hashtags(parsed: Dict[str, Any]) -> Dict[str, List[str]]:
    if "hashtags" in parsed and isinstance(parsed["hashtags"], dict):
        return parsed["hashtags"]
>>>>>>> 5a37524 (Initial commit of Content365 project)
    hashtags: Dict[str, List[str]] = {}
    caps = parsed.get("captions") or parsed.get("captions_by_platform") or {}
    if isinstance(caps, dict):
        for platform, block in caps.items():
<<<<<<< HEAD
            # Each platform can be a dict (caption/hashtags), a str, or a list
            if isinstance(block, dict):
                hs = block.get("hashtags", [])
                if isinstance(hs, str):
                    if "," in hs:
                        hs_list = [h.strip().lstrip("#") for h in hs.split(",") if h.strip()]
                    else:
                        hs_list = [h.strip().lstrip("#") for h in hs.split() if h.strip()]
                elif isinstance(hs, list):
                    hs_list = [str(h).strip().lstrip("#") for h in hs if str(h).strip()]
                else:
                    hs_list = []
                if hs_list:
                    hashtags[platform] = hs_list
            # string/list blocks have no explicit hashtags; skip
=======
            hs_list: List[str] = []
            if isinstance(block, dict):
                hs = block.get("hashtags", [])
                if isinstance(hs, str):
                    parts = [h.strip().lstrip("#") for h in re.split(r"[\s,]+", hs) if h.strip()]
                    hs_list = parts
                elif isinstance(hs, list):
                    hs_list = [str(h).strip().lstrip("#") for h in hs if str(h).strip()]
            if hs_list:
                hashtags[platform] = hs_list
>>>>>>> 5a37524 (Initial commit of Content365 project)
    return hashtags

def _normalize_ai_result(ai_result: Any) -> Optional[Dict[str, Any]]:
    """
<<<<<<< HEAD
    Accept raw string (possibly fenced) from LLM, parse JSON, and
    produce a normalized dict with:
      { "blog": {...}, "captions": {...}, "hashtags": {...optional...} }
    - Supports 'captions' OR 'captions_by_platform'
    - Tolerates blog as str or dict; maps 'cta' -> 'CTA'
=======
    Parse/normalize the AI JSON into a consistent dict:
    { blog: {...}, captions: {plat: str|{text:...}}, hashtags: {plat: [tags]} }
    NOTE: do NOT call enforce_hashtag_rules here; we enforce per-platform later.
>>>>>>> 5a37524 (Initial commit of Content365 project)
    """
    if ai_result is None:
        return None

    if isinstance(ai_result, dict):
        parsed = ai_result
    elif isinstance(ai_result, str):
        txt = _strip_code_fences(ai_result)
        txt = _extract_json_blob(txt)
<<<<<<< HEAD
        parsed = json.loads(txt)
    else:
        # Anything else -> stringify into blog intro
        return {
            "blog": {"title": "Generated Content", "intro": str(ai_result), "bullets": [], "CTA": ""},
            "captions": {}
        }

    # ---- Blog ----
    raw_blog = parsed.get("blog", parsed.get("article", {}))
    if isinstance(raw_blog, str):
        blog = {"title": "Generated Content", "intro": raw_blog, "bullets": [], "CTA": ""}
    elif isinstance(raw_blog, dict):
        blog = {
            "title": raw_blog.get("title") or "Generated Content",
            "intro": raw_blog.get("intro", ""),
            "bullets": raw_blog.get("bullets", []) or [],
            "CTA": raw_blog.get("CTA", raw_blog.get("cta", "")) or ""
        }
    else:
        blog = {"title": "Generated Content", "intro": "", "bullets": [], "CTA": ""}

    # ---- Captions ----
=======
        try:
            parsed = json.loads(txt)
        except Exception:
            return {
                "blog": {"headline": "Generated Content", "intro": txt, "body": [], "bullets": [], "cta": ""},
                "captions": {}, "hashtags": {}
            }
    else:
        return {
            "blog": {"headline": "Generated Content", "intro": str(ai_result), "body": [], "bullets": [], "cta": ""},
            "captions": {}, "hashtags": {}
        }

    raw_blog = parsed.get("blog") or parsed.get("article") or {}
    if isinstance(raw_blog, str):
        blog = {"headline": "Generated Content", "intro": raw_blog, "body": [], "bullets": [], "cta": ""}
    elif isinstance(raw_blog, dict):
        blog = {
            "headline": raw_blog.get("headline") or raw_blog.get("title") or "Generated Content",
            "intro": raw_blog.get("intro") or raw_blog.get("introduction") or "",
            "body": raw_blog.get("body") or [],
            "bullets": raw_blog.get("bullets") or raw_blog.get("points") or [],
            "cta": raw_blog.get("cta") or raw_blog.get("CTA") or "",
        }
    else:
        blog = {"headline": "Generated Content", "intro": "", "body": [], "bullets": [], "cta": ""}

    if isinstance(blog.get("body"), str):
        blog["body"] = [blog["body"]]
    if not isinstance(blog.get("body"), list):
        blog["body"] = []

>>>>>>> 5a37524 (Initial commit of Content365 project)
    caps = parsed.get("captions_by_platform") or parsed.get("captions") or {}
    if not isinstance(caps, dict):
        caps = {}

<<<<<<< HEAD
    # ---- Hashtags (optional) ----
=======
>>>>>>> 5a37524 (Initial commit of Content365 project)
    hashtags_block = parsed.get("hashtags")
    if not isinstance(hashtags_block, dict):
        hashtags_block = _coerce_hashtags({"captions": caps})

<<<<<<< HEAD
    norm = {"blog": blog, "captions": caps}
    if hashtags_block:
        # keep your existing platform-specific rules
        norm["hashtags"] = enforce_hashtag_rules(hashtags_block)
    return norm

async def call_local_llm(prompt: str) -> Optional[str]:
    """
    Calls a local/hosted OpenAI-compatible LLM (LM Studio/Ollama) if LLM_API_URL+LLM_MODEL set.
    Returns the raw string content from choices[0].message.content, or None on error.
    """
    if not LLM_API_URL or not LLM_MODEL:
        return None

=======
    # return raw; clamp later per platform
    return {"blog": blog, "captions": caps, "hashtags": hashtags_block}

def _to_pdf_schema(parsed: Dict[str, Any]) -> Dict[str, Any]:
    blog_in = parsed.get("blog") or {}
    blog_out = {
        "headline": blog_in.get("headline") or blog_in.get("title") or "Your Content Pack",
        "intro": blog_in.get("intro") or blog_in.get("introduction") or "",
        "body": blog_in.get("body") or [],
        "bullets": blog_in.get("bullets") or blog_in.get("points") or [],
        "cta": blog_in.get("cta") or blog_in.get("CTA") or "",
    }
    if isinstance(blog_out["body"], str):
        blog_out["body"] = [blog_out["body"]]

    captions = parsed.get("captions") or parsed.get("captions_by_platform") or {}
    hashtags = parsed.get("hashtags") or {}
    tags_clean: Dict[str, List[str]] = {}
    if isinstance(hashtags, dict):
        for k, v in hashtags.items():
            if isinstance(v, str):
                parts = [p.strip().lstrip("#") for p in re.split(r"[\s,]+", v) if p.strip()]
                tags_clean[k] = parts
            elif isinstance(v, list):
                tags_clean[k] = [str(x).lstrip("#").strip() for x in v if str(x).strip()]

    return {"blog": blog_out, "captions": captions, "hashtags": tags_clean}

def _safe_build_prompt(topic: str, tone: str, audience_type: str, post_style: str, word_count: str, platforms_str: str) -> str:
    try:
        return build_prompt(
            topic=topic, tone=tone, audience_type=audience_type,
            post_style=post_style, word_count=word_count, platforms=platforms_str
        )
    except Exception:
        tmpl = load_prompt_template()
        return tmpl.format(
            topic=topic, tone=tone, audience_type=audience_type,
            post_style=post_style, word_count=word_count, platforms=platforms_str
        )

def _append_context_to_prompt(prompt: str, audience: str, notes: str) -> str:
    extra_lines = []
    if audience:
        extra_lines.append(f"\nAudience Details: {audience}")
    if notes:
        extra_lines.append(f"\nCreator Notes: {notes}")
    if not extra_lines:
        return prompt
    return f"{prompt.rstrip()}{''.join(extra_lines)}"

def _parse_platforms_param(raw_platforms: List[str]) -> List[str]:
    if not raw_platforms: return []
    if len(raw_platforms) == 1 and ("," in raw_platforms[0] or " " in raw_platforms[0]):
        return [p.strip() for p in re.split(r"[,\s]+", raw_platforms[0]) if p.strip()]
    return raw_platforms

def _normalize_platform_labels(platforms: List[str]) -> List[str]:
    """Normalize common aliases (e.g., X -> Twitter) for user-facing labels (form/debug)."""
    out = []
    for p in platforms or []:
        pl = (p or "").strip()
        if pl.lower() in {"x", "twitter"}:
            pl = "Twitter"
        out.append(pl)
    return out

# ---------- providers ----------
async def _call_local_llm(prompt: str) -> Optional[str]:
    if not LLM_API_URL or not LLM_MODEL:
        return None
>>>>>>> 5a37524 (Initial commit of Content365 project)
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": "Follow instructions exactly. Output ONLY valid JSON."},
            {"role": "user", "content": prompt}
        ],
<<<<<<< HEAD
        "temperature": 0.6,
        "top_p": 0.9,
        "max_tokens": 1200,
        "stream": False,
        "stop": ["```"]
    }

    headers = {"Content-Type": "application/json"}

    try:
        if httpx is not None:
=======
        "temperature": 0.6, "top_p": 0.9, "max_tokens": 1200, "stream": False, "stop": ["```"]
    }
    headers = {"Content-Type": "application/json"}
    try:
        if httpx:
>>>>>>> 5a37524 (Initial commit of Content365 project)
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(LLM_API_URL, headers=headers, json=payload)
                r.raise_for_status()
                data = r.json()
<<<<<<< HEAD
        elif requests is not None:
=======
        elif requests:
>>>>>>> 5a37524 (Initial commit of Content365 project)
            r = requests.post(LLM_API_URL, headers=headers, json=payload, timeout=60)
            r.raise_for_status()
            data = r.json()
        else:
            return None
<<<<<<< HEAD

        # OpenAI-compatible response
        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        if not isinstance(content, str):
            return None
        return content
    except Exception:
        return None

async def call_llm_with_fallback(prompt: str, context: Dict[str, Any]) -> Optional[str]:
    """
    Order of operations:
      1) If provider router enabled, try it first (lets you target 'nano banana' / 'flash 2.5', etc.)
      2) Try local LLM (LM Studio)
      3) Fall back to OpenRouter util
    """
    # 1) Provider router (optional)
    if ENABLE_PROVIDER_ROUTER:
        try:
            routed = await generate_pack_with_provider(prompt=prompt, context=context)  # should return JSON string or dict
            if routed:
                return routed if isinstance(routed, str) else json.dumps(routed)
        except Exception:
            pass

    # 2) Local LLM
    local = await call_local_llm(prompt)
    if local:
        return local

    # 3) OpenRouter fallback
    try:
        return await call_openrouter(prompt)
    except Exception:
        return None

# ---------- Small helpers ----------

def _safe_build_prompt(topic: str, tone: str, audience_type: str, post_style: str, word_count: str, platforms_str: str) -> str:
    """
    Prefer utils.prompt_builder.build_prompt if present; otherwise load template file.
    """
    try:
        # Use the structured builder if available
        return build_prompt(
            topic=topic,
            tone=tone,
            audience_type=audience_type,
            post_style=post_style,
            word_count=word_count,
            platforms=platforms_str
        )
    except Exception:
        # Fallback to file-based template
        tmpl = load_prompt_template()
        return tmpl.format(
            topic=topic,
            tone=tone,
            audience_type=audience_type,
            post_style=post_style,
            word_count=word_count,
            platforms=platforms_str
        )

def _parse_platforms_param(raw_platforms: List[str]) -> List[str]:
    """
    On /success, 'platforms' often comes through as a single comma-separated item.
    Normalize to a clean list.
    """
    if not raw_platforms:
        return []
    if len(raw_platforms) == 1 and ("," in raw_platforms[0] or " " in raw_platforms[0]):
        # split by comma and/or whitespace
        parts = [p.strip() for p in re.split(r"[,]+", raw_platforms[0]) if p.strip()]
        return parts
    return raw_platforms

# ---------- ROUTES ----------
>>>>>>> 2ed0c2a (chore: wire Gemini provider + provider_router)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

<<<<<<< HEAD

=======
>>>>>>> 2ed0c2a (chore: wire Gemini provider + provider_router)
@app.get("/form", response_class=HTMLResponse)
async def form_get(request: Request):
    return templates.TemplateResponse("form.html", {"request": request})

<<<<<<< HEAD

=======
>>>>>>> 2ed0c2a (chore: wire Gemini provider + provider_router)
=======
        return (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
    except Exception as e:
        if DEBUG_AI: print(f"[AI] Local LLM error: {e}")
        return None

async def _call_ai(prompt: str) -> Optional[str]:
    """
    Try providers in order and auto-rescue between OpenRouter/Gemini/Local.
    """
    if not prompt.startswith(STRICT_JSON_PREFIX):
        prompt = f"{STRICT_JSON_PREFIX}{prompt}"

    order = PROVIDER_ORDER[:] if PROVIDER_ORDER else [AI_PROVIDER]
    order = [("gemini" if p in ("gemini", "google") else "openrouter" if p in ("openrouter", "or") else "local") for p in order]

    def _append_if(order_list, provider):
        if provider not in order_list:
            order_list.append(provider)

    if HAS_OR_KEY and "openrouter" not in order:
        _append_if(order, "openrouter")
    if HAS_GEM_KEY and "gemini" not in order:
        _append_if(order, "gemini")
    if LLM_API_URL and "local" not in order:
        _append_if(order, "local")

    last_err = None
    for provider in order:
        try:
            if provider == "local":
                local = await _call_local_llm(prompt)
                if local:
                    if DEBUG_AI: print("[AI] Using local LLM")
                    return local

            elif provider == "openrouter":
                if not HAS_OR_KEY:
                    if DEBUG_AI: print("[AI] Skipping OpenRouter: OPENROUTER_API_KEY missing")
                    continue
                from utils.openrouter import generate_text as call_openrouter  # async
                if DEBUG_AI: print("[AI] Calling OpenRouter")
                return await call_openrouter(prompt)

            elif provider == "gemini":
                if not HAS_GEM_KEY:
                    if DEBUG_AI: print("[AI] Skipping Gemini: GOOGLE_API_KEY missing")
                    continue
                try:
                    from utils.gemini import generate_text as call_gemini  # async
                except Exception as e:
                    if DEBUG_AI: print(f"[AI] Gemini import failed: {e}")
                    continue
                if DEBUG_AI: print("[AI] Calling Gemini")
                return await call_gemini(prompt)

        except Exception as e:
            last_err = e
            msg = str(e)
            if DEBUG_AI: print(f"[AI] Provider '{provider}' failed: {msg}")
            if provider == "openrouter" and "402" in msg and HAS_GEM_KEY:
                try:
                    from utils.gemini import generate_text as call_gemini  # async
                    if DEBUG_AI: print("[AI] Auto-rescue → Gemini due to OpenRouter 402")
                    return await call_gemini(prompt)
                except Exception as e2:
                    if DEBUG_AI: print(f"[AI] Rescue to Gemini failed: {e2}")
            continue

    if DEBUG_AI and last_err:
        print(f"[AI] All providers failed. Last error: {last_err}")
    return None

# ---------------- routes ----------------
app_version_banner = {"version": APP_VERSION, "cwd": os.getcwd()}

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "version": APP_VERSION, "year": datetime.now().year},
    )

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return PlainTextResponse("", media_type="image/x-icon")

@app.get("/form", response_class=HTMLResponse)
async def form_get(request: Request):
    return templates.TemplateResponse("form.html", {"request": request, "version": APP_VERSION})

@app.get("/debug/env")
async def debug_env():
    return {
        "version": APP_VERSION,
        "cwd": os.getcwd(),
        "AI_PROVIDER": os.getenv("AI_PROVIDER"),
        "PROVIDER_ORDER": os.getenv("PROVIDER_ORDER"),
        "OPENROUTER_MODEL": os.getenv("OPENROUTER_MODEL"),
        "OPENROUTER_API_KEY": "set" if os.getenv("OPENROUTER_API_KEY") else "MISSING",
        "GEMINI_MODEL": os.getenv("GEMINI_MODEL"),
        "GOOGLE_API_KEY": "set" if os.getenv("GOOGLE_API_KEY") else "MISSING",
        "LLM_API_URL": LLM_API_URL or "MISSING",
        "LLM_MODEL": LLM_MODEL or "MISSING",
        # brand surfacing
        "BRAND_NAME": BRAND_NAME,
        "BRAND_WEBSITE": BRAND_WEBSITE,
        "LOGO_PATH": LOGO_PATH,
    }

@app.get("/debug/ai/test", response_class=PlainTextResponse)
async def debug_ai_test():
    """Force a tiny JSON-only AI call to verify provider connectivity."""
    prompt = '{"blog":{"headline":"Test","intro":"Hello","body":["Line"],"bullets":["One"],"cta":"Go"},"captions":{},"hashtags":{}}'
    res = await _call_ai(f"Return EXACTLY this JSON with no extra characters: {prompt}")
    return res or "None"

@app.post("/debug/ai/prompt", response_class=PlainTextResponse)
async def debug_ai_prompt(
    topic: str = Form(...),
    audience: str = Form(""),
    tone: str = Form(""),
    platforms: List[str] = Form([]),
    word_count: str = Form("medium"),
    audience_type: str = Form("B2C"),
    post_style: str = Form("General"),
    notes: str = Form("")
):
    """Preview the exact prompt string sent to the AI (no call made)."""
    platforms_str = ", ".join(_normalize_platform_labels(platforms or []))
    clean_post_style = "" if (post_style or "").lower() == "general" else post_style
    try:
        prompt = _safe_build_prompt(
            topic=topic, tone=tone, audience_type=audience_type,
            post_style=clean_post_style, word_count=word_count, platforms_str=platforms_str
        )
        prompt = _append_context_to_prompt(prompt, audience=audience, notes=notes)
    except Exception as e:
        prompt = f"[PROMPT ERROR] {e}"
    return prompt

@app.get("/healthz", response_class=PlainTextResponse)
async def healthz():
    return "ok"

@app.get("/status")
async def status():
    return JSONResponse({
        "ok": True,
        "app_url": APP_URL,
        "output_folder": OUTPUT_FOLDER,
        "time": datetime.utcnow().isoformat()+"Z",
        **app_version_banner
    })

@app.get("/sample")
async def sample():
    fc = fallback_content(
        "Sample Topic", "audience",
        ["Instagram","LinkedIn","TikTok","Twitter","Facebook"],
        "#sample", "medium", "Neutral", "B2C", "General"
    )
    filename = f"sample-{uuid.uuid4().hex[:8]}.pdf"
    filepath = os.path.join(OUTPUT_FOLDER, filename)
    brand = {
        "brand_name": "Content365",   # brand text (still shown alongside the logo)
        "website": "content365.xyz",
        "logo_path": "assets/logo.png",  # <— now uses your real logo
        "primary_color": (0.12, 0.46, 0.95),
        "footer_text": "Generated by Content365.xyz — Create your own AI marketing packs in minutes.",
    }

    pdf_payload = _to_pdf_schema(fc)
    generate_pdf(pdf_payload, output_path=filepath, brand_config=brand)
    return FileResponse(filepath, media_type="application/pdf", filename=filename)

# ----- core form handlers -----
>>>>>>> 5a37524 (Initial commit of Content365 project)
@app.post("/form")
async def form_post(
    request: Request,
    topic: str = Form(...),
    audience: str = Form(""),
    tone: str = Form(""),
    hashtags: str = Form(""),
    notes: str = Form(""),
    platforms: List[str] = Form([]),
    word_count: str = Form("medium"),
<<<<<<< HEAD
<<<<<<< HEAD
    email: str = Form("")
):
    platforms_str = ', '.join(platforms)
    platforms_encoded = quote(platforms_str)

    prompt_template = load_prompt_template()
    prompt = prompt_template.format(
        topic=topic,
        audience=audience,
        tone=tone,
        platforms=platforms_str,
        word_count=word_count
    )
    prompt += (
        f"\nfor an audience of '{audience}' in a '{tone}' tone.\n"
        f"Generate social media captions tailored for the following platforms: {platforms_str}.\n"
        "Each caption should:\n"
        "- Match the tone and audience type\n"
        "- Include emojis and a compelling call to action\n"
        "- End with 5–7 smart, topic-relevant hashtags per platform\n"
        "Return results grouped by platform in markdown format."
    )

    try:
        ai_result = await call_openrouter(prompt)
        ai_success = True
    except Exception:
        ai_result = (
            "⚠️ Our AI service is currently unavailable.\n\n"
            "**Mini Blog:**\n"
            "AI in 2025 will reshape industries from healthcare to education. Here are 3 key predictions:\n"
            "- ✨ Democratization of AI tools\n"
            "- 🧠 Rise of personal AI assistants\n"
            "- 📊 AI-driven decisions in daily life\n\n"
            "**Social Captions:**\n"
            "1. \"2025: The year AI gets personal. Are you ready? 🤖🚀\"\n"
            "2. \"The AI wave is here — freelancers, grab your board 🏄‍♂️📈\"\n"
            "3. \"Let's talk AI trends. Spoiler: It's moving fast. 🔥\"\n\n"
            "_You weren't charged for this fallback pack._"
        )
        ai_success = False

    if ENABLE_PAYWALL and ai_success:
=======
    email: str = Form(""),
    audience_type: str = Form("B2C"),
    post_style: str = Form("General")
):
    platforms_clean = platforms or []
=======
    email: str = Form(""),
    audience_type: str = Form("B2C"),
    post_style: str = Form("General"),
):
    # keep user-facing labels for prompt; normalize to slugs later
    platforms_clean = _normalize_platform_labels(platforms or [])
>>>>>>> 5a37524 (Initial commit of Content365 project)
    platforms_str = ", ".join(platforms_clean)
    platforms_encoded = quote(platforms_str)
    clean_post_style = "" if (post_style or "").lower() == "general" else post_style

<<<<<<< HEAD
    # Build the prompt using builder (or template fallback)
    try:
        prompt = _safe_build_prompt(
            topic=topic,
            tone=tone,
            audience_type=audience_type,
            post_style=clean_post_style,
            word_count=word_count,
            platforms_str=platforms_str
        )
    except Exception as e:
        prompt = f"⚠️ Failed to format prompt: {e}"
        ai_result = None
        ai_success = False
    else:
        try:
            ai_raw = await call_llm_with_fallback(prompt, context={
                "topic": topic,
                "tone": tone,
                "audience_type": audience_type,
                "post_style": clean_post_style,
                "word_count": word_count,
                "platforms": platforms_clean,
                "email": email
            })
            ai_result = ai_raw
            ai_success = ai_raw is not None
        except Exception:
            ai_result = None
            ai_success = False

    # Stripe paywall (safe-guard if price id missing)
    if ENABLE_PAYWALL and ai_success and STRIPE_PRICE_ID:
>>>>>>> 2ed0c2a (chore: wire Gemini provider + provider_router)
=======
    # Build + call AI
    try:
        prompt = _safe_build_prompt(
            topic=topic, tone=tone, audience_type=audience_type,
            post_style=clean_post_style, word_count=word_count, platforms_str=platforms_str
        )
        prompt = _append_context_to_prompt(prompt, audience=audience, notes=notes)
    except Exception as e:
        if DEBUG_AI: print(f"[AI] Prompt format error: {e}")
        prompt = f'{{"error":"Failed to format prompt: {e}"}}'

    ai_raw = await _call_ai(prompt)
    ai_success = ai_raw is not None

    # Paywall (optional)
    if ENABLE_PAYWALL and ai_success and STRIPE_PRICE_ID:
>>>>>>> 5a37524 (Initial commit of Content365 project)
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
            mode="payment",
<<<<<<< HEAD
<<<<<<< HEAD
            success_url=f"{APP_URL}/success?topic={quote(topic)}&audience={quote(audience)}"
                        f"&tone={quote(tone)}&hashtags={quote(hashtags)}&notes={quote(notes)}"
                        f"&platforms={platforms_encoded}&word_count={word_count}&email={quote(email)}",
=======
            success_url=(
                f"{APP_URL}/success?"
                f"topic={quote(topic)}&audience={quote(audience)}"
                f"&tone={quote(tone)}&hashtags={quote(hashtags)}&notes={quote(notes)}"
                f"&platforms={platforms_encoded}&word_count={word_count}&email={quote(email)}"
                f"&audience_type={quote(audience_type)}&post_style={quote(post_style)}"
            ),
>>>>>>> 2ed0c2a (chore: wire Gemini provider + provider_router)
            cancel_url=f"{APP_URL}/form"
        )
        return RedirectResponse(session.url, status_code=303)

<<<<<<< HEAD
    return await generate_pdf_response(topic, audience, tone, hashtags, notes, ai_result, email)

=======
    return await generate_pdf_response(topic, audience, tone, hashtags, notes, ai_result, email, audience_type, post_style)
>>>>>>> 2ed0c2a (chore: wire Gemini provider + provider_router)
=======
            success_url=(
                f"{APP_URL}/success?topic={quote(topic)}&audience={quote(audience)}&tone={quote(tone)}"
                f"&hashtags={quote(hashtags)}&notes={quote(notes)}&platforms={platforms_encoded}"
                f"&word_count={word_count}&email={quote(email)}&audience_type={quote(audience_type)}"
                f"&post_style={quote(post_style)}"
            ),
            cancel_url=f"{APP_URL}/form",
        )
        return RedirectResponse(session.url, status_code=303)

    return await generate_pdf_response(
        topic, audience, tone, hashtags, notes,
        ai_raw, email, audience_type, post_style,
        platforms_clean, word_count
    )
>>>>>>> 5a37524 (Initial commit of Content365 project)

@app.get("/success")
async def success(
    topic: str,
    audience: str = "",
    tone: str = "",
    hashtags: str = "",
    notes: str = "",
    platforms: List[str] = Query([]),
    word_count: str = Query("medium"),
<<<<<<< HEAD
<<<<<<< HEAD
    email: str = ""
):
    platforms_str = ', '.join(platforms)

    prompt_template = load_prompt_template()
    prompt = prompt_template.format(
        topic=topic,
        audience=audience,
        tone=tone,
        platforms=platforms_str,
        word_count=word_count
    )
    prompt += (
        f"\nfor an audience of '{audience}' in a '{tone}' tone.\n"
        f"Generate social media captions tailored for the following platforms: {platforms_str}.\n"
        "Each caption should:\n"
        "- Match the tone and audience type\n"
        "- Include emojis and a compelling call to action\n"
        "- End with 5–7 smart, topic-relevant hashtags per platform\n"
        "Return results grouped by platform in markdown format."
    )

    try:
        ai_result = await call_openrouter(prompt)
    except Exception:
        ai_result = (
            "⚠️ Our AI service is currently unavailable.\n\n"
            "**Mini Blog:**\n"
            "AI in 2025 will reshape industries from healthcare to education. Here are 3 key predictions:\n"
            "- ✨ Democratization of AI tools\n"
            "- 🧠 Rise of personal AI assistants\n"
            "- 📊 AI-driven decisions in daily life\n\n"
            "**Social Captions:**\n"
            "1. \"2025: The year AI gets personal. Are you ready? 🤖🚀\"\n"
            "2. \"The AI wave is here — freelancers, grab your board 🏄‍♂️📈\"\n"
            "3. \"Let's talk AI trends. Spoiler: It's moving fast. 🔥\"\n\n"
            "_You weren't charged for this fallback pack._"
        )

    return await generate_pdf_response(topic, audience, tone, hashtags, notes, ai_result, email)


async def generate_pdf_response(topic, audience, tone, hashtags, notes, ai_result, email):
    try:
        social_captions = json.loads(ai_result)
    except Exception:
        # fallback: put AI result inside a general key
        social_captions = {"General": [ai_result]}

    content_dict = {
        "lead_magnet": f"Top tips for {audience or 'your niche'} success in 2025",
        "seo_keywords": f"{topic.lower()}, {audience.lower()} marketing, AI content tools",
        "social_captions": social_captions,
        "hashtags": hashtags,
        "tips": notes
    }

    filename = f"{uuid.uuid4().hex[:12]}.pdf"
    filepath = os.path.join(OUTPUT_FOLDER, filename)
    generate_pdf(content_dict=content_dict)

    return FileResponse(filepath, media_type="application/pdf", filename=filename)

=======
=======
>>>>>>> 5a37524 (Initial commit of Content365 project)
    email: str = "",
    audience_type: str = Query("B2C"),
    post_style: str = Query("General")
):
<<<<<<< HEAD
    platforms_clean = _parse_platforms_param(platforms)
=======
    platforms_clean = _normalize_platform_labels(_parse_platforms_param(platforms))
>>>>>>> 5a37524 (Initial commit of Content365 project)
    platforms_str = ", ".join(platforms_clean)
    clean_post_style = "" if (post_style or "").lower() == "general" else post_style

    try:
        prompt = _safe_build_prompt(
<<<<<<< HEAD
            topic=topic,
            tone=tone,
            audience_type=audience_type,
            post_style=clean_post_style,
            word_count=word_count,
            platforms_str=platforms_str
        )
        ai_result = await call_llm_with_fallback(prompt, context={
            "topic": topic,
            "tone": tone,
            "audience_type": audience_type,
            "post_style": clean_post_style,
            "word_count": word_count,
            "platforms": platforms_clean,
            "email": email
        })
    except Exception:
        ai_result = None

    return await generate_pdf_response(topic, audience, tone, hashtags, notes, ai_result, email, audience_type, post_style)

# --- PDF HANDLER ---

def _to_pdf_schema(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert normalized payload with 'blog', 'captions', 'hashtags' into
    the PDF generator schema:
      { "blog": {"title","intro","bullets","cta"}, "platforms": {P: {"caption","hashtags":[]}} }
    """
    blog = parsed.get("blog") or {}
    # normalize keys
    b = {
        "title": blog.get("title") or "Your Content Pack",
        "intro": blog.get("intro") or blog.get("introduction") or "",
        "bullets": blog.get("bullets") or blog.get("points") or [],
        "cta": blog.get("cta") or blog.get("CTA") or "",
    }

    caps = parsed.get("captions") or parsed.get("captions_by_platform") or {}
    tags = parsed.get("hashtags") or {}

    platforms = {}
    if isinstance(caps, dict):
        for k, v in caps.items():
            caption = v if isinstance(v, str) else (v.get("text") if isinstance(v, dict) else "")
            hts = tags.get(k, [])
            # Coerce hashtags to list of strings
            if isinstance(hts, str):
                parts = [p.strip() for p in re.split(r"[\\s,]+", hts) if p.strip()]
                hts = [("#" + p.lstrip("#")) for p in parts]
            elif isinstance(hts, list):
                hts = [("#" + str(x).lstrip("#").strip()) for x in hts if str(x).strip()]
            else:
                hts = []
            platforms[str(k)] = {"caption": caption, "hashtags": hts}
    return {"blog": b, "platforms": platforms}

async def generate_pdf_response(topic, audience, tone, hashtags, notes, ai_result, email, audience_type, post_style):
    clean_post_style = "" if (post_style or "").lower() == "general" else post_style

=======
            topic=topic, tone=tone, audience_type=audience_type,
            post_style=clean_post_style, word_count=word_count, platforms_str=platforms_str
        )
        prompt = _append_context_to_prompt(prompt, audience=audience, notes=notes)
        ai_raw = await _call_ai(prompt)
    except Exception as e:
        if DEBUG_AI: print(f"[AI] Error building/calling: {e}")
        ai_raw = None

    return await generate_pdf_response(
        topic, audience, tone, hashtags, notes,
        ai_result=ai_raw, email=email, audience_type=audience_type,
        post_style=post_style, platforms=platforms_clean, word_count=word_count
    )

# ----- fallback that respects inputs -----
def fallback_content(
    topic: str, audience: str, platforms: List[str], user_hashtags: str,
    word_count: str, tone: str, audience_type: str, post_style: str
) -> Dict[str, Any]:
    t = topic or "Your Niche"
    base_tags = [h.lstrip("#").strip() for h in (user_hashtags or "").split() if h.strip()]
    para_counts = {"short": 1, "medium": 3, "long": 5}
    n_paras = para_counts.get((word_count or "medium").lower(), 3)
    body_pool = [
        f"{t.title()} for {audience or 'your audience'}: what it is and why it matters.",
        "Start simple: publish weekly, repurpose into 5–7 posts, and track one KPI.",
        "Keep one clear CTA per post so readers always know the next step.",
        "Use templates to stay consistent and save time.",
        "Review results every 2 weeks and double down on what works.",
    ]
    body = body_pool[:n_paras]

    defaults = {
        "instagram": f"{t.title()} made simple. Here’s a quick way to start today.",
        "linkedin":  f"{t.title()}: 3 practical steps to implement this week.",
        "tiktok":    f"One {t} tactic I use to save time every week.",
        "twitter":   f"{t} in one line: simple, fast, actionable.",
        "x":         f"{t} in one line: simple, fast, actionable.",
        "facebook":  f"{t} tips that help people move faster. Are you using them yet?",
    }
    base_platform_tags = {
        "instagram": ["tips","howto","growth"],
        "linkedin":  ["strategy","operations","leadership"],
        "tiktok":    ["hacks","tools","workflow"],
        "twitter":   ["insights","threads"],
        "x":         ["insights","threads"],
        "facebook":  ["community","local"],
    }

    chosen = platforms or ["Instagram","LinkedIn","TikTok","Twitter","Facebook"]
    captions, hashtags = {}, {}
    for p in chosen:
        key = p.lower()
        captions[p] = defaults.get(key, f"{t}: quick takeaway for {p}.")
        hashtags[p] = list(dict.fromkeys(base_tags + base_platform_tags.get(key, [])))

    return {
        "blog": {
            "headline": f"{t.title()}",
            "intro": f"{t} can work for small teams too—here’s a simple way to start.",
            "body": body,
            "bullets": [
                "Publish consistently with a simple template",
                "Repurpose one piece into multiple posts",
                "Track one KPI for 2–4 weeks"
            ],
            "cta": "Ready to put this into action today?"
        },
        "captions": captions,
        "hashtags": hashtags
    }

# ----- PDF handler -----
async def generate_pdf_response(
    topic: str, audience: str, tone: str, hashtags: str, notes: str,
    ai_result: Optional[str], email: str, audience_type: str, post_style: str,
    platforms: List[str], word_count: str
):
    clean_post_style = "" if (post_style or "").lower() == "general" else post_style

    # Normalize AI or fallback content
>>>>>>> 5a37524 (Initial commit of Content365 project)
    if ai_result:
        try:
            gpt_response = _normalize_ai_result(ai_result)
            if not gpt_response or "blog" not in gpt_response:
                raise ValueError("Normalization failed")
<<<<<<< HEAD
        except Exception:
            gpt_response = fallback_content()
    else:
        gpt_response = fallback_content()
=======
        except Exception as e:
            if DEBUG_AI: print(f"[AI] Normalize error -> fallback: {e}")
            gpt_response = fallback_content(
                topic, audience, platforms, hashtags, word_count, tone, audience_type, post_style
            )
    else:
        gpt_response = fallback_content(
            topic, audience, platforms, hashtags, word_count, tone, audience_type, post_style
        )

    # --- Normalize "AI" casing in the generated content (blog text only here) ---
    try:
        _blog = gpt_response.get("blog") or {}
        # strings
        for k in ("headline", "intro", "cta"):
            _blog[k] = _fix_ai_casing(_blog.get(k, ""))
        # lists
        _blog["body"] = [_fix_ai_casing(x) for x in (_blog.get("body") or [])]
        _blog["bullets"] = [_fix_ai_casing(x) for x in (_blog.get("bullets") or [])]
        gpt_response["blog"] = _blog
    except Exception as _e:
        if DEBUG_AI: print(f"[AI] Casing normalize (blog) skipped: {_e}")

    # --- Enforce per-platform rules & normalize keys before PDF ---
    # User-selected platforms (labels) -> slugs
    selected_slugs = _valid_platforms([_norm_platform(p) for p in platforms])

    caps_in: Dict[str, Any] = (gpt_response.get("captions") or {})
    tags_in: Dict[str, Any] = (gpt_response.get("hashtags") or {})

    captions: Dict[str, Any] = {}
    hashtags_dict: Dict[str, List[str]] = {}

    # Robust key variants so TitleCase keys (LinkedIn/TikTok) are found
    SPECIAL = {
        "instagram": "Instagram",
        "linkedin":  "LinkedIn",
        "tiktok":    "TikTok",
        "x":         "Twitter",   # some outputs still use "Twitter"
        "facebook":  "Facebook",
    }

    for slug in selected_slugs:
        # Try to fetch caption using multiple key variants
        variants = {
            slug,
            slug.upper(),
            slug.capitalize(),
            SPECIAL.get(slug, ""),
        }
        variants = {v for v in variants if v}  # drop empty

        cap = ""
        for k in variants:
            v = caps_in.get(k)
            if isinstance(v, dict):
                cap = v.get("text") or v.get("caption") or ""
            elif isinstance(v, str):
                cap = v
            if cap:
                break

        # Ensure consistent AI casing in captions (no impact on hashtag logic)
        cap = _fix_ai_casing(cap)

        # Collect raw tags (list or comma/space-separated string)
        raw_tags: List[str] = []
        for k in variants:
            v = tags_in.get(k)
            if isinstance(v, list):
                raw_tags = [str(x) for x in v]
                break
            elif isinstance(v, str):
                raw_tags = [p.strip() for p in re.split(r"[\s,]+", v) if p.strip()]
                break

        # Enforce per-platform limits (keeps your 3-arg signature)
        clamped = enforce_hashtag_rules(slug, raw_tags, cap or "")

        captions[slug] = cap
        hashtags_dict[slug] = clamped

    # Build final payload for the PDF generator
    pdf_payload = {
        "blog": _to_pdf_schema(gpt_response)["blog"],
        "captions": captions,
        "hashtags": hashtags_dict,
    }
>>>>>>> 5a37524 (Initial commit of Content365 project)

    filename = f"{uuid.uuid4().hex[:12]}.pdf"
    filepath = os.path.join(OUTPUT_FOLDER, filename)
    brand = {
<<<<<<< HEAD
        "brand_name": os.getenv("BRAND_NAME", "Content365"),
        "website": os.getenv("APP_URL", "content365.xyz"),
        "logo_path": os.getenv("LOGO_PATH", "assets/logo.png"),
        "primary_color": (0.12, 0.46, 0.95),
        "footer_text": f"© {datetime.now().year} Content365 — Smart marketing packs",
    }
    pdf_payload = _to_pdf_schema(gpt_response)
    generate_pdf(pdf_payload, output_path=filepath, brand_config=brand)

    # ---- Email delivery (optional, non-blocking) ----
    if email and "@" in email:
        try:
            send_pdf_email(
                to_email=email,
                pdf_path=filepath,
                subject="Your Content365 Marketing Pack",
                body_text="Your PDF is attached. Thanks for using Content365!"
            )
        except Exception:
            # Do not block the response if email fails
            pass

    return FileResponse(filepath, media_type="application/pdf", filename=filename)

def fallback_content():
    return {
        "blog": {
            "title": "The Future of AI in Local Marketing",
            "intro": "AI is no longer just for enterprise giants. Small businesses are using it to personalize outreach, reduce costs, and grow smarter.",
            "bullets": [
                "Automated content generation saves 10+ hours/week",
                "AI-powered chat boosts conversions",
                "Predictive targeting increases engagement"
            ],
            "cta": "Start using AI to grow your business today!"
        },
        "captions": {
            "Instagram": "AI isn’t just for big tech anymore. Here's how small businesses are leveling up 📈🚀",
            "LinkedIn": "AI adoption is redefining local marketing. Here are 3 ways to implement it today.",
            "TikTok": "Here’s an AI trick I use to save 10 hours every week 👇",
            "Twitter": "AI is the new marketing intern. Smart, fast, always on. #AIinMarketing",
            "Facebook": "AI tools are helping local businesses save time and grow faster. Are you using them yet?"
        },
        "hashtags": {
            "Instagram": ["AIforBusiness", "ContentMarketing", "SmallBizGrowth", "MarketingTips", "AutomationWins"],
            "LinkedIn": ["AIMarketing", "Leadership", "DigitalStrategy"],
            "TikTok": ["AIHacks", "MarketingTools", "SmallBusiness"],
            "Twitter": ["AI2025", "GrowthHacking"],
            "Facebook": ["AIMarketing", "LocalBusiness"]
        }
    }

# --- Utility & Health Routes ---
>>>>>>> 2ed0c2a (chore: wire Gemini provider + provider_router)

@app.get("/thank-you", response_class=HTMLResponse)
async def thank_you(request: Request):
    return templates.TemplateResponse("thank_you.html", {"request": request})
<<<<<<< HEAD
=======

@app.get("/health/pdf")
async def health_pdf():
    try:
        from utils.pdf_generator import get_pdf_engine_info
        info = get_pdf_engine_info()
    except Exception:
        info = {"engine": "unknown"}
    fonts = {
        "regular_exists": os.path.exists("assets/fonts/DejaVuSans.ttf"),
        "bold_exists": os.path.exists("assets/fonts/DejaVuSans-Bold.ttf"),
    }
    return {"engine": info, "fonts": fonts}

@app.get("/health/llm")
async def health_llm():
    return {
        "provider_router_enabled": ENABLE_PROVIDER_ROUTER,
        "llm_api_url_set": bool(LLM_API_URL),
        "llm_model_set": bool(LLM_MODEL),
        "paywall_enabled": ENABLE_PAYWALL,
    }

@app.get("/health/email")
async def health_email():
    return {
        "sendgrid_api_key_set": bool(os.getenv("SENDGRID_API_KEY", "").strip()),
        "from_email_set": bool(os.getenv("FROM_EMAIL", "").strip()),
        "from_name_set": bool(os.getenv("FROM_NAME", "").strip()),
    }

@app.get("/sample")
async def sample():
    """
    Quick no-AI sample PDF for testing layout/branding without hitting providers.
    """
    fc = fallback_content()
    filename = f"sample-{uuid.uuid4().hex[:8]}.pdf"
    filepath = os.path.join(OUTPUT_FOLDER, filename)
    brand = {
        "brand_name": os.getenv("BRAND_NAME", "Content365"),
        "website": os.getenv("APP_URL", "content365.xyz"),
        "logo_path": os.getenv("LOGO_PATH", "assets/logo.png"),
        "primary_color": (0.12, 0.46, 0.95),
        "footer_text": f"© {datetime.now().year} Content365 — Smart marketing packs",
    }
    pdf_payload = _to_pdf_schema(fc)
    generate_pdf(pdf_payload, output_path=filepath, brand_config=brand)
    return FileResponse(filepath, media_type="application/pdf", filename=filename)

@app.get("/status")
async def status():
    return JSONResponse({
        "ok": True,
        "app_url": APP_URL,
        "output_folder": OUTPUT_FOLDER,
        "time": datetime.utcnow().isoformat() + "Z"
    })
>>>>>>> 2ed0c2a (chore: wire Gemini provider + provider_router)
=======
        "brand_name": BRAND_NAME,
        "website": BRAND_WEBSITE,   # pdf generator will auto-link https:// if missing
        "logo_path": LOGO_PATH,
        "primary_color": (0.12, 0.46, 0.95),
        "footer_text": f"© {datetime.now().year} {BRAND_NAME} — Smart marketing packs",
    }

    generate_pdf(pdf_payload, output_path=filepath, brand_config=brand)

    if email and "@" in email:
        try:
            send_pdf_email(
                to_email=email, pdf_path=filepath,
                subject="Your Content365 Marketing Pack",
                body_text="Your PDF is attached. Thanks for using Content365!"
            )
        except Exception as e:
            if DEBUG_AI: print(f"[EMAIL] send_pdf_email failed: {e}")

    return FileResponse(filepath, media_type="application/pdf", filename=filename)
>>>>>>> 5a37524 (Initial commit of Content365 project)
