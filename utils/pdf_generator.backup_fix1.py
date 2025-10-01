# -*- coding: utf-8 -*-
"""
Content365 premium PDF generator â€“ Enterprise polish (stable)

- Unicode/emoji-safe (DejaVu fallback â†’ Helvetica)
- Branded header + footer + optional watermark
- Clean hierarchy, bullets, CTA card, platform banners
- Clickable hyperlinks in body/social/footer
- Optional QR code block (qr_text or qr_url)
- Inline IMAGES via <img src="..."> in blog_html (local/relative only) â€” handled as flowables
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
    ListFlowable, ListItem, KeepTogether, Table, TableStyle, Image as RLImage
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
    Image = None   # we'll still attempt ReportLab direct load

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
    """Wrap bare URLs/emails with <a> if user didnâ€™t include anchor tags."""
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
    canvas.setFillColor(colors.HexColor("#EEEEEE"))  # alpha not consistent; keep solid light gray
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
# Flowable builders
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
# HTML â†’ Flowables
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
    return [Paragraph(_auto_link(c), BODY) for c in chunks]

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
    footer   = payload.get("footer", f"Â© {datetime.now().year} Content365 Â· content365.xyz")
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
    story.append(Spacer(1, 6))
    story.append(KeepTogether([Paragraph(title, TITLE)]))
    if subtitle:
        story.append(Paragraph(subtitle, SUB))

    story.append(HRFlowable(width="100%", color=primary, thickness=1.2, spaceBefore=6, spaceAfter=10))

    # Body (with images/lists)
    if blog_html:
        story.extend(_html_to_flowables(blog_html, max_img_w=doc.width))

    # Bullets (explicit field)
    if bullets:
        items: List[ListItem] = []
        for b in bullets:
            items.append(ListItem(Paragraph(_safe_html(str(b)), BODY), leftIndent=6))

        lst = ListFlowable(
            items,
            bulletType="bullet",
            bulletChar="â€¢",      # solid dot, renders under Helvetica/DejaVu
            leftIndent=10
        )
        story.append(lst)
        story.append(Spacer(1, 4))

    # CTA
    if cta_text:
        story.append(Spacer(1, 4))
        story.append(_cta_card(cta_text, accent))

    # QR (if any)
    qr_text = payload.get("qr_text") or payload.get("qr_url") or ""
    if qr_text:
        q = _qr_block(qr_text)
        if q:
            story.append(Spacer(1, 10))
            story.append(q)

    # Social sections
    if social:
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", color=primary, thickness=1.0, spaceBefore=8, spaceAfter=6))
        for idx, s in enumerate(social, start=1):
            name = s.get("name", f"Platform {idx}")
            caption = s.get("caption", "")
            hashtags = s.get("hashtags", []) or []

            story.append(_platform_banner(name))
            story.append(Spacer(1, 4))

            if caption:
                story.append(Paragraph(_safe_html(_auto_link(caption)), BODY))
            if hashtags:
                tag_line = " ".join(h for h in hashtags if isinstance(h, str) and h.strip())
                if tag_line:
                    story.append(Paragraph(tag_line, TAGS))
                    story.append(Spacer(1, 4))
            story.append(Spacer(1, 6))

    # Page callbacks
    def _on_page(c: Canvas, d):
        if debug_grid:
            _draw_debug_grid(c, d)
        _draw_watermark(c, d, watermark_text)
        _draw_header(c, d, brand, "Content365 Â· Marketing Pack")
        _draw_footer(c, d, footer)

    # Build & verify
    try:
        doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    except Exception as e:
        try:
            if final_path.exists() and final_path.stat().st_size < 1024:
                final_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise RuntimeError(f"PDF build failed: {e!r}")

    if not final_path.exists() or final_path.stat().st_size == 0:
        raise RuntimeError("PDF generation produced no output file (post-build).")

    return str(final_path)

# -----------------------------------------------------------------------------
# Compatibility: accept legacy/new payloads and normalize to premium shape
# -----------------------------------------------------------------------------
def _adapt_payload_legacy(payload: Dict[str, Any], brand_cfg: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Accepts both new shape and legacy:
      - New: {title, subtitle, blog_html, bullets, social[{name,caption,hashtags}], ...}
      - Legacy A: {blog:{headline,intro,body[],bullets[],cta}, captions:{plat:text|{text}}, hashtags:{plat:[...]}}
      - Legacy B: {blog:{title,intro,bullets,cta}, platforms:{plat:{caption,hashtags}}}
    Produces the new shape for export_pdf_response.
    """
    if "blog_html" in payload or "social" in payload:
        # Already new shape
        newp = dict(payload)
    else:
        blog = payload.get("blog") or {}
        title = blog.get("headline") or blog.get("title") or payload.get("title") or "Content365 Pack"
        subtitle = payload.get("subtitle") or ""
        # Build blog_html from intro/body if present
        parts: List[str] = []
        if blog.get("intro"):
            parts.append(f"<p>{blog['intro']}</p>")
        for p in (blog.get("body") or []):
            parts.append(f"<p>{p}</p>")
        blog_html = payload.get("blog_html") or "\n".join(parts)
        bullets = blog.get("bullets") or payload.get("bullets") or []
        cta = blog.get("cta") or payload.get("cta_text") or ""

        social: List[Dict[str, Any]] = []
        captions = payload.get("captions") or {}
        hashtags = payload.get("hashtags") or {}
        platforms = payload.get("platforms") or {}

        if captions:
            # captions + hashtags dicts
            for plat, cap in captions.items():
                text = cap.get("text") if isinstance(cap, dict) else str(cap or "")
                hts = hashtags.get(plat) or []
                social.append({"name": plat, "caption": text, "hashtags": hts})
        elif platforms:
            # platforms dict with caption + hashtags
            for plat, data in platforms.items():
                data = data or {}
                social.append({"name": plat, "caption": data.get("caption") or "", "hashtags": data.get("hashtags") or []})

        newp = {
            "title": title,
            "subtitle": subtitle,
            "blog_html": blog_html,
            "bullets": bullets,
            "cta_text": cta,
            "social": social,
        }

    # --- brand normalization (defensive + defaults) ---
    _cfg = (brand_cfg or payload.get("brand") or {}) or {}

    brand_name = str(_cfg.get("brand_name") or "Content365").strip() or "Content365"
    website    = str(_cfg.get("website")    or "content365.xyz").strip() or "content365.xyz"

    logo_path  = _cfg.get("logo_path") or None
    try:
        logo_max_h = int(_cfg.get("logo_max_h", 22))
    except Exception:
        logo_max_h = 22

    primary    = str(_cfg.get("primary_color") or "#0B6BF2").strip() or "#0B6BF2"
    accent     = str(_cfg.get("accent_color")  or "#111827").strip() or "#111827"

    newp["brand"] = {
        "brand_name":    brand_name,
        "website":       website,
        "logo_path":     logo_path,
        "logo_max_h":    logo_max_h,   # used for header logo scaling
        "primary_color": primary,      # header + rules
        "accent_color":  accent,       # CTA border
    }

    # --- footer default ---
    if "footer" not in newp:
        newp["footer"] = payload.get("footer") or f"Â© {datetime.now().year} {newp['brand']['brand_name']} Â· {newp['brand']['website']}"

    return newp

# --------------------------- Tiny pure-Python fallback ------------------------
class _MiniPDF:
    PAGE_W = 612   # 8.5" * 72
    PAGE_H = 792   # 11"  * 72
    MARGIN_L = 54
    MARGIN_R = 54
    MARGIN_T = 86
    MARGIN_B = 58
    LEADING = 14
    FONT_SIZE = 11

    def __init__(self):
        self.objects: List[bytes] = []
        self.pages: List[int] = []
        self.font_obj = self._add_object(self._font_object("F1", "Helvetica"))

    def _add_object(self, body: bytes) -> int:
        self.objects.append(body)
        return len(self.objects)

    @staticmethod
    def _pdf_str(s: str) -> str:
        safe = ''.join((c if 32 <= ord(c) < 127 and c not in '()' else ('\\' + c if c in '()' else '?')) for c in (s or ""))
        return safe

    @staticmethod
    def _font_object(name: str, base: str) -> bytes:
        return f"<< /Type /Font /Subtype /Type1 /BaseFont /{base} /Name /{name} >>".encode()

    def _begin_page(self, content_stream: bytes) -> int:
        content_obj = self._add_object(b"<< /Length %d >>\nstream\n" % len(content_stream) + content_stream + b"\nendstream")
        page_dict = (
            f"<< /Type /Page /Parent 0 0 R /MediaBox [0 0 {self.PAGE_W} {self.PAGE_H}] "
            f"/Resources << /Font << /F1 {self.font_obj} 0 R >> >> /Contents {content_obj} 0 R >>"
        ).encode()
        page_obj = self._add_object(page_dict)
        self.pages.append(page_obj)
        return page_obj

    def _header_footer_stream(self, page_num: int, page_count: int) -> str:
        header = f"0.85 g 0 {self.PAGE_H-36} {self.PAGE_W} 24 re f 0 g\n"
        footer = f"0.95 g 0 24 {self.PAGE_W} 18 re f 0 g\n"
        label = f"Page {page_num} of {page_count}"
        est_w = int(len(label) * (self.FONT_SIZE * 0.5))
        x = self.PAGE_W - self.MARGIN_R - est_w
        y = 30
        text = f"BT /F1 {self.FONT_SIZE} Tf {x} {y} Td ({self._pdf_str(label)}) Tj ET\n"
        return header + footer + text

    def _text_block(self, line: str, x: int, y: int, leading: int) -> str:
        l = self._pdf_str(line)
        return f"BT /F1 {self.FONT_SIZE} Tf {x} {y} Td {leading} TL ({l}) Tj ET\n"

    def add_page(self, lines: List[str], page_num: int, page_count: int):
        buf: List[str] = [self._header_footer_stream(page_num, page_count)]
        cursor_y = self.PAGE_H - self.MARGIN_T
        x = self.MARGIN_L
        for line in lines:
            if cursor_y < self.MARGIN_B + 3 * self.LEADING:
                break
            buf.append(self._text_block(line, x, cursor_y, self.LEADING))
            cursor_y -= self.LEADING
        self._begin_page("".join(buf).encode("latin-1", errors="ignore"))

    def save(self, path: str):
        kids = " ".join(f"{p} 0 R" for p in self.pages)
        pages_obj = self._add_object(f"<< /Type /Pages /Kids [{kids}] /Count {len(self.pages)} >>".encode())
        fixed = [obj.replace(b"/Parent 0 0 R", f"/Parent {pages_obj} 0 R".encode()) for obj in self.objects]
        self.objects = fixed
        catalog_obj = self._add_object(f"<< /Type /Catalog /Pages {pages_obj} 0 R >>".encode())
        with open(path, "wb") as f:
            f.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
            offsets = [0]
            for i, obj in enumerate(self.objects, start=1):
                offsets.append(f.tell())
                f.write(f"{i} 0 obj\n".encode()); f.write(obj); f.write(b"\nendobj\n")
            xref_pos = f.tell()
            f.write(f"xref\n0 {len(self.objects)+1}\n".encode())
            f.write(b"0000000000 65535 f \n")
            for off in offsets[1:]:
                f.write(f"{off:010d} 00000 n \n".encode())
            f.write(b"trailer\n"); f.write(f"<< /Size {len(self.objects)+1} /Root {catalog_obj} 0 R >>\n".encode())
            f.write(b"startxref\n"); f.write(f"{xref_pos}\n".encode()); f.write(b"%%EOF")

def _generate_pdf_fallback(payload: Dict[str, Any], output_path: str, brand: Dict[str, Any]) -> str:
    """Minimal dependency-free PDF if premium engine fails."""
    lines: List[str] = []
    title = payload.get("title") or (payload.get("blog", {}) or {}).get("headline") or "Content365 Pack"
    lines += [title.upper(), ""]
    intro = (payload.get("blog", {}) or {}).get("intro") or ""
    if intro: lines += [intro, ""]
    for p in (payload.get("blog", {}) or {}).get("body") or []:
        lines += [str(p), ""]
    for b in payload.get("bullets", []) or (payload.get("blog", {}) or {}).get("bullets") or []:
        lines.append(f"- {b}")
    cta = payload.get("cta_text") or (payload.get("blog", {}) or {}).get("cta") or ""
    if cta: lines += ["", cta]
    # social
    social = payload.get("social") or []
    platforms = payload.get("platforms") or {}
    if not social and platforms:
        for name, data in platforms.items():
            social.append({"name": name, "caption": data.get("caption",""), "hashtags": data.get("hashtags",[])})
    if social:
        lines += ["", "SOCIAL CAPTIONS:"]
        for s in social:
            lines.append(f"{s.get('name', 'Platform')}: {s.get('caption','')}")
            hts = s.get("hashtags") or []
            if hts: lines.append("  " + " ".join(str(h) for h in hts))
    # crude wrap + paginate
    pdf = _MiniPDF()
    max_chars = 90
    wrapped: List[str] = []
    for ln in lines:
        words = ln.split()
        if not words:
            wrapped.append("")
            continue
        cur: List[str] = []
        cur_len = 0
        for w in words:
            add = (1 if cur else 0) + len(w)
            if cur_len + add <= max_chars:
                cur.append(w); cur_len += add
            else:
                wrapped.append(" ".join(cur)); cur=[w]; cur_len=len(w)
        if cur: wrapped.append(" ".join(cur))
    line_budget = int((pdf.PAGE_H - pdf.MARGIN_T - pdf.MARGIN_B) / pdf.LEADING)
    pages = [wrapped[i:i+line_budget] for i in range(0, len(wrapped), line_budget)]
    for i, pg in enumerate(pages, start=1):
        pdf.add_page(pg, i, len(pages))
    pdf.save(output_path)
    return output_path

# -----------------------------------------------------------------------------
# Compatibility: accept legacy/new payloads and normalize to premium shape
# -----------------------------------------------------------------------------
def _adapt_payload_legacy(payload: Dict[str, Any], brand_cfg: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Accepts both new shape and legacy:
      - New: {title, subtitle, blog_html, bullets, social[{name,caption,hashtags}], ...}
      - Legacy A: {blog:{headline,intro,body[],bullets[],cta}, captions:{plat:text|{text}}, hashtags:{plat:[...]}}
      - Legacy B: {blog:{title,intro,bullets,cta}, platforms:{plat:{caption,hashtags}}}
    Produces the new shape for export_pdf_response.
    """
    if "blog_html" in payload or "social" in payload:
        # Already new shape
        newp = dict(payload)
    else:
        blog = payload.get("blog") or {}
        title = blog.get("headline") or blog.get("title") or payload.get("title") or "Content365 Pack"
        subtitle = payload.get("subtitle") or ""
        # Build blog_html from intro/body if present
        parts: List[str] = []
        if blog.get("intro"):
            parts.append(f"<p>{blog['intro']}</p>")
        for p in (blog.get("body") or []):
            parts.append(f"<p>{p}</p>")
        blog_html = payload.get("blog_html") or "\n".join(parts)
        bullets = blog.get("bullets") or payload.get("bullets") or []
        cta = blog.get("cta") or payload.get("cta_text") or ""

        social: List[Dict[str, Any]] = []
        captions = payload.get("captions") or {}
        hashtags = payload.get("hashtags") or {}
        platforms = payload.get("platforms") or {}

        if captions:
            # captions + hashtags dicts
            for plat, cap in captions.items():
                text = cap.get("text") if isinstance(cap, dict) else str(cap or "")
                hts = hashtags.get(plat) or []
                social.append({"name": plat, "caption": text, "hashtags": hts})
        elif platforms:
            # platforms dict with caption + hashtags
            for plat, data in platforms.items():
                data = data or {}
                social.append({"name": plat, "caption": data.get("caption") or "", "hashtags": data.get("hashtags") or []})

        newp = {
            "title": title,
            "subtitle": subtitle,
            "blog_html": blog_html,
            "bullets": bullets,
            "cta_text": cta,
            "social": social,
        }

    # --- brand normalization (defensive + defaults) ---
    _cfg = (brand_cfg or payload.get("brand") or {}) or {}

    brand_name = str(_cfg.get("brand_name") or "Content365").strip() or "Content365"
    website    = str(_cfg.get("website")    or "content365.xyz").strip() or "content365.xyz"

    logo_path  = _cfg.get("logo_path") or None
    try:
        logo_max_h = int(_cfg.get("logo_max_h", 22))
    except Exception:
        logo_max_h = 22

    primary    = str(_cfg.get("primary_color") or "#0B6BF2").strip() or "#0B6BF2"
    accent     = str(_cfg.get("accent_color")  or "#111827").strip() or "#111827"

    newp["brand"] = {
        "brand_name":    brand_name,
        "website":       website,
        "logo_path":     logo_path,
        "logo_max_h":    logo_max_h,   # used for header logo scaling
        "primary_color": primary,      # header + rules
        "accent_color":  accent,       # CTA border
    }

    # --- footer default ---
    if "footer" not in newp:
        newp["footer"] = payload.get("footer") or f"Â© {datetime.now().year} {newp['brand']['brand_name']} Â· {newp['brand']['website']}"

    return newp

