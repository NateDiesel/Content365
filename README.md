# 🚀 Content365 - AI-Powered Content Pack Generator

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Click%20Here-brightgreen)](https://content365.xyz)
[![Built with FastAPI](https://img.shields.io/badge/Built%20With-FastAPI-blue)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Content365** is your all-in-one AI marketing assistant that instantly creates platform-optimized, downloadable content packs — designed to grow your brand and save you hours.

---

## ✨ Features

- 🧠 AI-written blog post tailored to your niche
- 💬 Platform-specific social captions (Instagram, LinkedIn, TikTok, Twitter, Facebook)
- 🔗 Smart hashtags generated per platform best practices
- 🧲 Lead magnet suggestions for list-building
- 🧾 Branded, emoji-compatible PDF output (Unicode-safe)
- 💸 Stripe-powered checkout + fallback flow
- 📩 Optional email delivery of your content pack
- 📱 Mobile-friendly, SEO-enhanced UI

---

## 🖼️ Sample Output

You can preview a generated pack here:

📄 [`/static/sample-output.pdf`](https://content365.xyz/static/sample-output.pdf)  
*Includes blog post, captions, hashtags, lead magnet, and brand footer*

---

## 🔧 Tech Stack

- ⚙️ **Backend**: FastAPI + OpenRouter (Mixtral-8x7B)
- 📄 **PDF Generator**: ReportLab (Unicode-safe, emoji support)
- 💰 **Payments**: Stripe API + webhook success handling
- 📤 **Email Delivery**: SendGrid (optional)
- 🖼️ **Frontend**: HTML/CSS with mobile-responsive layout

---

## 🛠 Setup Instructions

```bash
# Clone the repo
git clone https://github.com/NateDiesel/Content365.git
cd Content365

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows use venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app
uvicorn main:app --reload --port 8000
```

---

## 🔐 Environment Variables

Create a `.env` file (based on `.env.example`) with:

```
OPENROUTER_API_KEY=your_openrouter_key
STRIPE_SECRET_KEY=your_stripe_key
STRIPE_WEBHOOK_SECRET=your_webhook_key
SENDGRID_API_KEY=your_sendgrid_key
EMAIL_SENDER=your_verified_sender@example.com
```

---

## 🧠 Project Structure

```
📁 routes/             # Stripe + webhook handling
📁 utils/              # PDF & email generation logic
📁 static/             # Sample output, branding
📁 templates/          # HTML templates (form, success, preview)
📄 main.py             # FastAPI entrypoint
📄 Dockerfile          # Deployment config
📄 .env.example        # Sample environment file
```

---

## 👀 Credits & Attribution

Built with ❤️ by [Nathan Bentley](https://github.com/NateDiesel)  
Powered by OpenRouter, ReportLab, Stripe, and SendGrid.

---

## 🪙 License

MIT - Free for personal and commercial use with attribution.
