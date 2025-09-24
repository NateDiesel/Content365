# -*- coding: utf-8 -*-
import os, re, uuid, json
from typing import Optional, List, Dict, Any
from datetime import datetime
from urllib.parse import quote

from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import (
    HTMLResponse, FileResponse, RedirectResponse,
    JSONResponse, PlainTextResponse
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from dotenv import load_dotenv

# Optional deps (never hard-crash if missing)
try:
    import stripe  # noqa: F401
except Exception:
    stripe = None
try:
    import httpx
except Exception:
    httpx = None
try:
    import requests
except Exception:
    requests = None

# --- Internal modules ---
from utils.pdf_generator import generate_pdf
try:
    from utils.prompt_loader import load_prompt_template
except Exception:
    load_prompt_template = None
try:
    from utils.prompt_builder import build_prompt
except Exception:
    build_prompt = None
try:
    from utils.hashtag_rules import enforce_hashtag_rules as _enforce_hashtag_rules
except Exception:
    _enforce_hashtag_rules = None
try:
    from utils.send_email import send_pdf_email
except Exception:
    send_pdf_email = None

# ------------------------------------------------------------------------------
# ENV / CONFIG
# ------------------------------------------------------------------------------
load_dotenv(override=True)

APP_VERSION     = os.getenv("APP_VERSION", "v4.3-release")
APP_URL         = os.getenv("APP_URL", "http://127.0.0.1:8000")
ENABLE_PAYWALL  = (os.getenv("ENABLE_PAYWALL", "false").strip().lower() == "true")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID", "")
if stripe:
    try:
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    except Exception:
        pass

OUTPUT_FOLDER   = os.getenv("OUTPUT_DIR", "generated")
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

BRAND_NAME      = os.getenv("BRAND_NAME", "Content365")
BRAND_WEBSITE   = (os.getenv("BRAND_WEBSITE") or os.getenv("APP_DOMAIN") or "content365.xyz").strip()
LOGO_PATH       = os.getenv("LOGO_PATH", "assets/logo.png")

AI_PROVIDER     = (os.getenv("AI_PROVIDER", "openrouter") or "openrouter").strip().lower()
PROVIDER_ORDER  = [p.strip().lower() for p in (os.getenv("PROVIDER_ORDER") or AI_PROVIDER).split(",") if p.strip()]
LLM_API_URL     = os.getenv("LLM_API_URL", "").strip()
LLM_MODEL       = os.getenv("LLM_MODEL", "").strip()
OPENROUTER_KEY  = os.getenv("OPENROUTER_API_KEY", "")
HAS_OR_KEY      = bool(OPENROUTER_KEY)
HAS_GEM_KEY     = bool(os.getenv("GOOGLE_API_KEY"))
STRICT_JSON_PREFIX = (
    "IMPORTANT: Return ONLY valid JSON matching the requested schema. "
    "Do not include code fences, commentary, or markdown. "
)

# ------------------------------------------------------------------------------
# APP
# ------------------------------------------------------------------------------
app = FastAPI(title="Content365", version=APP_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in (os.getenv("CORS_ALLOW_ORIGINS") or "*").split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")
templates.env.globals["now"] = lambda: datetime.now()

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/assets", StaticFiles(directory="assets"), name="assets")
app.mount("/generated", StaticFiles(directory=OUTPUT_FOLDER), name="generated")

# ------------------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------------------
_AI_WORD_RX = re.compile(r"\bai\b", flags=re.IGNORECASE)

def _fix_ai_casing(s: Optional[str]) -> str:
    if not s:
        return ""
    s = s.replace("\u00A0", " ")
    return _AI_WORD_RX.sub("AI", s)

def _norm_platform(p: str) -> str:
    p = (p or "").strip().lower()
    if p == "twitter":
        return "x"
    return p

def _valid_platforms(seq):
    allowed = {"instagram", "tiktok", "linkedin", "x", "facebook"}
    out, seen = [], set()
    for s in (seq or []):
        ss = _norm_platform(s)
        if ss in allowed and ss not in seen:
            seen.add(ss)
            out.append(ss)
    return out

def _normalize_platform_labels(platforms: List[str]) -> List[str]:
    out = []
    for p in platforms or []:
        pl = (p or "").strip()
        if pl.lower() in {"x", "twitter"}:
            pl = "Twitter"
        out.append(pl)
    return out

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

def _safe_build_prompt(topic: str, tone: str, audience_type: str,
                       post_style: str, word_count: str, platforms_str: str) -> str:
    if build_prompt:
        return build_prompt(
            topic=topic, tone=tone, audience_type=audience_type,
            post_style=post_style, word_count=word_count, platforms=platforms_str
        )
    if load_prompt_template:
        tmpl = load_prompt_template()
        return tmpl.format(
            topic=topic, tone=tone, audience_type=audience_type,
            post_style=post_style, word_count=word_count, platforms=platforms_str
        )
    return (
        f"Create JSON with keys blog,captions,hashtags for topic='{topic}', tone='{tone}', "
        f"audience_type='{audience_type}', style='{post_style}', word_count='{word_count}', "
        f"platforms='{platforms_str}'. Ensure valid JSON only."
    )

def _append_context_to_prompt(prompt: str, audience: str, notes: str) -> str:
    extra = []
    if audience: extra.append(f"\nAudience Details: {audience}")
    if notes:    extra.append(f"\nCreator Notes: {notes}")
    return f"{prompt.rstrip()}{''.join(extra)}" if extra else prompt

def _parse_platforms_param(raw_platforms: List[str]) -> List[str]:
    if not raw_platforms: return []
    if len(raw_platforms) == 1 and ("," in raw_platforms[0] or " " in raw_platforms[0]):
        return [p.strip() for p in re.split(r"[,\s]+", raw_platforms[0]) if p.strip()]
    return raw_platforms

def _apply_hashtag_rules(slug: str, tags: List[str], caption: str) -> List[str]:
    if not _enforce_hashtag_rules:
        tags = [("#" + t.lstrip("#")) for t in tags if str(t).strip()]
        return tags[:6]
    try:
        return _enforce_hashtag_rules(slug, tags, caption)  # legacy signature
    except TypeError:
        try:
            out = _enforce_hashtag_rules({slug: tags})       # dict signature
            return [("#" + t.lstrip("#")) for t in (out.get(slug) or [])]
        except Exception:
            tags = [("#" + t.lstrip("#")) for t in tags if str(t).strip()]
            return tags[:6]

# ------------------------------------------------------------------------------
# AI PROVIDERS
# ------------------------------------------------------------------------------
async def _call_local_llm(prompt: str) -> Optional[str]:
    if not (LLM_API_URL and LLM_MODEL):
        return None
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": "Follow instructions exactly. Output ONLY valid JSON."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.6, "top_p": 0.9, "max_tokens": 1200, "stream": False, "stop": ["```"],
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
    except Exception:
        return None

async def _call_ai(prompt: str) -> Optional[str]:
    if not prompt.startswith(STRICT_JSON_PREFIX):
        prompt = f"{STRICT_JSON_PREFIX}{prompt}"
    order = [("gemini" if p in ("gemini","google") else "openrouter" if p in ("openrouter","or") else "local") for p in (PROVIDER_ORDER or [AI_PROVIDER])]
    def _append_if(lst, v):
        if v not in lst: lst.append(v)
    if HAS_OR_KEY: _append_if(order, "openrouter")
    if HAS_GEM_KEY: _append_if(order, "gemini")
    if LLM_API_URL: _append_if(order, "local")
    for provider in order:
        try:
            if provider == "local":
                res = await _call_local_llm(prompt)
                if res: return res
            elif provider == "openrouter" and HAS_OR_KEY:
                from utils.openrouter import generate_text as call_openrouter  # async
                return await call_openrouter(prompt)
            elif provider == "gemini" and HAS_GEM_KEY:
                from utils.gemini import generate_text as call_gemini         # async
                return await call_gemini(prompt)
        except Exception:
            continue
    return None

# ------------------------------------------------------------------------------
# ROUTES
# ------------------------------------------------------------------------------
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

# ---- Core helper: generate + save, return filename ----
def _generate_and_save_pdf(pdf_payload: Dict[str, Any], brand: Dict[str, Any]) -> str:
    file_name = f"{uuid.uuid4().hex[:12]}.pdf"
    out_path = os.path.join(OUTPUT_FOLDER, file_name)
    try:
        # Signature A: (payload, output_path=, brand_config=)
        generate_pdf(pdf_payload, output_path=out_path, brand_config=brand)
    except TypeError:
        # Signature B: returns bytes
        pdf_bytes = generate_pdf(**pdf_payload, **brand)
        with open(out_path, "wb") as fh:
            fh.write(pdf_bytes)
    return file_name

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
    company_name: str = Form(""),
):
    platforms_clean = _normalize_platform_labels(platforms or [])
    platforms_str = ", ".join(platforms_clean)
    clean_post_style = "" if (post_style or "").lower() == "general" else post_style

    try:
        prompt = _safe_build_prompt(
            topic=_fix_ai_casing(topic),
            tone=tone,
            audience_type=audience_type,
            post_style=clean_post_style,
            word_count=word_count,
            platforms_str=platforms_str,
        )
        prompt = _append_context_to_prompt(prompt, audience=audience, notes=notes)
    except Exception as e:
        prompt = f'{{"error":"Failed to format prompt: {e}"}}'

    ai_raw = await _call_ai(prompt)
    ai_success = ai_raw is not None

    if ENABLE_PAYWALL and ai_success and STRIPE_PRICE_ID and stripe:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
            mode="payment",
            success_url=(
                f"{APP_URL}/success?"
                f"topic={quote(topic)}&audience={quote(audience)}&tone={quote(tone)}"
                f"&hashtags={quote(hashtags)}&notes={quote(notes)}&platforms={quote(platforms_str)}"
                f"&word_count={word_count}&email={quote(email)}&audience_type={quote(audience_type)}"
                f"&post_style={quote(post_style)}&company_name={quote(company_name)}"
            ),
            cancel_url=f"{APP_URL}/form",
        )
        return RedirectResponse(session.url, status_code=303)

    file_name = await generate_pdf_response(
        topic=topic, audience=audience, tone=tone, hashtags=hashtags, notes=notes,
        ai_result=ai_raw, email=email, audience_type=audience_type, post_style=post_style,
        platforms=platforms_clean, word_count=word_count, company_name=company_name,
    )
    return templates.TemplateResponse(
        "result.html",
        {"request": request, "pdf_url": f"/generated/{file_name}", "download_url": f"/generated/{file_name}", "file_name": file_name},
    )

@app.get("/success")
async def success(
    request: Request,
    topic: str,
    audience: str = "",
    tone: str = "",
    hashtags: str = "",
    notes: str = "",
    platforms: List[str] = Query([]),
    word_count: str = Query("medium"),
    email: str = "",
    audience_type: str = Query("B2C"),
    post_style: str = Query("General"),
    company_name: str = Query(""),
):
    platforms_clean = _normalize_platform_labels(_parse_platforms_param(platforms))
    platforms_str = ", ".join(platforms_clean)
    clean_post_style = "" if (post_style or "").lower() == "general" else post_style

    try:
        prompt = _safe_build_prompt(
            topic=_fix_ai_casing(topic),
            tone=tone,
            audience_type=audience_type,
            post_style=clean_post_style,
            word_count=word_count,
            platforms_str=platforms_str,
        )
        prompt = _append_context_to_prompt(prompt, audience=audience, notes=notes)
        ai_raw = await _call_ai(prompt)
    except Exception:
        ai_raw = None

    file_name = await generate_pdf_response(
        topic=topic, audience=audience, tone=tone, hashtags=hashtags, notes=notes,
        ai_result=ai_raw, email=email, audience_type=audience_type, post_style=post_style,
        platforms=platforms_clean, word_count=word_count, company_name=company_name,
    )
    return templates.TemplateResponse(
        "result.html",
        {"request": request, "pdf_url": f"/generated/{file_name}", "download_url": f"/generated/{file_name}", "file_name": file_name},
    )

# ----- fallback (no external calls) -----
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

# ----- PDF handler: returns file_name ONLY; routes render preview -----
async def generate_pdf_response(
    topic: str, audience: str, tone: str, hashtags: str, notes: str,
    ai_result: Optional[str], email: str, audience_type: str, post_style: str,
    platforms: List[str], word_count: str, company_name: str = "",
) -> str:
    if ai_result:
        try:
            gpt_response = _normalize_ai_result(ai_result)
            if not gpt_response or "blog" not in gpt_response:
                raise ValueError("Normalization failed")
        except Exception:
            gpt_response = fallback_content(
                topic, audience, platforms, hashtags, word_count, tone, audience_type, post_style
            )
    else:
        gpt_response = fallback_content(
            topic, audience, platforms, hashtags, word_count, tone, audience_type, post_style
        )
    try:
        _blog = gpt_response.get("blog") or {}
        for k in ("headline", "intro", "cta"):
            _blog[k] = _fix_ai_casing(_blog.get(k, ""))
        _blog["body"] = [_fix_ai_casing(x) for x in (_blog.get("body") or [])]
        _blog["bullets"] = [_fix_ai_casing(x) for x in (_blog.get("bullets") or [])]
        gpt_response["blog"] = _blog
    except Exception:
        pass

    selected_slugs = _valid_platforms([_norm_platform(p) for p in platforms])
    caps_in: Dict[str, Any] = (gpt_response.get("captions") or {})
    tags_in: Dict[str, Any] = (gpt_response.get("hashtags") or {})
    captions: Dict[str, str] = {}
    hashtags_dict: Dict[str, List[str]] = {}
    SPECIAL = {
        "instagram": "Instagram",
        "linkedin":  "LinkedIn",
        "tiktok":    "TikTok",
        "x":         "Twitter",
        "facebook":  "Facebook",
    }
    for slug in selected_slugs:
        variants = {slug, slug.upper(), slug.capitalize(), SPECIAL.get(slug, "")}
        variants = {v for v in variants if v}
        cap = ""
        for k in variants:
            v = caps_in.get(k)
            if isinstance(v, dict):
                cap = v.get("text") or v.get("caption") or ""
            elif isinstance(v, str):
                cap = v
            if cap:
                break
        cap = _fix_ai_casing(cap)
        raw_tags: List[str] = []
        for k in variants:
            v = tags_in.get(k)
            if isinstance(v, list):
                raw_tags = [str(x) for x in v]; break
            elif isinstance(v, str):
                raw_tags = [p.strip() for p in re.split(r"[\s,]+", v) if p.strip()]; break
        hashtags_dict[slug] = _apply_hashtag_rules(slug, raw_tags, cap or "")
        captions[slug] = cap

    pdf_payload = {
        "blog": _to_pdf_schema(gpt_response)["blog"],
        "captions": captions,
        "hashtags": hashtags_dict,
    }

    brand = {
        "brand_name": BRAND_NAME,
        "website": BRAND_WEBSITE,
        "logo_path": LOGO_PATH,
        "primary_color": (0.12, 0.46, 0.95),
        "footer_text": f"© {datetime.now().year} {BRAND_NAME} — Smart marketing packs",
        "company_name": company_name,
        "hero_hook": "Close 2–3 extra deals this quarter with AI.",
        "hero_cta":  "Get the free toolkit → content365.xyz/real-estate-ai",
    }
    file_name = _generate_and_save_pdf(pdf_payload, brand)

    if email and "@" in email and send_pdf_email:
        try:
            out_path = os.path.join(OUTPUT_FOLDER, file_name)
            send_pdf_email(
                to_email=email, pdf_path=out_path,
                subject="Your Content365 Marketing Pack",
                body_text="Your PDF is attached. Thanks for using Content365!",
            )
        except Exception:
            pass
    return file_name

# ----- misc / health -----
@app.get("/thank-you", response_class=HTMLResponse)
async def thank_you(request: Request):
    return templates.TemplateResponse("thank_you.html", {"request": request})

@app.get("/healthz", response_class=PlainTextResponse)
async def healthz():
    return "ok"

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
        "llm_api_url_set": bool(LLM_API_URL),
        "llm_model_set": bool(LLM_MODEL),
        "openrouter_key_set": HAS_OR_KEY,
        "gemini_key_set": HAS_GEM_KEY,
        "paywall_enabled": ENABLE_PAYWALL,
    }

@app.get("/health/email")
async def health_email():
    return {
        "sendgrid_api_key_set": bool(os.getenv("SENDGRID_API_KEY", "").strip()),
        "from_email_set": bool(os.getenv("FROM_EMAIL", "").strip()),
        "from_name_set": bool(os.getenv("FROM_NAME", "").strip()),
    }

@app.get("/status")
async def status():
    return JSONResponse({
        "ok": True,
        "app_url": APP_URL,
        "output_folder": OUTPUT_FOLDER,
        "time": datetime.utcnow().isoformat() + "Z",
        "version": APP_VERSION,
        "cwd": os.getcwd(),
    })
