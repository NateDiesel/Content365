# 📦 Content365 – AI Marketing Content Pack Generator

<<<<<<< HEAD
**Live Site:** [https://content365.xyz](https://content365.xyz)  
=======
**Live Site:** https://content365.xyz  
>>>>>>> 2ed0c2a (chore: wire Gemini provider + provider_router)
**Demo:** Available on request • **License:** MIT  
**Status:** ✅ Production-ready & monetized

---

## ✨ Features

<<<<<<< HEAD
- AI-generated blog post + social captions + lead magnet + SEO
- Platform-specific hashtags (LinkedIn, IG, TikTok, etc.)
- GPT fallback logic (no crash if model fails)
- Stripe paywall and email delivery
- Clean, grouped PDF output with branding
- Mobile-optimized form UX + emoji support

---

## 📸 Screenshots

> ![Form UI](static/demo-form.png)  
> ![PDF Output](static/demo-pdf-preview.png)
=======
- AI-generated **blog post + social captions + SEO** in one go
- Platform-specific **hashtags** (LinkedIn, IG, TikTok, etc.)
- **Dual-engine PDF** output with branding  
  - 🖨️ **Pro**: ReportLab + DejaVu fonts (headers/footers, page X of Y)  
  - 🧰 **Fallback**: zero-deps stdlib writer (grayscale, no emoji)
- **Emoji-safe** PDFs (unsupported emoji are auto-stripped to avoid tofu)
- GPT fallback logic (no crash if the model stumbles)
- Stripe paywall + email delivery (optional)
- Mobile-optimized form UX
>>>>>>> 2ed0c2a (chore: wire Gemini provider + provider_router)

---

## ⚙️ Tech Stack

<<<<<<< HEAD
- 🧠 LLM: OpenRouter (Mixtral-8x7B) + Local fallback
- ⚡ Backend: FastAPI + Stripe + SendGrid
- 🧾 PDF: ReportLab (with emoji/unicode support)
- 🚀 Deploy: Docker + Railway
- 📁 Assets: `pdf_generator.py`, `prompt_loader.py`, `openrouter.py`

---

## 🧪 Running Locally
=======
- **Backend:** FastAPI
- **PDF:** ReportLab (Pro) + stdlib fallback
- **Templates:** Jinja2
- **Runtime:** Uvicorn
- **Tests:** Pytest

Key files:
- `utils/pdf_generator.py` — dual-engine PDF generator (no `micropip`)
- `main.py` — normalizes AI output → PDF schema, adds `/health/pdf`
- `tests/test_pdf_generator.py` — PDF smoke + edge cases

---

## 🧪 Quick Start (Local)
>>>>>>> 2ed0c2a (chore: wire Gemini provider + provider_router)

```bash
git clone https://github.com/NateDiesel/Content365.git
cd Content365
<<<<<<< HEAD
python -m venv venv && source venv/bin/activate  # or .\venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn main:app --reload
=======

# Create & activate a virtual env
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows (PowerShell):
# .\.venv\Scripts\Activate.ps1

# Install runtime deps
pip install -r requirements.txt

# Copy and edit environment
cp .env.template .env          # macOS/Linux
# Windows:
# copy .env.template .env

# Run the dev server
python -m uvicorn main:app --reload --port 8000
>>>>>>> 2ed0c2a (chore: wire Gemini provider + provider_router)
