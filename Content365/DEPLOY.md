# Content365 v4.6 FINAL (clean)

## Quickstart (Windows PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -U pip wheel
pip install -r requirements.txt

# Local dev env (paywall off; LM Studio defaults):
$env:ENABLE_PAYWALL="false"
$env:APP_URL="http://127.0.0.1:8000"
$env:LLM_API_URL="http://127.0.0.1:1234/v1/chat/completions"
$env:LLM_MODEL="mistral-7b-instruct-v0.2"

# Run
python -m uvicorn main:app --reload --port 8000
```

## Notes
- DejaVu fonts must stay in `assets/fonts/` for emoji/unicode PDF output.
- Health check: `GET /__heal` -> `{"ok": true}`
- Stripe keys are optional while `ENABLE_PAYWALL=false`.
