from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
import stripe
import os
from utils.pdf_generator import generate_dynamic_pdf

router = APIRouter()

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "").strip()
PRICE_ID = os.getenv("STRIPE_PRICE_ID", "").strip()
APP_URL = os.getenv("APP_URL", "").strip().rstrip('/')

if not STRIPE_SECRET_KEY:
    raise RuntimeError("STRIPE_SECRET_KEY is missing.")
if not PRICE_ID:
    raise RuntimeError("STRIPE_PRICE_ID is missing.")
if not APP_URL.startswith("http"):
    raise RuntimeError(f"APP_URL looks invalid: {APP_URL}")

stripe.api_key = STRIPE_SECRET_KEY

@router.get("/create-checkout-session")
async def create_checkout_session():
    try:
        print(f"Creating checkout session with PRICE_ID: {PRICE_ID}, APP_URL: {APP_URL}")
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{'price': PRICE_ID, 'quantity': 1}],
            mode='payment',
            success_url=f"{APP_URL}/success",
            cancel_url=f"{APP_URL}/canceled",
        )
        return {"url": session.url}
    except Exception as e:
        print(f"Stripe error: {e}")
        raise HTTPException(status_code=500, detail="Stripe session creation failed.")

@router.get("/success")
async def success(background_tasks: BackgroundTasks):
    try:
        print("Generating dynamic PDF...")
        pdf_path = generate_dynamic_pdf(topic="digital marketing")
        background_tasks.add_task(os.remove, pdf_path)
        return FileResponse(pdf_path, media_type='application/pdf', filename="content_pack.pdf")
    except Exception as e:
        print(f"PDF generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate content pack.")
