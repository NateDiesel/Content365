from fpdf import FPDF
import os
import uuid
import together
from dotenv import load_dotenv
import sys
from datetime import datetime

# Toggle this to True if you want to enable email sending
SEND_EMAIL = False
if SEND_EMAIL:
    from email_sender import send_pdf_email

load_dotenv()

LOGO_PATH = "assets/logo.png"
FONT_REGULAR = "fonts/DejaVuSans.ttf"         # ✅ corrected from fonts/ttf/
FONT_BOLD = "fonts/DejaVuSans-Bold.ttf"       # ✅ corrected from fonts/ttf/

class PDF(FPDF):
    def header(self):
        if os.path.exists(LOGO_PATH):
            self.image(LOGO_PATH, x=10, y=8, w=30)
            self.ln(25)
        self.set_font("DejaVu", "B", 16)
        self.cell(0, 10, "AI Content Pack Pro", ln=True, align="C")
        self.set_font("DejaVu", "", 11)
        self.cell(0, 10, datetime.now().strftime("Generated on %B %d, %Y"), ln=True, align="C")
        self.ln(5)
        self.set_draw_color(180, 180, 180)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(10)

def call_together(prompt, max_tokens=300):
    print(f"🔍 Calling Together.ai with prompt: {prompt[:60]}...")
    try:
        response = together.Complete.create(
            prompt=prompt,
            model="mistralai/Mixtral-8x7B-Instruct-v0.1",
            max_tokens=max_tokens,
            temperature=0.7,
        )
        result = response.get('choices', [{}])[0].get('text', '').strip()
        print("✅ Response received.")
        return result if result else "[Empty response]"
    except Exception as e:
        print("❌ Together.ai error:", str(e))
        return "[Error generating content]"

def generate_dynamic_pdf(topic, recipient_email=None):
    print(f"📝 Starting PDF generation for topic: {topic}")

    if not os.getenv("TOGETHER_API_KEY"):
        print("❌ TOGETHER_API_KEY is missing.")
        return None

    if not os.path.exists(FONT_REGULAR) or not os.path.exists(FONT_BOLD):
        print("❌ Font files not found. Expected at:")
        print(f"   - {FONT_REGULAR}")
        print(f"   - {FONT_BOLD}")
        return None

    blog_post = call_together(f"Write a 300-word blog post about {topic}.")
    captions = call_together(f"Write 3 engaging social media captions about {topic}.")
    lead_magnet = call_together(f"Suggest a compelling lead magnet idea for {topic}.")
    keywords = call_together(f"List 5 SEO keywords for {topic}, comma separated.")

    print("📄 Building PDF...")

    try:
        pdf = PDF()
        pdf.add_font("DejaVu", "", FONT_REGULAR)
        pdf.add_font("DejaVu", "B", FONT_BOLD)
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("DejaVu", "", 12)

        pdf.set_font("DejaVu", "B", 14)
        pdf.cell(0, 10, "📄 Blog Post", ln=True)
        pdf.set_font("DejaVu", "", 12)
        pdf.multi_cell(0, 8, blog_post)
        pdf.ln(5)

        pdf.set_font("DejaVu", "B", 14)
        pdf.cell(0, 10, "💬 Social Media Captions", ln=True)
        pdf.set_font("DejaVu", "", 12)
        pdf.multi_cell(0, 8, captions)
        pdf.ln(5)

        pdf.set_font("DejaVu", "B", 14)
        pdf.cell(0, 10, "🎁 Lead Magnet Idea", ln=True)
        pdf.set_font("DejaVu", "", 12)
        pdf.multi_cell(0, 8, lead_magnet)
        pdf.ln(5)

        pdf.set_font("DejaVu", "B", 14)
        pdf.cell(0, 10, "🔍 SEO Keywords", ln=True)
        pdf.set_font("DejaVu", "", 12)
        pdf.multi_cell(0, 8, keywords)
        pdf.ln(10)

        pdf.set_text_color(0, 102, 204)
        pdf.set_font("DejaVu", "", 11)
        pdf.cell(0, 10, "Create your own content pack at: ResumePilot.ai", ln=True, link="https://resumepilot.ai")

        filename = f"./content_pack_{uuid.uuid4().hex}.pdf"
        with open(filename, "wb") as f:
            pdf.output(f)

        print(f"✅ PDF generated: {filename}")

        if SEND_EMAIL and recipient_email:
            send_pdf_email(recipient_email, filename, topic)

        return filename

    except Exception as e:
        print("❌ PDF generation error:", str(e))
        return None

if __name__ == "__main__":
    topic = sys.argv[1] if len(sys.argv) > 1 else "email marketing for realtors"
    email = sys.argv[2] if len(sys.argv) > 2 else None
    result = generate_dynamic_pdf(topic, email)
    print("✅ Done! PDF saved at:", result)
