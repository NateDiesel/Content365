import os
from dotenv import load_dotenv
load_dotenv()
print("OPENROUTER_API_KEY present?", bool(os.getenv("OPENROUTER_API_KEY")))
print("OPENROUTER_MODEL:", os.getenv("OPENROUTER_MODEL"))
print("LLM_MODEL:", os.getenv("LLM_MODEL"))
