from flask import Flask, render_template, request, send_file
from utils.pdf_generator import generate_content_pack
import os
import uuid

app = Flask(__name__)

# Ensure folder exists for generated PDFs
OUTPUT_FOLDER = "generated_pdfs"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/form", methods=["GET", "POST"])
def form():
    if request.method == "POST":
        topic = request.form.get("topic")
        audience = request.form.get("audience")
        tone = request.form.get("tone")
        platform = request.form.get("platform")
        notes = request.form.get("notes")

        filename = f"{uuid.uuid4().hex[:12]}.pdf"
        filepath = os.path.join(OUTPUT_FOLDER, filename)

        generate_content_pack(
            topic=topic,
            audience=audience,
            tone=tone,
            platform=platform,
            notes=notes,
            output_path=filepath
        )

        return send_file(filepath, as_attachment=True)

    return render_template("form.html")

if __name__ == "__main__":
    app.run(debug=True)
from flask import Flask, render_template, request, send_file
from utils.pdf_generator import generate_content_pack
import os
import uuid

app = Flask(__name__)

# Ensure folder exists for generated PDFs
OUTPUT_FOLDER = "generated_pdfs"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/form", methods=["GET", "POST"])
def form():
    if request.method == "POST":
        topic = request.form.get("topic")
        audience = request.form.get("audience")
        tone = request.form.get("tone")
        platform = request.form.get("platform")
        notes = request.form.get("notes")

        filename = f"{uuid.uuid4().hex[:12]}.pdf"
        filepath = os.path.join(OUTPUT_FOLDER, filename)

        generate_content_pack(
            topic=topic,
            audience=audience,
            tone=tone,
            platform=platform,
            notes=notes,
            output_path=filepath
        )

        return send_file(filepath, as_attachment=True)

    return render_template("form.html")

if __name__ == "__main__":
    app.run(debug=True)
