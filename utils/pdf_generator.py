
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER
from reportlab.lib import colors
from reportlab.lib.units import inch

def generate_pdf(content_blocks, output_path):
    c = canvas.Canvas(output_path, pagesize=LETTER)
    width, height = LETTER
    y = height - inch

    def draw_section(title, lines):
        nonlocal y
        c.setFont("Helvetica-Bold", 14)
        c.drawString(inch, y, title)
        y -= 0.3 * inch
        c.setStrokeColor(colors.lightgrey)
        c.line(inch, y, width - inch, y)
        y -= 0.2 * inch
        c.setFont("Helvetica", 11)
        for line in lines:
            for sub in line.split("\n"):
                if y < inch:
                    c.showPage()
                    y = height - inch
                c.drawString(inch, y, sub.strip())
                y -= 0.22 * inch
        y -= 0.3 * inch

    if 'blog' in content_blocks:
        draw_section("📘 Blog Post", content_blocks['blog'].splitlines())
    if 'captions' in content_blocks:
        draw_section("💬 Social Captions", content_blocks['captions'].splitlines())
    if 'hashtags' in content_blocks:
        draw_section("🏷️ Hashtags", content_blocks['hashtags'].splitlines())

    # Add Premium Tips
    tips = [
        "💡 Premium Tips:",
        "• Post at peak hours for each platform (e.g. 9AM on LinkedIn, evenings for IG).",
        "• Use carousel format to break this blog into a series.",
        "• Repurpose captions into emails, tweets, or newsletter intros.",
        "• Use Canva to turn tips into branded visual quote tiles."
    ]
    draw_section("✨ Premium Tips", tips)

    # Footer
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.grey)
    c.drawRightString(width - inch, 0.6 * inch, "© 2025 Content365.xyz • contact@content365.xyz")
    c.save()
