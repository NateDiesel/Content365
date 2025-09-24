# 🤝 Contributing to Content365

Thanks for your interest in contributing to Content365! Here’s how to get started.

## 🔧 Local Setup

```bash
git clone https://github.com/NateDiesel/Content365.git
cd Content365
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## 🧪 Testing

- Test PDF generation with sample form submission
- Stripe webhook can be tested via test mode or CLI
- Email delivery (SendGrid) is optional — check logs if off

## 📦 Project Overview

- `main.py` - FastAPI entrypoint  
- `routes/` - Stripe-related routing  
- `utils/` - PDF/email helpers  
- `templates/` - HTML UI  
- `static/` - Output files

## 🙌 Ways to Contribute

- Improve hashtag logic
- Enhance platform styling
- Suggest new PDF formats or content types
- Refactor or optimize GPT prompts

PRs welcome!
