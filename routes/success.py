from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse
import stripe
import os
from Content365.utils.pdf_generator import generate_dynamic_pdf
from Content365.utils.email_sender import send_pdf_email

router = APIRouter()

# Load environment variables
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "").strip()
PRICE_ID = os.getenv("STRIPE_PRICE_ID", "").strip()
APP_URL = os.getenv("APP_URL", "").strip().rstrip('/')

# Validate Stripe config
if not STRIPE_SECRET_KEY:
    raise RuntimeError("STRIPE_SECRET_KEY is missing.")
if not PRICE_ID:
    raise RuntimeError("STRIPE_PRICE_ID is missing.")
if not APP_URL.startswith("http"):
    raise RuntimeError(f"APP_URL looks invalid: {APP_URL}")

stripe.api_key = STRIPE_SECRET_KEY

@router.get("/", response_class=HTMLResponse)
async def topic_form():
    return """
    <html>
    <head>
        <title>Start Your AI Content Pack</title>
    </head>
    <body style="font-family: sans-serif; padding: 40px;">
        <h1>ðŸ§  Generate Your AI Content Pack</h1>
        <form action="/create-checkout-session" method="get">
            <label for="topic">What topic should your content be about?</label><br>
            <input type="text" name="topic" value="digital marketing" required>
            <br><br>
            <button type="submit">Buy & Generate</button>
        </form>
    </body>
    </html>
    """

@router.get("/create-checkout-session")
async def create_checkout_session(request: Request):
    topic = request.query_params.get("topic", "digital marketing")
    print(f"Creating checkout session with PRICE_ID: {PRICE_ID}, APP_URL: {APP_URL}, topic: {topic}")
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{'price': PRICE_ID, 'quantity': 1}],
            mode='payment',
            success_url=f"{APP_URL}/success?topic={topic}",
            cancel_url=f"{APP_URL}/canceled",
        )
        return {"url": session.url}
    except Exception as e:
        print(f"Stripe error: {e}")
        raise HTTPException(status_code=500, detail="Stripe session creation failed.")

@router.get("/success")
async def success(request: Request, background_tasks: BackgroundTasks):
    topic = request.query_params.get("topic", "digital marketing")
    print(f"Generating dynamic PDF for topic: {topic}")
    try:
        pdf_path = generate_dynamic_pdf(topic=topic)
        filename = os.path.basename(pdf_path)

        # Email it to the user
        recipient_email = "mnb.mushrooms@gmail.com"
        send_pdf_email(recipient_email, pdf_path)

        # Schedule deletion of the file
        background_tasks.add_task(os.remove, pdf_path)
        print("âœ… PDF generated and emailed!")

        html_content = f"""
        <html>
        <head>
            <title>Success</title>
            <meta http-equiv="refresh" content="5;url=/static/index.html">
        </head>
        <body style="font-family: sans-serif; text-align: center; padding: 40px;">
            <h1>âœ… Content Pack Sent!</h1>
            <p>Your AI-generated content pack is being downloaded and has also been emailed to <strong>{recipient_email}</strong>.</p>
            <p>If the download doesn't start automatically, <a href='/download?file={filename}'>click here</a>.</p>
            <p>Youâ€™ll be redirected to create another in 5 seconds.</p>
            <script>
                setTimeout(function() {{
                    window.location.href = "/download?file={filename}";
                }}, 1000);
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)
    except Exception as e:
        print(f"PDF generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate content pack.")

@router.get("/download")
async def download(file: str):
    path = f"./{file}"
    if os.path.exists(path):
        return FileResponse(path, media_type='application/pdf', filename=file)
    else:
        raise HTTPException(status_code=404, detail="File not found.")
