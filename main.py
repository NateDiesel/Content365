from flask import Flask, render_template, request, send_file, redirect, url_for
from utils.pdf_generator import generate_dynamic_pdf
from dotenv import load_dotenv
import os
import uuid
import stripe
from email.message import EmailMessage
import smtplib

load_dotenv()

app = Flask(__name__)

# Stripe + SendGrid config
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
APP_URL = os.getenv("APP_URL", "http://localhost:8001")
ENABLE_PAYWALL = os.getenv("ENABLE_PAYWALL", "false").lower() == "true"
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
SENDGRID_SENDER = os.getenv("SENDGRID_SENDER", "noreply@content365.ai")

# Ensure folder exists for generated PDFs
OUTPUT_FOLDER = "generated_pdfs"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/form", methods=["GET", "POST"])
def form():
    if request.method == "POST":
        # Extract form inputs
        topic = request.form.get("topic")
        audience = request.form.get("audience")
        tone = request.form.get("tone")
        hashtags = request.form.get("hashtags", "")
        notes = request.form.get("notes", "")
        email = request.form.get("email")

        if ENABLE_PAYWALL:
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price": STRIPE_PRICE_ID,
                    "quantity": 1
                }],
                mode="payment",
                success_url=f"{APP_URL}/success?topic={topic}&audience={audience}&tone={tone}&hashtags={hashtags}&notes={notes}&email={email}",
                cancel_url=f"{APP_URL}/form"
            )
            return redirect(session.url, code=303)

        # Skip Stripe: go directly to success route
        return redirect(url_for("success", topic=topic, audience=audience, tone=tone, hashtags=hashtags, notes=notes, email=email))

    return render_template("form.html")

@app.route("/success")
def success():
    # Regenerate PDF after Stripe payment or direct access
    topic = request.args.get("topic")
    audience = request.args.get("audience")
    tone = request.args.get("tone")
    hashtags = request.args.get("hashtags", "")
    notes = request.args.get("notes", "")
    email = request.args.get("email")

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

    # Try sending email if provided
    try:
        if email:
            msg = EmailMessage()
            msg["Subject"] = "Your Content365 Pack"
            msg["From"] = SENDGRID_SENDER
            msg["To"] = email
            msg.set_content("Thanks for using Content365! Your content pack is attached.")

            with open(filepath, "rb") as f:
                msg.add_attachment(f.read(), maintype="application", subtype="pdf", filename=filename)

            with smtplib.SMTP("smtp.sendgrid.net", 587) as s:
                s.starttls()
                s.login("apikey", SENDGRID_API_KEY)
                s.send_message(msg)
    except Exception as e:
        print(f"Email delivery failed: {e}")

    return render_template("success.html", download_url=f"/{filepath}")

if __name__ == "__main__":
    app.run(debug=True)
