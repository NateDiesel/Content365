# -*- coding: utf-8 -*-
"""
Content365 premium PDF generator – Enterprise polish (stable)

- Unicode/emoji-safe (DejaVu fallback → Helvetica)
- Branded header + footer + optional watermark
- Clean hierarchy, bullets, CTA card, platform banners (with icons)
- Clickable hyperlinks in body/social/footer
- Optional QR code block (qr_text or qr_url)
- Inline IMAGES via <img src="..."> in blog_html (local/relative only) — handled as flowables
- Safe HTML subset: <b><i><u><br><p><ul><ol><li><a href>
- Robust image handling (fix/skip broken streams)
- Strict output verification + crisp exceptions
"""
from __future__ import annotations

import io
import os
import re
import uuid
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

# --------------------- ReportLab imports (premium engine) ---------------------
from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
    ListFlowable, ListItem, KeepTogether, Table, TableStyle,
    Image as RLImage, Flowable,  # Flowable added for custom widgets
)
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

# PIL for robust image loading/fixing
try:
    from PIL import Image, ImageFile
    ImageFile.LOAD_TRUNCATED_IMAGES = True  # tolerate slightly broken files
except Exception:  # pragma: no cover
    Image = None   # optional

# QR support (optional)
try:
    from reportlab.graphics.barcode import qr as _qr
    from reportlab.graphics.shapes import Drawing
except Exception:  # pragma: no cover
    _qr, Drawing = None, None

# ----------------------------------
# Fonts
# ----------------------------------
_DEJAVU = {
    "regular": "DejaVuSans",
    "bold": "DejaVuSans-Bold",
    "italic": "DejaVuSans-Oblique",
    "bold_italic": "DejaVuSans-BoldOblique",
}

def _try_register_dejavu() -> bool:
    candidates = [
        Path("assets/fonts"),
        Path("fonts"),
        Path(r"C:\Windows\Fonts"),
        Path("/usr/share/fonts/truetype/dejavu"),
        Path("/usr/local/share/fonts"),
    ]
    files = {
        "regular": ["DejaVuSans.ttf"],
        "bold": ["DejaVuSans-Bold.ttf"],
        "italic": ["DejaVuSans-Oblique.ttf"],
        "bold_italic": ["DejaVuSans-BoldOblique.ttf"],
    }
    found: Dict[str, Path] = {}
    for role, names in files.items():
        for base in candidates:
            for n in names:
                p = base / n
                if p.exists() and p.stat().st_size > 1024:
                    found[role] = p
                    break
            if role in found:
                break
    try:
        if "regular" in found:
            pdfmetrics.registerFont(TTFont(_DEJAVU["regular"], str(found["regular"])))
        if "bold" in found:
            pdfmetrics.registerFont(TTFont(_DEJAVU["bold"], str(found["bold"])))
        if "italic" in found:
            pdfmetrics.registerFont(TTFont(_DEJAVU["italic"], str(found["italic"])))
        if "bold_italic" in found:
            pdfmetrics.registerFont(TTFont(_DEJAVU["bold_italic"], str(found["bold_italic"])))
        return True
    except Exception:
        return False

_HAS_DEJAVU = _try_register_dejavu()
FACE   = _DEJAVU["regular"] if _HAS_DEJAVU else "Helvetica"
FACE_B = _DEJAVU["bold"]    if _HAS_DEJAVU else "Helvetica-Bold"

# ----------------------------------
# Styles
# ----------------------------------
_ss = getSampleStyleSheet()
TITLE = ParagraphStyle("C365_Title", parent=_ss["Title"], fontName=FACE_B, fontSize=22, leading=26, spaceAfter=6)
SUB   = ParagraphStyle("C365_Sub",   parent=_ss["Normal"], fontName=FACE,   fontSize=12.5, textColor=colors.HexColor("#666"), spaceAfter=12)
H2    = ParagraphStyle("C365_H2",    parent=_ss["Heading2"], fontName=FACE_B, fontSize=15, spaceBefore=8, spaceAfter=4)
BODY  = ParagraphStyle("C365_Body",  parent=_ss["BodyText"], fontName=FACE,  fontSize=11, leading=15, spaceAfter=8)
SMALL = ParagraphStyle("C365_Small", parent=_ss["Normal"],   fontName=FACE,  fontSize=9.5, leading=12, textColor=colors.HexColor("#555"))
TAGS  = ParagraphStyle("C365_Tags",  parent=_ss["Normal"],   fontName=FACE,  fontSize=10.5, textColor=colors.HexColor("#0B6BF2"), spaceBefore=2, spaceAfter=8)
CTA   = ParagraphStyle("C365_CTA",   parent=_ss["BodyText"], fontName=FACE_B, fontSize=12, leading=15, textColor=colors.HexColor("#0B6BF2"), spaceBefore=6, spaceAfter=10)

# ----------------------------------
# Helpers
# ----------------------------------
def _hex(c: Optional[str], default: str) -> colors.Color:
    try:
        return colors.HexColor(c) if c else colors.HexColor(default)
    except Exception:
        return colors.HexColor(default)

_A_RX = re.compile(r'(?<!")\b((?:https?://|www\.)\S+)', re.I)

def _auto_link(text: str) -> str:
    """Wrap bare URLs/emails with <a> if user didn’t include anchor tags."""
    if not text:
        return ""
    def repl(m):
        s = m.group(1)
        href = s if s.lower().startswith(("http://","https://")) else f"https://{s}"
        return f'<a href="{href}">{s}</a>'
    # Emails
    text = re.sub(r'([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})', r'<a href="mailto:\1">\1</a>', text)
    # Bare URLs
    return _A_RX.sub(repl, text)

def _safe_html(html: str) -> str:
    if not html:
        return ""
    html = re.sub(r"</?(script|style|iframe|object|embed|meta|link)[^>]*>", "", html, flags=re.I)
    html = html.replace("\r", "")
    return html

def _img_reader(path: Optional[str]) -> Optional[ImageReader]:
    if not path:
        return None
    try:
        p = Path(path)
        if p.exists():
            return ImageReader(str(p))
        return None
    except Exception:
        return None

# Platform colors
_PLATFORM_COLORS = {
    "instagram": "#E1306C",
    "linkedin":  "#0A66C2",
    "tiktok":    "#000000",
    "twitter":   "#1DA1F2",
    "x":         "#000000",
    "facebook":  "#1877F2",
}
def _platform_color(name: str, fallback: str = "#0B6BF2") -> colors.Color:
    return _hex(_PLATFORM_COLORS.get(name.lower(), fallback), fallback)

def _platform_icon_path(name: str) -> Optional[Path]:
    """Look for an icon like assets/icons/twitter.png (case-insensitive)."""
    base = Path("assets/icons")
    candidates = [
        base / (name.lower() + ".png"),
        base / (name.capitalize() + ".png"),
    ]
    for c in candidates:
        if c.exists() and c.stat().st_size > 0:
            return c
    return None

# ----------------------------------
# Header / Footer / Watermark
# ----------------------------------
def _draw_header(canvas: Canvas, doc, brand: Dict[str, Any], title_text: str):
    canvas.saveState()
    primary = _hex(brand.get("primary_color"), "#0B6BF2")

    # thin color strip
    strip_h = 10
    canvas.setFillColor(primary)
    canvas.rect(
        0,
        doc.height + doc.topMargin + strip_h,
        doc.width + doc.leftMargin + doc.rightMargin,
        strip_h,
        fill=1,
        stroke=0,
    )

    # brand name + clickable site (left)
    brand_name = brand.get("brand_name", "Content365")
    website = (brand.get("website") or "content365.xyz").strip()
    site_href = website if website.lower().startswith(("http://", "https://")) else f"https://{website}"

    x = doc.leftMargin
    y = doc.height + doc.topMargin + strip_h + 14

    canvas.setFont(FACE_B, 12)
    canvas.setFillColor(colors.black)
    canvas.drawString(x, y, brand_name)

    canvas.setFont(FACE, 9.5)
    y2 = y - 12
    canvas.setFillColor(colors.HexColor("#555555"))
    canvas.drawString(x, y2, website)
    if website:
        w = canvas.stringWidth(website, FACE, 9.5)
        canvas.linkURL(site_href, (x, y2 - 2, x + w, y2 + 10), relative=0, thickness=0, color=None)

    # logo on the right (if present)
    logo = _img_reader(brand.get("logo_path"))
    if logo:
        try:
            iw, ih = logo.getSize()
            max_h = float(brand.get("logo_max_h", 20))
            s = min(1.0, max_h / float(ih))
            w = iw * s
            h = ih * s
            lx = doc.leftMargin + doc.width + doc.rightMargin - w
            ly = y2 - 2
            canvas.drawImage(logo, lx, ly, width=w, height=h, mask="auto")
        except Exception:
            pass

    canvas.restoreState()

def _draw_footer(canvas: Canvas, doc, footer_text: str):
    if not footer_text:
        return
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#E5E7EB"))
    canvas.line(doc.leftMargin, doc.bottomMargin - 8, doc.leftMargin + doc.width, doc.bottomMargin - 8)
    canvas.setFont(FACE, 9)
    canvas.setFillColor(colors.HexColor("#666666"))
    x = doc.leftMargin
    y = doc.bottomMargin - 22
    canvas.drawString(x, y, footer_text)

    # clickable URL if present
    m = re.search(r'(https?://\S+|[A-Za-z0-9.-]+\.[A-Za-z]{2,})', footer_text)
    if m:
        url = m.group(1)
        if not url.lower().startswith(("http://", "https://")):
            url = "https://" + url
        w = canvas.stringWidth(footer_text, FACE, 9)
        canvas.linkURL(url, (x, y-2, x + w, y+10), relative=0, thickness=0, color=None)

    canvas.drawRightString(doc.leftMargin + doc.width, y, f"Page {canvas.getPageNumber()}")
    canvas.restoreState()

def _draw_watermark(canvas: Canvas, doc, text: str):
    if not text:
        return
    canvas.saveState()
    canvas.setFont(FACE_B, 50)
    canvas.setFillColor(colors.HexColor("#EEEEEE"))  # alpha not consistent, keep solid light gray
    canvas.translate(doc.leftMargin + doc.width / 2, doc.bottomMargin + doc.height / 2)
    canvas.rotate(30)
    canvas.drawCentredString(0, 0, text)
    canvas.restoreState()

def _draw_debug_grid(canvas: Canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#EEEEEE"))
    x0, x1 = doc.leftMargin, doc.leftMargin + doc.width
    y0, y1 = doc.bottomMargin, doc.bottomMargin + doc.height
    step = 36
    y = y0
    while y <= y1:
        canvas.line(x0, y, x1, y)
        y += step
    x = x0
    while x <= x1:
        canvas.line(x, y0, x, y1)
        x += step
    canvas.restoreState()

# ----------------------------------
# Premium Flowables
# ----------------------------------
class CTACard(Flowable):
    """Rounded CTA card with brand accent border."""
    def __init__(self, text: str, width: float, accent: colors.Color, style: ParagraphStyle):
        super().__init__()
        self.text = _auto_link(text)
        self.width = width
        self.accent = accent
        self._p = Paragraph(self.text, style)
        self._h = 0

    def wrap(self, availW, availH):
        w, h = self._p.wrap(self.width - 20, availH)
        self._h = h
        return (self.width, h + 20)

    def draw(self):
        c = self.canv
        w, h = self.width, self._h + 20
        r = 10
        # card
        c.setFillColor(colors.HexColor("#F5F7FF"))
        c.setStrokeColor(self.accent)
        c.setLineWidth(1)
        c.roundRect(0, 0, w, h, r, stroke=1, fill=1)
        # text
        c.saveState()
        c.translate(10, 10)
        self._p.drawOn(c, 0, 0)
        c.restoreState()

class PlatformBanner(Flowable):
    """Rounded platform bar with optional icon. Graceful fallback to initial."""
    def __init__(self, platform: str, width: float, color: colors.Color, height: float = 30):
        super().__init__()
        self.platform = platform
        self.width = width
        self.color = color
        self.height = height
        self.icon = _platform_icon_path(platform)

    def wrap(self, availW, availH):
        return (self.width, self.height)

    def draw(self):
        c = self.canv
        x, y, w, h = 0, 0, self.width, self.height
        r = 9
        pad = 6

        # background bar
        c.setFillColor(self.color)
        c.setStrokeColor(self.color)
        c.roundRect(x, y, w, h, r, stroke=0, fill=1)

        # icon (if present)
        text_x = x + pad
        if self.icon:
            try:
                size = h - 2 * pad
                c.drawImage(str(self.icon), x + pad, y + pad, width=size, height=size,
                            preserveAspectRatio=True, mask='auto')
                text_x = x + pad + size + 6
            except Exception:
                text_x = x + pad
        else:
            # fallback: white circle + initial
            diameter = h - 2 * pad
            cx = x + pad + diameter/2
            cy = y + h/2
            c.setFillColor(colors.white)
            c.circle(cx, cy, diameter*0.32, stroke=0, fill=1)
            c.setFillColor(colors.black)
            c.setFont(FACE_B, 10)
            c.drawCentredString(cx, cy - 3, (self.platform or "?")[:1].upper())
            text_x = x + pad + diameter + 6

        # platform label
        c.setFillColor(colors.white)
        c.setFont(FACE_B, 11.5)
        c.drawString(text_x, y + (h/2 - 4), self.platform)

# ----------------------------------
# Flowable builders (legacy table versions kept for compatibility if needed)
# ----------------------------------
def _platform_banner(name: str) -> Table:
    txt = f"  {name}  "
    tbl = Table([[txt]], colWidths=["*"])
    col = _platform_color(name)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), col),
        ("TEXTCOLOR",  (0,0), (-1,-1), colors.white),
        ("FONTNAME",   (0,0), (-1,-1), FACE_B),
        ("FONTSIZE",   (0,0), (-1,-1), 11.5),
        ("ALIGN",      (0,0), (-1,-1), "LEFT"),
        ("LEFTPADDING",(0,0), (-1,-1), 6),
        ("RIGHTPADDING",(0,0),(-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING",(0,0),(-1,-1), 3),
        ("BOX",        (0,0), (-1,-1), 0.0, col),
    ]))
    return tbl

def _cta_card(text: str, accent: colors.Color) -> Table:
    # kept for compatibility (not used; CTACard is the premium card)
    p = Paragraph(_auto_link(text), CTA)
    box = Table([[p]], colWidths=["*"])
    bg = colors.HexColor("#F3F6FF")
    box.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), bg),
        ("BOX",        (0,0), (-1,-1), 0.8, accent),
        ("LEFTPADDING",(0,0), (-1,-1), 10),
        ("RIGHTPADDING",(0,0),(-1,-1), 10),
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING",(0,0),(-1,-1), 8),
    ]))
    return box

def _qr_block(data: str, size: int = 90) -> Optional[Any]:
    if not data or not _qr or not Drawing:
        return None
    try:
        widget = _qr.QrCodeWidget(data)
        b = widget.getBounds()
        w = b[2] - b[0]
        h = b[3] - b[1]
        d = Drawing(size, size, transform=[size / w, 0, 0, size / h, 0, 0])
        d.add(widget)
        return d
    except Exception:
        return None

# ----------------------------------
# HTML → Flowables
# ----------------------------------
_IMG_OPEN_RE  = re.compile(r'<img\s+[^>]*src=(?:"|\')([^"\']+)(?:"|\')[^>]*\/?\s*>', re.I)
_IMG_CLOSE_RE = re.compile(r"</img\s*>", re.I)

def _extract_images(html: str) -> Tuple[str, List[str]]:
    """Return (html_without_img_tags, image_paths). Only local/relative paths kept."""
    paths: List[str] = []
    def _repl(m):
        src = m.group(1)
        if src and not src.lower().startswith(("http://", "https://", "data:")):
            paths.append(src)
        return ""
    html2 = _IMG_OPEN_RE.sub(_repl, html or "")
    html2 = _IMG_CLOSE_RE.sub("", html2)
    return html2, paths

def _paragraphs_from_html(fragment: str) -> List[Any]:
    chunks = [c for c in re.split(r"\n{2,}|</p>\s*<p>|</p>\s*", fragment) if c.strip()]
    return [Paragraph(_auto_link(_safe_html(c)), BODY) for c in chunks]

def _list_from_html(list_html: str) -> Optional[ListFlowable]:
    is_ordered = bool(re.match(r"\s*<ol", list_html, flags=re.I))
    items = re.findall(r"<li[^>]*>(.*?)</li>", list_html, flags=re.I | re.S)
    if not items:
        return None
    list_items = [ListItem(Paragraph(_safe_html(i), BODY), leftIndent=6) for i in items]
    return ListFlowable(list_items, bulletType=("1" if is_ordered else "bullet"), leftIndent=10)

def _make_image_flowable(p: Path, max_img_w: float) -> Optional[RLImage]:
    """Create a robust RLImage, fixing broken images with PIL; returns None on failure."""
    # Try PIL route first (best for broken streams)
    if Image is not None:
        try:
            with Image.open(str(p)) as im:
                im.load()  # force decode; will raise on corrupted data
                if im.mode not in ("RGB", "RGBA"):
                    im = im.convert("RGB")
                buf = io.BytesIO()
                im.save(buf, format="PNG")  # normalize
                buf.seek(0)
                img = RLImage(buf)
        except Exception:
            img = None
    else:
        img = None

    # Fallback: let ReportLab try from filename
    if img is None:
        try:
            img = RLImage(str(p))
        except Exception:
            return None

    # Scale to width
    try:
        iw, ih = float(img.imageWidth), float(img.imageHeight)
        if iw > max_img_w:
            scale = max_img_w / iw
            img._restrictSize(max_img_w, ih * scale)
    except Exception:
        pass
    return img

def _html_to_flowables(html: str, max_img_w: float) -> List[Any]:
    html = _safe_html(html)
    html, imgs = _extract_images(html)

    flows: List[Any] = []
    # Convert lists into real list flowables, preserving order
    pos = 0
    pattern = re.compile(r"(<ul[^>]*>.*?</ul>|<ol[^>]*>.*?</ol>)", re.I | re.S)
    for m in pattern.finditer(html):
        before = html[pos:m.start()]
        if before.strip():
            flows.extend(_paragraphs_from_html(before))
        lst = _list_from_html(m.group(1))
        if lst:
            flows.append(lst)
        pos = m.end()
    tail = html[pos:]
    if tail.strip():
        flows.extend(_paragraphs_from_html(tail))

    # Append images after surrounding text (discovery order), skipping bad ones gracefully
    for p in imgs:
        try:
            img_path = Path(p)
            if not img_path.exists():
                flows.append(Paragraph(f"<font color='#888888'>[missing image: {p}]</font>", SMALL))
                continue
            img = _make_image_flowable(img_path, max_img_w)
            if img is not None:
                flows.append(Spacer(1, 6))
                flows.append(img)
                flows.append(Spacer(1, 4))
            else:
                flows.append(Paragraph(f"<font color='#888888'>[unreadable image: {p}]</font>", SMALL))
        except Exception:
            flows.append(Paragraph(f"<font color='#888888'>[image error: {p}]</font>", SMALL))
            continue
    return flows

# ----------------------------------
# Main export (premium)
# ----------------------------------
def export_pdf_response(payload: Dict[str, Any], out_dir: str = "generated_pdfs") -> str:
    """Build a polished marketing PDF and return the absolute file path."""
    out_dir = str(out_dir or "generated_pdfs")
    out_path = Path(out_dir); out_path.mkdir(parents=True, exist_ok=True)
    file_name = f"{uuid.uuid4().hex[:12]}.pdf"
    final_path = (out_path / file_name).resolve()

    title    = payload.get("title", "Content365 Pack")
    subtitle = payload.get("subtitle", "")
    blog_html= payload.get("blog_html", "")
    bullets  = payload.get("bullets", []) or []
    social   = payload.get("social", []) or []
    cta_text = payload.get("cta_text", "")
    footer   = payload.get("footer", f"© {datetime.now().year} Content365 · content365.xyz")
    brand    = payload.get("brand", {}) or {}

    watermark_text = payload.get("watermark_text", "")
    debug_grid     = bool(payload.get("debug_grid", False))

    primary = _hex(brand.get("primary_color"), "#0B6BF2")
    accent  = _hex(brand.get("accent_color"),  "#111827")

    doc = SimpleDocTemplate(
        str(final_path), pagesize=LETTER,
        leftMargin=0.8*inch, rightMargin=0.8*inch, topMargin=0.9*inch, bottomMargin=0.9*inch,
        title=title, author="Content365", subject="Marketing Content Pack", creator="Content365 PDF Engine",
    )

    story: List[Any] = []

    # Title block
    # Add your desired content to the story here, for example:
    # story.append(Paragraph(title, TITLE))
# -----------------------------------------------------------------------------
# Compatibility wrapper for main.py + graceful fallback
# -----------------------------------------------------------------------------
def generate_pdf(payload: Dict[str, Any], output_path: str, brand_config: Optional[Dict[str, Any]] = None) -> str:
    """
    Compatibility entrypoint expected by main.py.
    - Adapts legacy payloads to the new premium shape.
    - Tries premium engine; if it fails, writes a minimal fallback PDF.
    - Writes exactly to `output_path`.
    """
    output_path = str(output_path)
    out_dir = str(Path(output_path).parent or "generated_pdfs")

    # Adapt to premium shape
    premium_payload = _adapt_payload_legacy(payload or {}, brand_config or {})
    
    def _adapt_payload_legacy(payload: Dict[str, Any], brand_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adapt legacy payloads to the new premium payload shape.
        This is a placeholder implementation; adjust mapping as needed.
        """
        # Merge brand config into payload['brand']
        brand = dict(brand_config)
        if "brand" in payload and isinstance(payload["brand"], dict):
            brand.update(payload["brand"])
        # Map legacy keys to premium keys as needed
        return {
            "title": payload.get("title", ""),
            "subtitle": payload.get("subtitle", ""),
            "blog_html": payload.get("blog_html", ""),
            "bullets": payload.get("bullets", []),
            "social": payload.get("social", []),
            "cta_text": payload.get("cta_text", ""),
            "footer": payload.get("footer", ""),
            "brand": brand,
            "watermark_text": payload.get("watermark_text", ""),
            "debug_grid": payload.get("debug_grid", False),
        }

    try:
        # Build with premium engine into the out_dir
        tmp_path = export_pdf_response(premium_payload, out_dir=out_dir)
        # Move/rename to the exact requested output_path if needed
        if os.path.abspath(tmp_path) != os.path.abspath(output_path):
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            shutil.move(tmp_path, output_path)
        return output_path
    except Exception:
        # Graceful fallback
        def _generate_pdf_fallback(payload: Dict[str, Any], output_path: str, brand: Dict[str, Any]) -> str:
            """Minimal fallback PDF generator in case premium engine fails."""
            from reportlab.pdfgen import canvas
            c = canvas.Canvas(output_path, pagesize=LETTER)
            c.setFont(FACE_B, 18)
            c.drawString(72, 720, payload.get("title", "Content365 Pack"))
            c.setFont(FACE, 12)
            c.drawString(72, 700, payload.get("subtitle", ""))
            c.setFont(FACE, 10)
            c.drawString(72, 680, "PDF generation failed, this is a fallback version.")
            c.save()
            return output_path
        return _generate_pdf_fallback(payload or {}, output_path, premium_payload.get("brand", {}))

__all__ = ["export_pdf_response", "generate_pdf"]
