from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from routes import stripe_checkout
import logging

app = FastAPI()
app.include_router(stripe_checkout.router)

# Setup logging
logging.basicConfig(level=logging.INFO)

@app.get("/")
async def root():
    return {"message": "✅ Marketing Content Pack API is running!"}

@app.get("/healthz")
async def healthcheck():
    return {"status": "ok"}

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "An unexpected error occurred. Please try again later."}
    )

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logging.info(f"Incoming request: {request.method} {request.url}")
    response = await call_next(request)
    return response

@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    return JSONResponse(status_code=404, content={"error": "Route not found"})
