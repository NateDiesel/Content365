from fastapi import APIRouter, Request, HTTPException
from utils.pdf_generator import generate_pdf
from utils.together_ai import generate_content

router = APIRouter()

@router.get("/success")
async def success(request: Request):
    print("➡️ /success route invoked")
    topic = request.query_params.get("topic", "digital marketing")
    print(f"🔍 Generating content for topic: {topic}")

    content = generate_content(topic)

    if not content:
        print("❌ Together.ai returned no content — aborting PDF generation")
        raise HTTPException(status_code=500, detail="Failed to generate content pack.")

    try:
        pdf_bytes = generate_pdf(content)
        print("✅ PDF generated successfully")
        return {"detail": "Here is your PDF!"}
    except Exception as e:
        print("❌ PDF generation failed:", str(e))
        raise HTTPException(status_code=500, detail="Failed to generate content pack.")
