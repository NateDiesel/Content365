# Content365 — Updates Pack (2025-09-06)

This pack patches your **existing Content365-fixed** folder with:
- Working **multi-select social platform pills** (+ Select All)
- **B2B/B2C toggle** and **Post Style** selector (used in prompt)
- **UTF-8 + DejaVuSans** for full emoji support in the PDF (no mojibake)
- **Platform icon headers as emojis** in PDF (📸 Instagram, 🎬 TikTok, 💼 LinkedIn, 🐦 X/Twitter, 📘 Facebook)
- Cleaner PDF spacing, headers, and hashtag blocks
- Footer spacing polish
- `main.py` wiring for all form fields + robust GPT fallback (no regressions)
- Non-breaking: Stripe and email delivery stay optional and guarded

## How to apply
1) **Back up** your current folder: `Content365-fixed-BACKUP/`
2) Extract this ZIP **into your existing `Content365-fixed/`**, allowing it to **overwrite** files.
3) Ensure fonts exist:
   - This pack expects `static/fonts/DejaVuSans.ttf`.
   - If you don't have it, copy it into `static/fonts/` (or use the included one in this ZIP).
4) Install deps (if needed):
   ```bash
   pip install reportlab fastapi uvicorn python-dotenv stripe
   ```
5) Run locally:
   ```bash
   uvicorn main:app --reload --port 8000
   ```
6) Test `/form` → generate → verify emojis/icons in PDF.

## Notes
- We use emojis as **platform logos** in the PDF to avoid image path issues and ensure reliability across environments.
- If you insist on raster/SVG logos later, we can add small PNGs and draw them in ReportLab (requires file paths).

## Files included
- `templates/form.html` (UI + pills + tooltips; minimal CSS hooks)
- `static/css/style.css` (pills, hover states, footer polish)
- `static/js/form.js` (pills logic including Select All)
- `utils/pdf_generator.py` (emoji-safe fonts, clean layout, platform headers)
- `main.py` (wires new fields, guards optional deps, preserves fallback)
- `static/fonts/DejaVuSans.ttf` (emoji-capable font)

— Generated: 2025-09-07 02:26:47.336781
