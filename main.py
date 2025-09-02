# -*- coding: utf-8 -*-
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
from urllib.parse import quote
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

    hashtags: Dict[str, List[str]] = {}
    caps = parsed.get("captions") or parsed.get("captions_by_platform") or {}
    if isinstance(caps, dict):
        for platform, block in caps.items():
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
    return hashtags

def _normalize_ai_result(ai_result: Any) -> Optional[Dict[str, Any]]:
    """
    Accept raw string (possibly fenced) from LLM, parse JSON, and
    produce a normalized dict with:
      { "blog": {...}, "captions": {...}, "hashtags": {...optional...} }
    - Supports 'captions' OR 'captions_by_platform'
    - Tolerates blog as str or dict; maps 'cta' -> 'CTA'
    """
    if ai_result is None:
        return None

    if isinstance(ai_result, dict):
        parsed = ai_result
    elif isinstance(ai_result, str):
        txt = _strip_code_fences(ai_result)
        txt = _extract_json_blob(txt)
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
    caps = parsed.get("captions_by_platform") or parsed.get("captions") or {}
    if not isinstance(caps, dict):
        caps = {}

    # ---- Hashtags (optional) ----
    hashtags_block = parsed.get("hashtags")
    if not isinstance(hashtags_block, dict):
        hashtags_block = _coerce_hashtags({"captions": caps})

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

    payload = {
        "model": LLM_MODEL,
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

    try:
        if httpx is not None:
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(LLM_API_URL, headers=headers, json=payload)
                r.raise_for_status()
                data = r.json()
        elif requests is not None:
            r = requests.post(LLM_API_URL, headers=headers, json=payload, timeout=60)
            r.raise_for_status()
            data = r.json()
        else:
            return None

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
    platforms_str = ", ".join(platforms_clean)
    platforms_encoded = quote(platforms_str)
    clean_post_style = "" if (post_style or "").lower() == "general" else post_style

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
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
            mode="payment",
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
    email: str = "",
    audience_type: str = Query("B2C"),
    post_style: str = Query("General")
):
    platforms_clean = _parse_platforms_param(platforms)
    platforms_str = ", ".join(platforms_clean)
    clean_post_style = "" if (post_style or "").lower() == "general" else post_style

    try:
        prompt = _safe_build_prompt(
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

    if ai_result:
        try:
            gpt_response = _normalize_ai_result(ai_result)
            if not gpt_response or "blog" not in gpt_response:
                raise ValueError("Normalization failed")
        except Exception:
            gpt_response = fallback_content()
    else:
        gpt_response = fallback_content()

    filename = f"{uuid.uuid4().hex[:12]}.pdf"
    filepath = os.path.join(OUTPUT_FOLDER, filename)
    brand = {
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
