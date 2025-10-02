# premium_test.py
import sys
from pathlib import Path

# Make sure project root is importable
root = Path(__file__).resolve().parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from utils.pdf_generator import generate_pdf

payload = {
    "title": "Content365 – October Launch Kit",
    "subtitle": "Campaign-ready posts, links & QR — exported as a polished PDF",
    "blog_html": """
<p><b>Welcome!</b> This is a premium layout showcase for the Content365 PDF engine.</p>
<p>It demonstrates <i>auto-linking</i> of bare URLs like content365.xyz, 
<a href="https://content365.xyz">explicit links</a>, lists, and inline images.</p>
<ul>
  <li>Branded header + footer</li>
  <li>Clickable links in body & footer</li>
  <li>CTA card with accent border</li>
  <li>Platform banners for each caption</li>
</ul>
<p>Here’s a small inline image (logo):</p>
<p><img src="assets/logo.png"></p>
""",
    "bullets": [
        "Lead with value",
        "Keep copy scannable",
        "End with a single CTA",
    ],
    "cta_text": "Start your next campaign → https://content365.xyz",

    # Social sections (banners + captions + hashtags)
    "social": [
        {
            "name": "Instagram",
            "caption": "Launch day! New premium PDF polish is live. 🚀",
            "hashtags": ["#Content365", "#Launch", "#Marketing"],
        },
        {
            "name": "LinkedIn",
            "caption": "We’ve shipped a clean, brandable PDF exporter with QR, CTA, and clickable links.",
            "hashtags": ["#Python", "#FastAPI", "#ReportLab"],
        },
        {
            "name": "Twitter",
            "caption": "Premium PDF layout: header, footer, CTA, QR. Try it: content365.xyz",
            "hashtags": ["#BuildInPublic", "#DevTools"],
        },
    ],

    # QR + watermark + footer
    "qr_url": "https://content365.xyz",
    "watermark_text": "PREVIEW",
    "footer": "© 2025 Content365 · content365.xyz",

    # Brand (colors + logo). A logo is in assets/logo.png already.
    "brand": {
        "brand_name": "Content365",
        "website": "content365.xyz",
        "logo_path": "assets/logo.png",
        "logo_max_h": 24,
        "primary_color": "#0B6BF2",  # header rule + accent blue
        "accent_color":  "#111827",  # CTA border dark
    },
}

out = Path("generated_pdfs") / "premium_showcase.pdf"
out.parent.mkdir(exist_ok=True)
print("Wrote:", generate_pdf(payload, str(out)))
