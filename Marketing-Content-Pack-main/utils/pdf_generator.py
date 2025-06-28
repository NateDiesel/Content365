from fpdf import FPDF
import os
import uuid
import together

together.api_key = os.getenv("TOGETHER_API_KEY")

def call_together(prompt, max_tokens=300):
    try:
        response = together.Complete.create(
            prompt=prompt,
            model="mistralai/Mixtral-8x7B-Instruct-v0.1",
            max_tokens=max_tokens,
            temperature=0.7,
        )
        return response['output']['choices'][0]['text'].strip()
    except Exception as e:
        print("❌ Together.ai error:", str(e))
        return "Error generating content."

def generate_dynamic_pdf(topic="digital marketing"):
    print(f"Using Together.ai to generate content for: {topic}")

    blog_post = call_together(f"Write a 300-word blog post about {topic}.")
    captions = call_together(f"Write 3 engaging social media captions about {topic}.")
    lead_magnet = call_together(f"Suggest a compelling lead magnet idea for {topic}.")
    keywords = call_together(f"List 5 SEO keywords for {topic}, comma separated.")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt="AI Content Pack Pro", ln=True, align="C")
    pdf.ln(10)

    pdf.multi_cell(0, 10, f"Blog Post Draft:\n{blog_post}")
    pdf.ln(5)
    pdf.multi_cell(0, 10, f"Social Media Captions:\n{captions}")
    pdf.ln(5)
    pdf.multi_cell(0, 10, f"Lead Magnet Idea:\n{lead_magnet}")
    pdf.ln(5)
    pdf.multi_cell(0, 10, f"SEO Keywords:\n{keywords}")

    filename = f"./content_pack_{uuid.uuid4().hex}.pdf"
    pdf.output(filename)
    return filename
