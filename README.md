# Marketing Content Pack API

✅ **Live URL:** https://your-app-url.up.railway.app  
✅ **Tech:** Python, FastAPI, Uvicorn, Stripe, Railway

## Features
- FastAPI app with Stripe integration
- Clean API with root, health check, error handling
- Logging of requests and errors
- Deployed live on Railway

## Example Routes
- `/` → Root message
- `/healthz` → Health check
- Stripe checkout routes (see `routes/stripe_checkout.py`)

## How to run locally
```bash
uvicorn main:app --reload
```
