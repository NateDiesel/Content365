from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from utils.pdf_generator import generate_pdf
from utils.openrouter import call_openrouter
import stripe
import uuid
import os

load_dotenv()

app = FastAPI()

# Stripe config
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
APP_URL = os.getenv("APP_URL", "http://localhost:8000")
ENABLE_PAYWALL = os.getenv("ENABLE_PAYWALL", "false").lower() == "true"
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")

# Output folder
OUTPUT_FOLDER = "generated_pdfs"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Static and templates
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
    notes: str = Form("")
):
    prompt = f"Write a blog post about '{topic}' in a '{tone}' tone. Include social media captions with emojis."

    try:
        ai_result = await call_openrouter(prompt)
        ai_success = True
    except Exception:
        ai_result = f"""⚠️ Our AI service is currently unavailable.

In the meantime, here’s a prewritten starter pack on AI trends:

---

📄 **Mini Blog**  
AI in 2025 will reshape industries from healthcare to education. Staying updated is essential. Here are 3 key predictions:
- ✨ Democratization of AI tools
- 🧠 Explosive growth of personal AI assistants
- 📊 AI-driven decisions in everyday life

---

📣 **Social Captions**  
1. “2025: The year AI gets personal. Are you ready? 🤖🚀”  
2. “The AI wave is here — freelancers, grab your board 🏄‍♂️📈”  
3. “Let’s talk AI trends. Spoiler: It’s moving fast. 🔥”

---

You weren’t charged for this fallback pack.
"""
        ai_success = False

    # Free if AI fails, Stripe if ENABLE_PAYWALL + success
    if ENABLE_PAYWALL and ai_success:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price": STRIPE_PRICE_ID,
                "quantity": 1
            }],
            mode="payment",
            success_url=f"{APP_URL}/success?topic={topic}&audience={audience}&tone={tone}&hashtags={hashtags}&notes={notes}",
            cancel_url=f"{APP_URL}/form"
        )
        return RedirectResponse(session.url, status_code=303)

    return await generate_pdf_response(topic, audience, tone, hashtags, notes, ai_result)


@app.get("/success")
async def success(
    topic: str,
    audience: str = "",
    tone: str = "",
    hashtags: str = "",
    notes: str = ""
):
    prompt = f"Write a blog post about '{topic}' in a '{tone}' tone. Include social media captions with emojis."
    try:
        ai_result = await call_openrouter(prompt)
    except Exception:
        ai_result = f"""⚠️ Our AI service is currently unavailable.

In the meantime, here’s a prewritten starter pack on AI trends:

---

📄 **Mini Blog**  
AI in 2025 will reshape industries from healthcare to education. Staying updated is essential. Here are 3 key predictions:
- ✨ Democratization of AI tools
- 🧠 Explosive growth of personal AI assistants
- 📊 AI-driven decisions in everyday life

---

📣 **Social Captions**  
1. “2025: The year AI gets personal. Are you ready? 🤖🚀”  
2. “The AI wave is here — freelancers, grab your board 🏄‍♂️📈”  
3. “Let’s talk AI trends. Spoiler: It’s moving fast. 🔥”

---

You weren’t charged for this fallback pack.
"""

    return await generate_pdf_response(topic, audience, tone, hashtags, notes, ai_result)


async def generate_pdf_response(topic, audience, tone, hashtags, notes, ai_result):
    content = f"""📌 Topic: {topic}
🎯 Audience: {audience}
🗣 Tone: {tone}
🏷 Hashtags: {hashtags}
📝 Notes: {notes}

---

🤖 AI-Generated Blog Post & Captions:
{ai_result}"""

    filename = f"{uuid.uuid4().hex[:12]}.pdf"
    filepath = os.path.join(OUTPUT_FOLDER, filename)
    generate_pdf(content_blocks={"blog": content}, output_path=filepath)

    return FileResponse(filepath, media_type="application/pdf", filename=filename)


@app.get("/thank-you", response_class=HTMLResponse)
async def thank_you(request: Request):
    return templates.TemplateResponse("thank_you.html", {"request": request})