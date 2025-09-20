# -*- coding: utf-8 -*-
import json, uuid, os, re
from urllib.parse import quote
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_FOLDER = os.getenv("OUTPUT_DIR", "generated_pdfs")
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

templates = Jinja2Templates(directory="templates")
templates.env.globals["now"] = lambda: datetime.now()  # <-- make now() available in templates
app.mount("/static", StaticFiles(directory="static"), name="static")

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
    hashtags: Dict[str, List[str]] = {}
    caps = parsed.get("captions") or parsed.get("captions_by_platform") or {}
    if isinstance(caps, dict):
        for platform, block in caps.items():
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
    return hashtags

def _normalize_ai_result(ai_result: Any) -> Optional[Dict[str, Any]]:
    if ai_result is None:
        return None

    if isinstance(ai_result, dict):
        parsed = ai_result
    elif isinstance(ai_result, str):
        txt = _strip_code_fences(ai_result)
        txt = _extract_json_blob(txt)
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

    caps = parsed.get("captions_by_platform") or parsed.get("captions") or {}
    if not isinstance(caps, dict):
        caps = {}

    hashtags_block = parsed.get("hashtags")
    if not isinstance(hashtags_block, dict):
        hashtags_block = _coerce_hashtags({"captions": caps})

    norm: Dict[str, Any] = {
        "blog": blog,
        "captions": caps,
        "hashtags": enforce_hashtag_rules(hashtags_block) if hashtags_block else {}
    }
    return norm

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
    """Normalize common aliases (e.g., X -> Twitter) for consistent downstream handling."""
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
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": "Follow instructions exactly. Output ONLY valid JSON."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.6, "top_p": 0.9, "max_tokens": 1200, "stream": False, "stop": ["```"]
    }
    headers = {"Content-Type": "application/json"}
    try:
        if httpx:
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(LLM_API_URL, headers=headers, json=payload)
                r.raise_for_status()
                data = r.json()
        elif requests:
            r = requests.post(LLM_API_URL, headers=headers, json=payload, timeout=60)
            r.raise_for_status()
            data = r.json()
        else:
            return None
        return (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
    except Exception as e:
        if DEBUG_AI: print(f"[AI] Local LLM error: {e}")
        return None

async def _call_ai(prompt: str) -> Optional[str]:
    """
    Tries providers in order, with auto-rescue:
    - Uses PROVIDER_ORDER or AI_PROVIDER
    - If OpenRouter fails (e.g., 402) and a Gemini key exists, auto-tries Gemini
    - If Gemini fails and OpenRouter key exists, auto-tries OpenRouter
    - Tries local if configured
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
        "brand_name": BRAND_NAME,
        "website": BRAND_WEBSITE,            # <- use real domain for PDF header (auto-link in pdf_generator)
        "logo_path": LOGO_PATH,
        "primary_color": (0.12,0.46,0.95),
        "footer_text": f"© {datetime.now().year} {BRAND_NAME} — Smart marketing packs"
    }
    pdf_payload = _to_pdf_schema(fc)
    generate_pdf(pdf_payload, output_path=filepath, brand_config=brand)
    return FileResponse(filepath, media_type="application/pdf", filename=filename)

# ----- core form handlers -----
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
    email: str = Form(""),
    audience_type: str = Form("B2C"),
    post_style: str = Form("General"),
):
    platforms_clean = _normalize_platform_labels(platforms or [])
    platforms_str = ", ".join(platforms_clean)
    platforms_encoded = quote(platforms_str)
    clean_post_style = "" if (post_style or "").lower() == "general" else post_style

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

    if ENABLE_PAYWALL and ai_success and STRIPE_PRICE_ID:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
            mode="payment",
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

@app.get("/success")
async def success(
    topic: str,
    audience: str = "",
    tone: str = "",
    hashtags: str = "",
    notes: str = "",
    platforms: List[str] = Query([]),
    word_count: str = Query("medium"),
    email: str = "",
    audience_type: str = Query("B2C"),
    post_style: str = Query("General")
):
    platforms_clean = _normalize_platform_labels(_parse_platforms_param(platforms))
    platforms_str = ", ".join(platforms_clean)
    clean_post_style = "" if (post_style or "").lower() == "general" else post_style

    try:
        prompt = _safe_build_prompt(
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

    if ai_result:
        try:
            gpt_response = _normalize_ai_result(ai_result)
            if not gpt_response or "blog" not in gpt_response:
                raise ValueError("Normalization failed")
        except Exception as e:
            if DEBUG_AI: print(f"[AI] Normalize error -> fallback: {e}")
            gpt_response = fallback_content(
                topic, audience, platforms, hashtags, word_count, tone, audience_type, post_style
            )
    else:
        gpt_response = fallback_content(
            topic, audience, platforms, hashtags, word_count, tone, audience_type, post_style
        )

    filename = f"{uuid.uuid4().hex[:12]}.pdf"
    filepath = os.path.join(OUTPUT_FOLDER, filename)
    brand = {
        "brand_name": BRAND_NAME,
        "website": BRAND_WEBSITE,   # <- real domain (PDF code will auto-link with https:// if missing)
        "logo_path": LOGO_PATH,
        "primary_color": (0.12, 0.46, 0.95),
        "footer_text": f"© {datetime.now().year} {BRAND_NAME} — Smart marketing packs",
    }

    pdf_payload = _to_pdf_schema(gpt_response)
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
