# 📦 Content365 – AI Marketing Content Pack Generator

**Live Site:** [https://content365.xyz](https://content365.xyz)  
**Demo:** Available on request • **License:** MIT  
**Status:** ✅ Production-ready & monetized

---

## ✨ Features

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

---

## ⚙️ Tech Stack

- 🧠 LLM: OpenRouter (Mixtral-8x7B) + Local fallback
- ⚡ Backend: FastAPI + Stripe + SendGrid
- 🧾 PDF: ReportLab (with emoji/unicode support)
- 🚀 Deploy: Docker + Railway
- 📁 Assets: `pdf_generator.py`, `prompt_loader.py`, `openrouter.py`

---

## 🧪 Running Locally

```bash
git clone https://github.com/NateDiesel/Content365.git
cd Content365
python -m venv venv && source venv/bin/activate  # or .\venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn main:app --reload
