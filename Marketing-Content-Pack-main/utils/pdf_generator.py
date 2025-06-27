import openai
from fpdf import FPDF
import os

# Configure Together.ai credentials
openai.api_key = os.getenv("TOGETHER_API_KEY")
openai.api_base = "https://api.together.xyz/v1"

def call_gpt(prompt, max_tokens=300):
    response = openai.ChatCompletion.create(
        model="mistralai/Mistral-7B-Instruct-v0.1",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=max_tokens
    )
    return response.choices[0].message["content"].strip()

def generate_dynamic_pdf(topic="digital marketing"):
    print(f"Using Together.ai to generate content for: {topic}")

    blog_post = call_gpt(f"Write a 300-word blog post about {topic}.")
    captions = call_gpt(f"Write 3 engaging social media captions about {topic}.")
    lead_magnet = call_gpt(f"Suggest a compelling lead magnet idea for {topic}.")
    keywords = call_gpt(f"List 5 SEO keywords for {topic}, comma separated.")

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

    path = "./content_pack.pdf"
    pdf.output(path)
    return path
