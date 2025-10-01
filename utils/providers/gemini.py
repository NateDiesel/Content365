# utils/providers/gemini.py
import os, json
from google import genai
from google.genai import types

_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Force the model to return the exact JSON shape we need for the PDF
RESPONSE_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "blog": types.Schema(
            type=types.Type.OBJECT,
            properties={
                "title":   types.Schema(type=types.Type.STRING),
                "intro":   types.Schema(type=types.Type.STRING),
                "bullets": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
                "cta":     types.Schema(type=types.Type.STRING),
            },
            required=["title", "intro"]
        ),
        "platforms": types.Schema(type=types.Type.OBJECT)
    },
    required=["blog", "platforms"]
)

def call_gemini_flash25(
    prompt_text: str,
    model: str = "gemini-2.5-flash",
    thinking_budget: int = 0
) -> dict:
    cfg = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=RESPONSE_SCHEMA,
        thinking_config=types.ThinkingConfig(thinking_budget=thinking_budget),
    )
    resp = _client.models.generate_content(model=model, contents=prompt_text, config=cfg)
    return json.loads(resp.text)  # the SDK returns JSON text when you set response_mime_type
