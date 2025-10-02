# legacy_test.py
import sys
from pathlib import Path

# Ensure project root is importable
root = Path(__file__).resolve().parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from utils.pdf_generator import generate_pdf

# ---- Legacy-shaped payload (no blog_html / social list) ----
payload = {
    "blog": {
        "headline": "Legacy Shape Smoke",
        "intro": "This uses the old payload structure and should still render with the premium layout.",
        "body": [
            "It goes through _adapt_payload_legacy() behind the scenes.",
            "You should see branded header/footer, clean paragraphs, and bullets.",
        ],
        "bullets": ["One", "Two", "Three"],
        "cta": "Learn more at content365.xyz",
    },
    # Old style captions/hashtags maps
    "captions": {
        "Instagram": {"text": "Shipping polish ✨"},
        "LinkedIn": {"text": "Adapter path verified. Premium renderer engaged."},
    },
    "hashtags": {
        "Instagram": ["#Content365", "#Launch"],
        "LinkedIn": ["#Python", "#ReportLab"],
    },
    # Optional footer (if omitted, adapter builds a default)
    "footer": "© 2025 Content365 · content365.xyz",
    # (We intentionally skip qr_url/watermark_text here; legacy adapter keeps core fields.)
}

# You can pass brand overrides either here:
brand = {
    "brand_name": "Content365",
    "website": "content365.xyz",
    "logo_path": "assets/logo.png",  # ensure this file exists (it does in your repo)
    "logo_max_h": 24,
    "primary_color": "#0B6BF2",
    "accent_color": "#111827",
}

# Or you can omit brand entirely to verify defaults:
# brand = None

out = Path("generated_pdfs") / "legacy_adapter_test.pdf"
out.parent.mkdir(exist_ok=True)
print("Wrote:", generate_pdf(payload, str(out), brand))
