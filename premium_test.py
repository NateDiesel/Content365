import sys, pathlib
root = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(root))
from pathlib import Path
from utils.pdf_generator import generate_pdf

payload = {
  "blog": {
    "headline": "October Sprint Update",
    "intro": "Shipping polish for the Content365 PDF engine.",
    "body": ["Premium header/footer, better bullets, auto-linking, and CTA card."],
    "bullets": ["Clean header with brand + site", "Clickable links", "Robust images"],
    "cta": "See the latest at content365.xyz"
  },
  "captions": {
    "Instagram": {"text": "We shipped polish "},
    "LinkedIn": {"text": "Polished PDF engine ready."}
  },
  "hashtags": {"Instagram": ["#Content365", "#Launch"], "LinkedIn": ["#Python", "#ReportLab"]}
}

brand = {
  "brand_name": "Content365",
  "website": "content365.xyz",
  "logo_path": "assets/logo.png",            # put a real logo file here
  "primary_color": "#0B6BF2",
  "accent_color": "#111827"
}

out = Path("generated_pdfs")/"premium_test.pdf"
out.parent.mkdir(exist_ok=True)
print("Wrote:", generate_pdf(payload, str(out), brand))
