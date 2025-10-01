import sys
from pathlib import Path
root = Path(__file__).resolve().parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from utils.pdf_generator import generate_pdf

p = {
  "blog": {
    "headline": "Sanity Check",
    "intro": "Hello from Content365.",
    "body": ["This is a quick smoke test paragraph."],
    "bullets": ["One", "Two", "Three"],
    "cta": "Grab more tools at content365.xyz"
  },
  "captions": {"Instagram": {"text": "Test caption #hello"}, "LinkedIn": {"text": "Another one"}},
  "hashtags": {"Instagram": ["#Hello", "#World"], "LinkedIn": ["#Test"]}
}

out = Path("generated_pdfs")/"smoke_fixed.pdf"
out.parent.mkdir(exist_ok=True)
print("Wrote:", generate_pdf(p, str(out)))
