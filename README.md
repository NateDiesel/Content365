# 🚀 Content365 – AI-Powered Content Pack Generator

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Click%20Here-brightgreen)](https://content365.xyz)
[![Built with FastAPI](https://img.shields.io/badge/Built%20With-FastAPI-blue)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Content365 is your all-in-one AI marketing assistant that instantly creates downloadable content packs:

### ✨ What You’ll Get
- ✅ AI-written blog post
- ✅ Social media captions (Instagram, LinkedIn, TikTok, etc.)
- ✅ Lead magnet content ideas
- ✅ SEO keyword suggestions
- ✅ Custom PDF branding + emoji support
- ✅ Optional email delivery
- ✅ Stripe-powered payment access

---

## 🚀 Live Demo
🔗 [https://content365.xyz](https://content365.xyz)

---

## 🧠 Powered By

| Feature        | Tech Stack                  |
|----------------|-----------------------------|
| Backend        | Python, FastAPI             |
| PDF Generator  | ReportLab, DejaVu fonts     |
| LLM            | OpenRouter (Mixtral-8x7B)   |
| Payments       | Stripe Checkout             |
| Email Delivery | SendGrid API                |
| Deployment     | Railway + Docker            |

---

## ⚙️ How to Run Locally

```bash
git clone https://github.com/NateDiesel/Content365.git
cd Content365
pip install -r requirements.txt

# Add your .env file with:
# STRIPE_SECRET_KEY=
# SENDGRID_API_KEY=
# OPENROUTER_API_KEY=

uvicorn main:app --reload --port 8000
```

Then visit `http://localhost:8000` to use the app locally.

---

## 📦 Sample Output

A sample PDF is available in [`static/sample-output.pdf`](static/sample-output.pdf). It includes:
- Blog post with headings
- Branded footer + emojis
- Captions and lead magnet suggestions

---

## 🧑‍💼 Perfect For

- Solo founders & freelancers
- Agencies & marketing teams
- SEO professionals & course creators

---

## 🧾 License

MIT — free to use, fork, and build upon.

---

Built by [@NateDiesel](https://github.com/NateDiesel) · Powered by Content365.ai