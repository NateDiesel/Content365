import os
import together

def generate_content(topic: str):
    together.api_key = os.getenv("TOGETHER_API_KEY", "")
    print(f"🔐 Together API key loaded: {'YES' if together.api_key else 'NO'}")

    prompt = f"Create a content pack about: {topic}"
    print("➡️ Sending prompt to Together.ai:", prompt)

    try:
        response = together.Complete.create(
            prompt=prompt,
            model="togethercomputer/llama-2-70b-chat",
            max_tokens=512,
            temperature=0.7,
        )
        print("✅ Together.ai response received")
        text = response["output"]["choices"][0]["text"]
        print("📄 Content snippet:", text[:200].replace("\n", " "))
        return text
    except Exception as e:
        print("❌ Error calling Together.ai:", str(e))
        return None
