import sys

port = int(os.environ.get("PORT", 8001))

from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import stripe
import os
import uuid
import re
import csv
from datetime import datetime
from utils.pdf_generator import generate_dynamic_pdf


load_dotenv()

app = FastAPI()

# Stripe config
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
PRICE_ID = os.getenv("STRIPE_PRICE_ID")
APP_URL = os.getenv("APP_URL", "http://localhost:8001").rstrip("/")

# Static files (optional)
app.mount("/static", StaticFiles(directory="static"), name="static")


def sanitize_input(text: str, max_len: int = 100) -> str:
    text = re.sub(r'[^\w\s\-.,!?@]', '', text)
    return text.strip()[:max_len]


def log_session(email, topic, tone, style, audience, filename):
    os.makedirs("logs", exist_ok=True)
    log_path = "logs/content_log.csv"
    headers = ["timestamp", "email", "topic", "tone", "style", "audience", "filename"]
    timestamp = datetime.now().isoformat()
    data = [timestamp, email, topic, tone, style, audience, filename]
    write_header = not os.path.exists(log_path)
    with open(log_path, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        if write_header:
            writer.writerow(headers)
        writer.writerow(data)


@app.get("/", response_class=HTMLResponse)
async def landing_page():
    return """
    <html>
    <head>
        <title>Buy Your AI Content Pack</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; margin-top: 60px; background: #f4f4f8; }
            input { padding: 10px; width: 300px; margin-bottom: 10px; border-radius: 5px; border: 1px solid #ccc; }
            form { background: white; padding: 30px; display: inline-block; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
            button { padding: 10px 20px; border: none; background: #007bff; color: white; font-weight: bold; border-radius: 5px; }
            h1 { color: #333; }
        </style>
    </head>
    <body>
        <form action="/buy" method="get">
            <h1>Buy Your AI Content Pack</h1>
            <input type="text" name="email" placeholder="Your email" required><br>
            <input type="text" name="topic" placeholder="Topic (e.g. LinkedIn Outreach)" required><br>
            <input type="text" name="tone" placeholder="Tone (e.g. Casual, Bold)"><br>
            <input type="text" name="style" placeholder="Style (e.g. Blog Post, Thread)"><br>
            <input type="text" name="audience" placeholder="Audience (e.g. Freelancers, VCs)"><br>
            <button type="submit">Buy Now</button>
        </form>
    </body>
    </html>
    """


@app.get("/buy")
async def buy_now(topic: str, email: str, tone: str = "", style: str = "", audience: str = ""):
    topic = sanitize_input(topic)
    tone = sanitize_input(tone)
    style = sanitize_input(style)
    audience = sanitize_input(audience)
    email = sanitize_input(email, max_len=150)

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": PRICE_ID, "quantity": 1}],
            mode="payment",
            success_url=f"{APP_URL}/success?session_id={{CHECKOUT_SESSION_ID}}&topic={topic}&tone={tone}&style={style}&audience={audience}&email={email}",
            cancel_url=f"{APP_URL}/",
        )
        return RedirectResponse(session.url, status_code=303)
    except Exception as e:
        return HTMLResponse(f"<h2>Checkout error:</h2><p>{e}</p>", status_code=500)


@app.get("/success", response_class=HTMLResponse)
async def success(topic: str, session_id: str, background_tasks: BackgroundTasks,
                  tone: str = "", style: str = "", audience: str = "", email: str = ""):
    topic = sanitize_input(topic)
    tone = sanitize_input(tone)
    style = sanitize_input(style)
    audience = sanitize_input(audience)
    email = sanitize_input(email, max_len=150)

    print(f"✅ Stripe payment successful. Generating PDF for: {topic}")
    pdf_path = generate_dynamic_pdf(topic, tone=tone, style=style, audience=audience)

    if not pdf_path or not os.path.exists(pdf_path):
        return HTMLResponse("<h2>❌ PDF generation failed. Please contact support.</h2>", status_code=500)

    filename = os.path.basename(pdf_path)
    background_tasks.add_task(os.remove, pdf_path)
    log_session(email=email, topic=topic, tone=tone, style=style, audience=audience, filename=filename)

    return f"""
    <html>
    <head><title>Success</title></head>
    <body style="font-family:sans-serif;text-align:center;margin-top:50px">
        <h2>✅ Your AI content pack is ready!</h2>
        <p><a href="/download?file={filename}" style="font-size:18px;">Download your content pack →</a></p>
        <p style="color:gray;"><i>This file will be deleted soon for security.</i></p>
    </body>
    </html>
    """


@app.get("/download")
async def download(file: str):
    file = sanitize_input(file, max_len=100)
    path = f"./{file}"
    if os.path.exists(path) and file.endswith(".pdf"):
        return FileResponse(path, media_type='application/pdf', filename=file)
    return HTMLResponse("<h2>❌ File not found or invalid request.</h2>", status_code=404)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8001))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
