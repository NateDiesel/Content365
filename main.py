from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from utils.pdf_generator import generate_dynamic_pdf
import stripe
import uuid
import os

load_dotenv()

app = FastAPI()

# Setup Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
APP_URL = os.getenv("APP_URL", "http://localhost:8001")
ENABLE_PAYWALL = os.getenv("ENABLE_PAYWALL", "false").lower() == "true"
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")

# Setup folders
OUTPUT_FOLDER = "generated_pdfs"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Templates & Static
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
    if ENABLE_PAYWALL:
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

    filename = f"{uuid.uuid4().hex[:12]}.pdf"
    filepath = os.path.join(OUTPUT_FOLDER, filename)

    generate_dynamic_pdf(
        topic=topic,
        audience=audience,
        tone=tone,
        notes=notes,
        custom_hashtags=hashtags,
        output_path=filepath
    )

    return FileResponse(filepath, media_type="application/pdf", filename=filename)

@app.get("/success")
async def success(
    topic: str,
    audience: str = "",
    tone: str = "",
    hashtags: str = "",
    notes: str = ""
):
    filename = f"{uuid.uuid4().hex[:12]}.pdf"
    filepath = os.path.join(OUTPUT_FOLDER, filename)

    generate_dynamic_pdf(
        topic=topic,
        audience=audience,
        tone=tone,
        notes=notes,
        custom_hashtags=hashtags,
        output_path=filepath
    )

    return FileResponse(filepath, media_type="application/pdf", filename=filename)
