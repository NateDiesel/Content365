from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from fastapi.responses import FileResponse, HTMLResponse
import stripe
import os
from Content365.utils.pdf_generator import generate_dynamic_pdf

router = APIRouter()

# Load environment variables
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "").strip()
PRICE_ID = os.getenv("STRIPE_PRICE_ID", "").strip()
APP_URL = os.getenv("APP_URL", "http://localhost:8000").strip().rstrip('/')

# Validate Stripe config
if not STRIPE_SECRET_KEY or not PRICE_ID:
    raise RuntimeError("Stripe credentials missing.")

stripe.api_key = STRIPE_SECRET_KEY

@router.get("/create-checkout-session")
async def create_checkout_session(request: Request):
    topic = request.query_params.get("topic", "digital marketing")

    try:
        print(f"Creating checkout session for topic: {topic}")
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{'price': PRICE_ID, 'quantity': 1}],
            mode='payment',
            success_url=f"{APP_URL}/success?session_id={{CHECKOUT_SESSION_ID}}&topic={topic}",
            cancel_url=f"{APP_URL}/canceled",
        )
        return {"url": session.url}
    except Exception as e:
        print("âŒ Stripe error:", e)
        raise HTTPException(status_code=500, detail="Stripe session creation failed.")

@router.get("/success")
async def success(request: Request, background_tasks: BackgroundTasks):
    topic = request.query_params.get("topic", "digital marketing")
    print(f"âœ… Stripe payment successful. Generating PDF for: {topic}")

    try:
        pdf_path = generate_dynamic_pdf(topic)
        filename = os.path.basename(pdf_path)

        # Optional: Delete file after download
        background_tasks.add_task(os.remove, pdf_path)

        # Render success page
        html = f"""
        <html>
        <head>
            <meta http-equiv="refresh" content="2;url=/download?file={filename}">
        </head>
        <body style="text-align:center; font-family:sans-serif; padding:40px;">
            <h1>âœ… Your AI Content Pack is Ready!</h1>
            <p>Auto-downloading your PDF... If not, <a href="/download?file={filename}">click here</a>.</p>
        </body>
        </html>
        """
        return HTMLResponse(content=html)

    except Exception as e:
        print("âŒ PDF generation failed:", e)
        raise HTTPException(status_code=500, detail="Failed to generate content pack.")

@router.get("/download")
async def download(file: str):
    path = f"./{file}"
    if os.path.exists(path):
        return FileResponse(path, media_type="application/pdf", filename=file)
    else:
        raise HTTPException(status_code=404, detail="File not found.")
