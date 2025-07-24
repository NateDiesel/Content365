import json
# -*- coding: utf-8 -*-
from fastapi import FastAPI, Request, Form, Query
from typing import List
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from utils.pdf_generator import generate_pdf
from utils.openrouter import call_openrouter
from utils.prompt_loader import load_prompt_template
from urllib.parse import quote
import stripe
import uuid
import os

load_dotenv()

app = FastAPI()

# Stripe and app config
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
APP_URL = os.getenv("APP_URL", "http://localhost:8000")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")
ENABLE_PAYWALL = os.getenv("ENABLE_PAYWALL", "false").lower() == "true"

# Output folder
OUTPUT_FOLDER = "generated_pdfs"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Templates + static
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/form", response_class=HTMLResponse)
async def form_get(request: Request):
    return templates.TemplateResponse("form.html", {"request": request})


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
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
            mode="payment",
            success_url=f"{APP_URL}/success?topic={quote(topic)}&audience={quote(audience)}"
                        f"&tone={quote(tone)}&hashtags={quote(hashtags)}&notes={quote(notes)}"
                        f"&platforms={platforms_encoded}&word_count={word_count}&email={quote(email)}",
            cancel_url=f"{APP_URL}/form"
        )
        return RedirectResponse(session.url, status_code=303)

    return await generate_pdf_response(topic, audience, tone, hashtags, notes, ai_result, email)


@app.get("/success")
async def success(
    topic: str,
    audience: str = "",
    tone: str = "",
    hashtags: str = "",
    notes: str = "",
    platforms: List[str] = Query([]),
    word_count: str = Query("medium"),
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
    content_dict = {
        "blog_post": ai_result,
        "lead_magnet": f"Top tips for {audience or 'your niche'} success in 2025",
        "seo_keywords": f"{topic.lower()}, {audience.lower()} marketing, AI content tools",
                try:
        social_captions = json.loads(ai_result)
    except json.JSONDecodeError:
        social_captions = {"General": [ai_result]}  # fallback if invalid JSON
        "hashtags": hashtags,
        "tips": notes
    }

    filename = f"{uuid.uuid4().hex[:12]}.pdf"
    filepath = os.path.join(OUTPUT_FOLDER, filename)
    generate_pdf(content_dict=content_dict)

    return FileResponse(filepath, media_type="application/pdf", filename=filename)


@app.get("/thank-you", response_class=HTMLResponse)
async def thank_you(request: Request):
    return templates.TemplateResponse("thank_you.html", {"request": request})
