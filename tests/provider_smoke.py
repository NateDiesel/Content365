import os, asyncio
from dotenv import load_dotenv
load_dotenv()
print("AI_PROVIDER =", os.getenv("AI_PROVIDER"))
from Content365.utils.gemini import generate_text

async def main():
    out = await generate_text("Reply only with the word READY")
    print("AI SAYS:", out)

asyncio.run(main())
