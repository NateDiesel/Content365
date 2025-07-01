from fpdf import FPDF
from fpdf.enums import XPos, YPos
import os
import uuid
import together
from dotenv import load_dotenv
from datetime import datetime
import traceback

load_dotenv()

LOGO_PATH = "assets/logo.png"
FONT_REGULAR = "fonts/DejaVuSans.ttf"
FONT_BOLD = "fonts/DejaVuSans-Bold.ttf"

class PDF(FPDF):
    def header(self):
        if os.path.exists(LOGO_PATH):
            self.image(LOGO_PATH, x=10, y=8, w=30)
            self.ln(20)
        self.set_font("DejaVu", "B", 18)
        self.cell(0, 12, "Content365 Marketing Pack", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        self.set_font("DejaVu", "", 11)
        self.cell(0, 10, datetime.now().strftime("Generated on %B %d, %Y"), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        self.ln(5)
        self.set_draw_color(160, 160, 160)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(10)

def call_together(prompt, max_tokens=300):
    print(f"🔍 Prompt: {prompt[:60]}...")
    try:
        response = together.Complete.create(
            prompt=prompt,
            model="mistralai/Mixtral-8x7B-Instruct-v0.1",
            max_tokens=max_tokens,
            temperature=0.7,
        )
        return response.get('choices', [{}])[0].get('text', '').strip() or "[Empty response]"
    except Exception as e:
        print("❌ Together.ai error:", e)
        return "[Error generating content]"

def generate_dynamic_pdf(topic, tone="", audience="", notes="", custom_hashtags="", output_path="generated_pdfs/output.pdf"):
    print(f"🧠 Generating Content365 pack for topic: {topic}")

    if not os.getenv("TOGETHER_API_KEY"):
        print("❌ TOGETHER_API_KEY is missing.")
        return None

    if not os.path.exists(FONT_REGULAR) or not os.path.exists(FONT_BOLD):
        print("❌ Font files not found.")
        return None

    # Prompts
    blog_prompt = f"Write a 500-word {tone.lower()} marketing article about {topic}." if tone else f"Write a 500-word blog post about {topic}."
    blog_post = call_together(blog_prompt)

    caption_prompt = f"""
    Generate optimized social media content for "{topic}" in a {tone.lower()} tone.
    Write 1 caption each for:
    - Instagram
    - LinkedIn
    - TikTok
    - Twitter/X
    - Facebook
    Include platform-specific hashtags and formatting.
    """.strip()
    captions = call_together(caption_prompt)

    lead_magnet = call_together(f"Suggest a compelling lead magnet idea for {topic}.")
    keywords = call_together(f"List 5 SEO keywords for {topic}, comma separated.")

    # Combine hashtags
    if custom_hashtags.strip():
        hashtags_block = f"\n\n🧷 User-requested hashtags:\n{custom_hashtags}"
    else:
        hashtags_block = ""

    # PDF assembly
    try:
        pdf = PDF()
        pdf.add_font("DejaVu", "", FONT_REGULAR)
        pdf.add_font("DejaVu", "B", FONT_BOLD)
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        pdf.set_font("DejaVu", "B", 14)
        pdf.cell(0, 10, "📌 Summary", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("DejaVu", "", 12)
        pdf.multi_cell(0, 8, f"Topic: {topic}\nAudience: {audience}\nTone: {tone}\nNotes: {notes}")
        pdf.ln(8)

        content_blocks = [
            ("📄 Long-form Blog Article", blog_post),
            ("💬 Social Media Captions (All Platforms)", captions + hashtags_block),
            ("🎁 Lead Magnet Ideas", lead_magnet),
            ("🔍 SEO Keywords", keywords),
        ]

        for title, content in content_blocks:
            pdf.set_font("DejaVu", "B", 14)
            pdf.cell(0, 10, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("DejaVu", "", 12)
            pdf.multi_cell(0, 8, content)
            pdf.ln(6)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        pdf.output(output_path)
        print(f"✅ Content365 PDF saved: {output_path}")
        return output_path

    except Exception as e:
        print("❌ PDF generation error:", e)
        traceback.print_exc()
        return None
