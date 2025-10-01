# 📦 Content365 – AI Marketing Content Pack Generator

**Live Site:** [https://content365.xyz](https://content365.xyz)   2ed0c2a (chore: wire Gemini provider + provider_router)
**Demo:** Available on request • **License:** MIT  
**Status:** ✅ Production-ready & monetized

---

## ✨ Features

- AI-generated **blog post + social captions + SEO** in one go
- Platform-specific **hashtags** (LinkedIn, IG, TikTok, etc.)
- **Dual-engine PDF** output with branding  
  - 🖨️ **Pro**: ReportLab + DejaVu fonts (headers/footers, page X of Y)  
  - 🧰 **Fallback**: zero-deps stdlib writer (grayscale, no emoji)
- **Emoji-safe** PDFs (unsupported emoji are auto-stripped to avoid tofu)
- GPT fallback logic (no crash if the model stumbles)
- Stripe paywall + email delivery (optional)
- Mobile-optimized form UX
- 🧠 LLM: OpenRouter (Mixtral-8x7B) + Local fallback
- ⚡ Backend: FastAPI + Stripe + SendGrid
- 🧾 PDF: ReportLab (with emoji/unicode support)
- 🚀 Deploy: Docker + Railway
- 📁 Assets: `pdf_generator.py`, `prompt_loader.py`, `openrouter.py`

---

## 🧪 Running Locally

