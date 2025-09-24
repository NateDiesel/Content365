# 📦 Content365 – AI Marketing Content Pack Generator

**Live Site:** [https://content365.xyz](https://content365.xyz)  
**Demo:** Available on request • **License:** MIT  
**Status:** ✅ Production-ready & monetized

---

## ✨ Features
- AI-generated **blog post + social captions + lead magnet + SEO** in one go
- Platform-specific **hashtags** (LinkedIn, Instagram, TikTok, X, Facebook) with smart trimming
- **Preview page:** post-generation embedded PDF preview + download
- GPT fallback logic (no crash if the model stumbles)
- Stripe paywall + email delivery (optional; can be disabled locally)
- Clean, grouped PDF output with branding
- Emoji-safe PDFs (uses DejaVu; strips unsupported emoji if needed)
- Mobile-optimized form UX

---

## ⚙️ Tech Stack
- 🧠 LLM: OpenRouter (e.g., Mixtral-8x7B) + local fallback
- ⚡ Backend: FastAPI (+ Stripe, SendGrid optional)
- 🧾 PDF: ReportLab (emoji/unicode friendly)
- 🖼 Templates: Jinja2
- 🚀 Deploy: Docker + Railway
- 📁 Key files: `utils/pdf_generator.py`, `utils/prompt_loader.py`, `main.py`

---

## 🧪 Running Locally
- **Preview flow:** After generation the app redirects to `/result` with an embedded PDF and a Download button.
- **Generated files:** Saved under `/generated/` and served statically.

**Minimal .env for local dev**
