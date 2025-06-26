from fastapi import FastAPI
from routes import stripe_checkout

app = FastAPI()
app.include_router(stripe_checkout.router)
