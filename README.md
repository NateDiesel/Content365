# 📦 Content365 – AI Marketing Content Pack Generator

<<<<<<< HEAD
<<<<<<< HEAD
**Live Site:** [https://content365.xyz](https://content365.xyz)  
=======
**Live Site:** https://content365.xyz  
>>>>>>> 2ed0c2a (chore: wire Gemini provider + provider_router)
=======
**Live Site:** [https://content365.xyz](https://content365.xyz)  
**Live Site:** https://content365.xyz  
>>>>>>> 5a37524 (Initial commit of Content365 project)
**Demo:** Available on request • **License:** MIT  
**Status:** ✅ Production-ready & monetized

---

## ✨ Features

<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> 5a37524 (Initial commit of Content365 project)
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
<<<<<<< HEAD
=======
=======
>>>>>>> 5a37524 (Initial commit of Content365 project)
- AI-generated **blog post + social captions + SEO** in one go
- Platform-specific **hashtags** (LinkedIn, IG, TikTok, etc.)
- **Dual-engine PDF** output with branding  
  - 🖨️ **Pro**: ReportLab + DejaVu fonts (headers/footers, page X of Y)  
  - 🧰 **Fallback**: zero-deps stdlib writer (grayscale, no emoji)
- **Emoji-safe** PDFs (unsupported emoji are auto-stripped to avoid tofu)
- GPT fallback logic (no crash if the model stumbles)
- Stripe paywall + email delivery (optional)
- Mobile-optimized form UX
<<<<<<< HEAD
>>>>>>> 2ed0c2a (chore: wire Gemini provider + provider_router)
=======
>>>>>>> 5a37524 (Initial commit of Content365 project)

---

## ⚙️ Tech Stack

<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> 5a37524 (Initial commit of Content365 project)
- 🧠 LLM: OpenRouter (Mixtral-8x7B) + Local fallback
- ⚡ Backend: FastAPI + Stripe + SendGrid
- 🧾 PDF: ReportLab (with emoji/unicode support)
- 🚀 Deploy: Docker + Railway
- 📁 Assets: `pdf_generator.py`, `prompt_loader.py`, `openrouter.py`

---

## 🧪 Running Locally
<<<<<<< HEAD
=======
=======
>>>>>>> 5a37524 (Initial commit of Content365 project)
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
<<<<<<< HEAD
>>>>>>> 2ed0c2a (chore: wire Gemini provider + provider_router)
=======
>>>>>>> 5a37524 (Initial commit of Content365 project)

```bash
git clone https://github.com/NateDiesel/Content365.git
cd Content365
<<<<<<< HEAD
<<<<<<< HEAD
python -m venv venv && source venv/bin/activate  # or .\venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn main:app --reload
=======
=======
python -m venv venv && source venv/bin/activate  # or .\venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn main:app --reload
>>>>>>> 5a37524 (Initial commit of Content365 project)

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
<<<<<<< HEAD
>>>>>>> 2ed0c2a (chore: wire Gemini provider + provider_router)
=======
>>>>>>> 5a37524 (Initial commit of Content365 project)
