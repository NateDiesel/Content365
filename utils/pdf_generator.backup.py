from __future__ import annotations
import os, io, uuid
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

# ReportLab imports
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, ListFlowable, ListItem, PageBreak
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

BASE_DIR = Path(os.getcwd()).resolve()

def _safe_color(rgb: Tuple[float, float, float] | str | None, default=(0.12, 0.46, 0.95)):
    try:
        if isinstance(rgb, (tuple, list)) and len(rgb) == 3:
            r, g, b = rgb
            return colors.Color(float(r), float(g), float(b))
        if isinstance(rgb, str):
            # hex "#RRGGBB"
            rgb = rgb.lstrip("#")
            r = int(rgb[0:2], 16) / 255.0
            g = int(rgb[2:4], 16) / 255.0
            b = int(rgb[4:6], 16) / 255.0
            return colors.Color(r, g, b)
    except Exception:
        pass
    r, g, b = default
    return colors.Color(r, g, b)

def _try_register_fonts():
    # Prefer DejaVuSans if present
    try:
        reg = BASE_DIR / "assets" / "fonts" / "DejaVuSans.ttf"
        bold = BASE_DIR / "assets" / "fonts" / "DejaVuSans-Bold.ttf"
        if reg.exists():
            pdfmetrics.registerFont(TTFont("DejaVuSans", str(reg)))
            pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", str(bold if bold.exists() else reg)))
            return "DejaVuSans", "DejaVuSans-Bold"
    except Exception:
        pass
    # Fallback to Helvetica
    return "Helvetica", "Helvetica-Bold"

def _coerce_blog(blog: Dict[str, Any]) -> Dict[str, Any]:
    blog = blog or {}
    return {
        "headline": blog.get("headline") or blog.get("title") or "Your Content Pack",
        "intro": blog.get("intro") or blog.get("introduction") or "",
        "body": blog.get("body") or [],
        "bullets": blog.get("bullets") or blog.get("points") or [],
        "cta": blog.get("cta") or blog.get("CTA") or "",
    }

def _abs_path(p: str | os.PathLike | None) -> Optional[str]:
    if not p:
        return None
    p = str(p)
    ap = Path(p)
    if not ap.is_absolute():
        ap = (BASE_DIR / p).resolve()
    return str(ap)

def _build_story(payload: Dict[str, Any], brand: Dict[str, Any]) -> List[Any]:
    blog = _coerce_blog(payload.get("blog") or {})
    captions = payload.get("captions") or {}
    hashtags = payload.get("hashtags") or {}

    brand_name   = brand.get("brand_name") or "Content365"
    website      = brand.get("website") or "content365.xyz"
    logo_path    = _abs_path(brand.get("logo_path") or "assets/logo.png")
    primary_col  = _safe_color(brand.get("primary_color"))
    footer_text  = brand.get("footer_text") or f"© {brand_name}"
    hero_hook    = brand.get("hero_hook") or ""
    hero_cta     = brand.get("hero_cta") or ""

    # Fonts / styles
    base_font, base_bold = _try_register_fonts()
    styles = getSampleStyleSheet()
    styles["Normal"].fontName = base_font
    styles["Normal"].fontSize = 10.5
    styles["Normal"].leading  = 14
    styles["Title"].fontName  = base_bold
    styles["Title"].fontSize  = 20
    styles["Title"].textColor = primary_col

    h2 = ParagraphStyle(
        "H2", parent=styles["Heading2"], fontName=base_bold, fontSize=14,
        textColor=colors.black, spaceBefore=10, spaceAfter=6
    )
    bullet = ParagraphStyle(
        "Bullet", parent=styles["Normal"], leftIndent=14
    )
    meta = ParagraphStyle(
        "Meta", parent=styles["Normal"], textColor=colors.grey, fontSize=9
    )
    cta = ParagraphStyle(
        "CTA", parent=styles["Normal"], textColor=primary_col, fontName=base_bold, fontSize=12
    )

    story: List[Any] = []

    # Header with logo + brand
    if logo_path and Path(logo_path).exists():
        story.append(Image(logo_path, width=1.0*inch, height=1.0*inch, hAlign="LEFT"))
    story.append(Paragraph(brand_name, styles["Title"]))
    story.append(Paragraph(website, meta))
    story.append(Spacer(1, 0.2*inch))

    # Headline / Intro
    story.append(Paragraph(blog["headline"], h2))
    if blog["intro"]:
        story.append(Paragraph(blog["intro"], styles["Normal"]))
        story.append(Spacer(1, 0.1*inch))

    # Body paragraphs
    body = blog.get("body") or []
    if isinstance(body, str):
        body = [body]
    for para in body[:8]:
        story.append(Paragraph(str(para), styles["Normal"]))
        story.append(Spacer(1, 0.08*inch))

    # Bullets
    bullets = blog.get("bullets") or []
    if bullets:
        story.append(Spacer(1, 0.08*inch))
        story.append(Paragraph("Key Points", h2))
        items = [ListItem(Paragraph(str(b), bullet), leftIndent=4) for b in bullets[:10]]
        story.append(ListFlowable(items, bulletType="bullet", start="•", leftIndent=12))
        story.append(Spacer(1, 0.08*inch))

    # Hero CTA
    if hero_hook or hero_cta:
        story.append(Spacer(1, 0.12*inch))
        if hero_hook:
            story.append(Paragraph(hero_hook, styles["Normal"]))
        if hero_cta:
            story.append(Paragraph(hero_cta, cta))
        story.append(Spacer(1, 0.12*inch))

    # Captions per platform
    if captions:
        story.append(PageBreak())
        story.append(Paragraph("Captions by Platform", h2))
        for platform, cap in captions.items():
            story.append(Paragraph(f"<b>{platform}</b>", styles["Normal"]))
            story.append(Paragraph(str(cap or ""), styles["Normal"]))
            tags = hashtags.get(platform) or []
            if tags:
                tag_line = " ".join(f"#{str(t).lstrip('#')}" for t in tags[:12])
                story.append(Paragraph(tag_line, meta))
            story.append(Spacer(1, 0.08*inch))

    # Footer (small gray text)
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph(footer_text, meta))

    return story

def _render_to_path(out_path: str, story: List[Any]):
    out_dir = Path(out_path).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(out_path, pagesize=letter,
                            leftMargin=0.75*inch, rightMargin=0.75*inch,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    doc.build(story)

def _render_to_bytes(story: List[Any]) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                            leftMargin=0.75*inch, rightMargin=0.75*inch,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    doc.build(story)
    return buf.getvalue()

def get_pdf_engine_info() -> Dict[str, Any]:
    base_font, base_bold = _try_register_fonts()
    return {"engine": "reportlab", "font_regular": base_font, "font_bold": base_bold}

# === Public APIs (compatible with both old/new call sites) ===

def generate_pdf(payload: Dict[str, Any],
                 out_path: Optional[str] = None,
                 brand_config: Optional[Dict[str, Any]] = None):
    """If out_path is provided, write to disk (return None).
       Otherwise, return PDF bytes."""
    brand = brand_config or {}
    story = _build_story(payload, brand)
    if out_path:
        _render_to_path(out_path, story)
        return None
    return _render_to_bytes(story)

def export_pdf_response(payload: Dict[str, Any], out_dir: Optional[str] = None) -> str:
    """Legacy API used by older code. Writes a file and returns its path."""
    out_dir = out_dir or "generated"
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    out_path = Path(out_dir) / f"{uuid.uuid4().hex[:12]}.pdf"
    story = _build_story(payload, {})
    _render_to_path(str(out_path), story)
    return str(out_path)
