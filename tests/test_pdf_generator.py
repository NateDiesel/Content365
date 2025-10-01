# tests/test_pdf_generator.py
import os
from Content365.utils.pdf_generator import generate_pdf

def test_generate_basic(tmp_path):
    gpt = {
        "blog": {"title": "Title", "intro": "Intro", "bullets": ["A","B"], "cta": "Do thing"},
        "platforms": {"Instagram": {"caption": "Hello world", "hashtags": ["#a","#b"]}},
    }
    out = tmp_path/"out.pdf"
    path = generate_pdf(gpt, output_path=str(out), brand_config={"brand_name":"Content365"})
    assert os.path.exists(path)
    assert os.path.getsize(path) > 500  # should not be empty

def test_handles_missing_keys(tmp_path):
    gpt = {"blog": {"title": "Only Title"}}
    out = tmp_path/"out2.pdf"
    path = generate_pdf(gpt, output_path=str(out), brand_config={})
    assert os.path.exists(path)

# --- Added tests below ---

def test_ignores_blank_hashtags(tmp_path):
    """Blank/space-only/duplicate hashtags should not break generation."""
    gpt = {
        "blog": {"title": "T", "intro": "I", "bullets": ["One"]},
        "platforms": {
            "Twitter": {"caption": "C", "hashtags": ["", "   ", "#ok", "ok", None]},
        },
    }
    out = tmp_path / "out3.pdf"
    path = generate_pdf(gpt, output_path=str(out), brand_config={"brand_name": "Content365"})
    assert out.exists() and out.stat().st_size > 500

def test_emojis_ok(tmp_path):
    """PDF should still generate when emoji are present (they're stripped for rendering)."""
    gpt = {
        "blog": {
            "title": "Emoji Test ðŸš€",
            "intro": "Intro with emoji ðŸ’¡",
            "bullets": ["One âœ…", "Two ðŸ”¥"],
            "cta": "Go â†’",
        },
        "platforms": {
            "Instagram": {"caption": "Caption with emoji ðŸ˜€ðŸ˜ŽðŸ”¥", "hashtags": ["#tag"]},
        },
    }
    out = tmp_path / "emoji.pdf"
    path = generate_pdf(gpt, output_path=str(out), brand_config={"brand_name": "Content365"})
    assert out.exists() and out.stat().st_size > 500

def test_wrapping_long_text(tmp_path):
    """Long captions should wrap and paginate without errors."""
    long_caption = (
        "This is a very long caption intended to test line wrapping and fallback pagination in the PDF "
        "builder. It should wrap across multiple lines without crashing or overlapping the footer region. "
    ) * 8
    gpt = {
        "blog": {"title": "Wrap Test", "intro": long_caption, "bullets": ["Alpha", "Beta", "Gamma"]},
        "platforms": {
            "LinkedIn": {"caption": long_caption, "hashtags": ["#One", "#Two", "#Three"]},
        },
    }
    out = tmp_path / "wrap.pdf"
    path = generate_pdf(gpt, output_path=str(out), brand_config={"brand_name": "Content365"})
    assert out.exists() and out.stat().st_size > 500
