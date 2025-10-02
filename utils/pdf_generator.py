# -*- coding: utf-8 -*-
"""
Content365 premium PDF generator — Enterprise polish (stable)

- Unicode/emoji-safe (DejaVu fallback → Helvetica) with sanitizer on fallback hosts
- Branded header + footer + optional watermark
- Clean hierarchy, bullets, CTA card, platform banners
- Clickable hyperlinks in body/social/footer
- Optional QR code block + footer QR
- Inline IMAGES via <img src="..."> in blog_html (local/relative only) — handled as flowables
- Safe HTML subset (defensive)
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
try:
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
    # Optional QR rendering
    from reportlab.graphics.barcode import qr as rl_qr  # pragma: no cover
    from reportlab.graphics.shapes import Drawing      # pragma: no cover
    from reportlab.graphics import renderPDF           # pragma: no cover
except Exception:  # pragma: no cover
    colors = None
    LETTER = (612, 792)
    getSampleStyleSheet = lambda: {}  # type: ignore
    ParagraphStyle = object  # type: ignore
    SimpleDocTemplate = object  # type: ignore
    Paragraph = object  # type: ignore
    Spacer = object  # type: ignore
    HRFlowable = object  # type: ignore
    ListFlowable = object  # type: ignore
    ListItem = object  # type: ignore
    KeepTogether = object  # type: ignore
    Table = object  # type: ignore
    TableStyle = object  # type: ignore
    RLImage = object  # type: ignore
    ImageReader = object  # type: ignore
    pdfmetrics = None
    TTFont = object  # type: ignore
    Canvas = object  # type: ignore
    rl_qr = None     # type: ignore
    Drawing = object # type: ignore
    renderPDF = None # type: ignore
    # IMPORTANT: provide a safe unit fallback so downstream defaults don't crash
    inch = 72  # type: ignore

# PIL for robust image loading/fixing (optional)
try:
    from PIL import Image, ImageFile  # pragma: no cover
    ImageFile.LOAD_TRUNCATED_IMAGES = True
except Exception:  # pragma: no cover
    Image = None

# after the try/except that imports reportlab and defines fallbacks
_HAS_REPORTLAB = not (
    colors is None
    or Paragraph is object
    or SimpleDocTemplate is object
    or ParagraphStyle is object
)

# -----------------------------------------------------------------------------
# Fonts (Unicode coverage with graceful fallback)
# -----------------------------------------------------------------------------
def _register_fonts() -> dict:
    """
    Try to register DejaVu Sans (broad Unicode coverage). Fall back to Helvetica if not found.
    Returns a dict of canonical font names to use in styles.
    """
    if pdfmetrics is None:
        return {
            "regular": "Helvetica",
            "bold": "Helvetica-Bold",
            "italic": "Helvetica-Oblique",
            "bold_italic": "Helvetica-BoldOblique",
        }
    FONT_DIRS = [
        os.path.join(os.getcwd(), "fonts"),
        (os.path.join(os.path.dirname(__file__), "fonts") if "__file__" in globals() else None),
        "/usr/share/fonts/truetype/dejavu",
        "/usr/local/share/fonts",
        "/Library/Fonts",
        "C:\\Windows\\Fonts",
    ]
    FONT_DIRS = [p for p in FONT_DIRS if p and os.path.isdir(p)]
    candidates = {
        "regular": ["DejaVuSans.ttf"],
        "bold": ["DejaVuSans-Bold.ttf"],
        "italic": ["DejaVuSans-Oblique.ttf", "DejaVuSans-Italic.ttf"],
        "bold_italic": ["DejaVuSans-BoldOblique.ttf", "DejaVuSans-BoldItalic.ttf"],
    }
    found: Dict[str, str] = {}
    for role, names in candidates.items():
        for base in FONT_DIRS:
            for fname in names:
                path = os.path.join(base, fname)
                if os.path.isfile(path) and os.path.getsize(path) > 1024:
                    try:
                        pdfmetrics.registerFont(TTFont(f"DejaVu-{role}", path))
                        found[role] = f"DejaVu-{role}"
                        break
                    except Exception:
                        pass
            if role in found:
                break
    if {"regular", "bold"} <= set(found):
        return {
            "regular": found["regular"],
            "bold": found["bold"],
            "italic": found.get("italic", found["regular"]),
            "bold_italic": found.get("bold_italic", found["bold"]),
        }
    # Fallback to core 14
    return {
        "regular": "Helvetica",
        "bold": "Helvetica-Bold",
        "italic": "Helvetica-Oblique",
        "bold_italic": "Helvetica-BoldOblique",
    }

_FONTS = _register_fonts()
FACE   = _FONTS["regular"]
FACE_B = _FONTS["bold"]

# -----------------------------------------------------------------------------
# Emoji/Text sanitizer for Helvetica fallback
# -----------------------------------------------------------------------------
_EMOJI_MAP = {
    "✅":"✔", "✔️":"✔", "❌":"✖",
    "➜":"→", "➡️":"→",
    "📣":"[CTA]", "🔗":"[link]", "💡":"[idea]",
    "⭐":"*", "🔥":"[hot]", "🚀":"[launch]", "📈":"[up]", "👇":"↓",
}
# Broad emoji ranges (BMP + common symbols)
_EMOJI_RANGES = [(0x1F300,0x1FAFF), (0x1F1E6,0x1F1FF), (0x2600,0x27BF)]

def _looks_like_emoji(ch: str) -> bool:
    cp = ord(ch)
    if cp in (0xFE0E, 0xFE0F):  # variation selectors
        return True
    for a, b in _EMOJI_RANGES:
        if a <= cp <= b:
            return True
    return False

def _sanitize_for_font(s: str) -> str:
    """Map/strip emoji only when DejaVu is NOT active (Helvetica fallback)."""
    if not isinstance(s, str):
        s = str(s or "")
    for k, v in _EMOJI_MAP.items():
        s = s.replace(k, v)
    if "dejavu" not in _FONTS["regular"].lower():
        s = "".join(ch for ch in s if not _looks_like_emoji(ch))
    return s

# -----------------------------------------------------------------------------
# Styles
# -----------------------------------------------------------------------------
if _HAS_REPORTLAB:
    _ss = getSampleStyleSheet()
    TITLE = ParagraphStyle("C365_Title", parent=_ss["Title"],   fontName=FACE_B, fontSize=22, leading=26, spaceAfter=6)
    SUB   = ParagraphStyle("C365_Sub",   parent=_ss["Normal"],  fontName=FACE,   fontSize=12.5, textColor=colors.HexColor("#666666"), spaceAfter=12)
    H2    = ParagraphStyle("C365_H2",    parent=_ss["Heading2"],fontName=FACE_B, fontSize=15, spaceBefore=8, spaceAfter=4)
    BODY  = ParagraphStyle("C365_Body",  parent=_ss["BodyText"],fontName=FACE,   fontSize=11, leading=15, spaceAfter=8)
    SMALL = ParagraphStyle("C365_Small", parent=_ss["Normal"],  fontName=FACE,   fontSize=9.5, leading=12, textColor=colors.HexColor("#555555"))
    TAGS  = ParagraphStyle("C365_Tags",  parent=_ss["Normal"],  fontName=FACE,   fontSize=10, leading=13, textColor=colors.HexColor("#0B6BF2"), spaceBefore=2, spaceAfter=8)
    CTA   = ParagraphStyle("C365_CTA",   parent=_ss["BodyText"],fontName=FACE_B, fontSize=12, leading=15, textColor=colors.HexColor("#111827"), spaceBefore=6, spaceAfter=10)

    CAPTION = ParagraphStyle(
        "C365_Caption",
        parent=_ss["Normal"],
        fontName=FACE,
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#6B7280"),
        alignment=1,
        spaceBefore=2,
        spaceAfter=6,
    )
else:
    # Dummy placeholders so references exist; they won't be used in fallback path.
    class _DummyStyle: pass
    TITLE = SUB = H2 = BODY = SMALL = TAGS = CTA = CAPTION = _DummyStyle()

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _hex(c: Optional[str], default: str) -> str:
    """
    Validate and normalize to '#RRGGBB'; fall back to `default` if invalid.
    Accepts 'RRGGBB' or '#RRGGBB' and returns '#RRGGBB'.
    """
    c = (c or "").strip()
    if re.fullmatch(r"#?[0-9A-Fa-f]{6}", c):
        return c if c.startswith("#") else f"#{c}"
    return default

# Bare URL recognizer (skip things already inside href="...").
_A_RX = re.compile(r'(?<!")\b((?:https?://|www\.)\S+)', re.I)

def _auto_link(text: str) -> str:
    """Wrap bare URLs/emails with <a> if user didn’t include anchor tags."""
    if not text:
        return ""
    # Emails
    text = re.sub(r'([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})', r'<a href="mailto:\1">\1</a>', text)
    # Bare URLs
    def repl(m):
        s = m.group(1)
        href = s if s.lower().startswith(("http://", "https://")) else f"https://{s}"
        return f'<a href="{href}">{s}</a>'
    return _A_RX.sub(repl, text)

def _safe_html(html: str) -> str:
    if not html:
        return ""
    html = re.sub(r"</?(script|style|iframe|object|embed|meta|link)[^>]*>", "", html, flags=re.I)
    html = html.replace("\r", "")
    return html

def _img_reader(path: Optional[str]) -> Optional["ImageReader"]:
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
def _platform_color(name: str, fallback: str = "#0B6BF2") -> Any:
    return colors.HexColor(_PLATFORM_COLORS.get(name.lower(), fallback))

# -----------------------------------------------------------------------------
# Header / Footer / Watermark / Debug grid
# -----------------------------------------------------------------------------
def _draw_qr(canvas: Canvas, x: float, y: float, size: float, url: str) -> None:
    """Draw a QR code linking to `url` at (x,y) with `size` square. Gracefully no-op if libs absent."""
    try:
        if rl_qr is None or renderPDF is None:
            return
        widget = rl_qr.QrCodeWidget(str(url))
        bounds = widget.getBounds()
        bw = float(bounds[2] - bounds[0]) or 1.0
        bh = float(bounds[3] - bounds[1]) or 1.0
        scale = min(size / bw, size / bh)
        d = Drawing(size, size)
        d.add(widget)
        d.scale(scale, scale)
        renderPDF.draw(d, canvas, x, y)
        # Clickable link over QR
        canvas.linkURL(
            url if str(url).lower().startswith(("http://", "https://")) else f"https://{url}",
            (x, y, x + size, y + size), relative=0, thickness=0, color=None
        )
    except Exception:
        pass

def _draw_header(canvas: "Canvas", doc, brand: Dict[str, Any], title_text: str):
    canvas.saveState()
    page_w, page_h = canvas._pagesize
    primary = colors.HexColor(_hex(brand.get("primary_color"), "#0B6BF2"))

    # top strip
    strip_h = 10
    canvas.setFillColor(primary)
    canvas.rect(0, page_h - strip_h, page_w, strip_h, fill=1, stroke=0)

    # brand + site
    brand_name = _sanitize_for_font(brand.get("brand_name", "Content365"))
    website_raw = (brand.get("website") or "content365.xyz").strip()
    website = _sanitize_for_font(website_raw)
    site_href = website_raw if website_raw.lower().startswith(("http://", "https://")) else f"https://{website_raw}"

    x = doc.leftMargin
    y = page_h - strip_h - 14

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

    # title (right)
    canvas.setFont(FACE_B, 10.5)
    canvas.setFillColor(colors.HexColor("#111827"))
    right_x = page_w - doc.rightMargin
    canvas.drawRightString(right_x, y, _sanitize_for_font(title_text))

    # logo (optional with fallbacks)
    logo = _img_reader(brand.get("logo_path"))
    if not logo:
        for _candidate in (
            "static/content365_logo.png",
            "static/content365-logo.png",
            "assets/content365_logo.png",
            "assets/content365-logo.png",
            "static/logo.png",
            "assets/logo.png",
        ):
            logo = _img_reader(_candidate)
            if logo:
                break

    if logo:
        try:
            iw, ih = logo.getSize()
            max_h = float(brand.get("logo_max_h", 20))
            s = min(1.0, max_h / float(ih))
            w = float(iw) * s
            h = float(ih) * s
            lx = right_x - w
            ly = y2 - 2
            canvas.drawImage(logo, lx, ly, width=w, height=h, mask="auto")
        except Exception:
            pass

    canvas.restoreState()

def _draw_footer(canvas: Canvas, doc, footer_text: str, brand: Dict[str, Any]):
    if not footer_text:
        return
    footer_text = _sanitize_for_font(footer_text)
    canvas.saveState()
    page_w, _ = canvas._pagesize
    canvas.setStrokeColor(colors.HexColor("#E5E7EB"))
    canvas.line(doc.leftMargin, doc.bottomMargin - 8, page_w - doc.rightMargin, doc.bottomMargin - 8)
    canvas.setFont(FACE, 9)
    canvas.setFillColor(colors.HexColor("#666666"))
    x = doc.leftMargin
    y = doc.bottomMargin - 22
    canvas.drawString(x, y, footer_text)

    # make first URL clickable, if any
    m = re.search(r'(https?://\S+|[A-Za-z0-9.-]+\.[A-Za-z]{2,})', footer_text)
    if m:
        url = m.group(1)
        if not url.lower().startswith(("http://", "https://")):
            url = "https://" + url
        w = canvas.stringWidth(footer_text, FACE, 9)
        canvas.linkURL(url, (x, y-2, x + w, y+10), relative=0, thickness=0, color=None)

    # Page number
    canvas.drawRightString(page_w - doc.rightMargin, y, f"Page {canvas.getPageNumber()}")

    # Optional QR in footer
    try:
        qr_url = (brand or {}).get("qr_url") or (brand or {}).get("website")
        if qr_url:
            size = float((brand or {}).get("qr_size", 0.7*inch))
            qr_x = page_w - doc.rightMargin - size
            qr_y = doc.bottomMargin - size - 2
            _draw_qr(canvas, qr_x, qr_y, size, str(qr_url))
    except Exception:
        pass

    canvas.restoreState()

def _draw_watermark(canvas: Canvas, doc, text: str):
    if not text:
        return
    text = _sanitize_for_font(text)
    canvas.saveState()
    page_w, page_h = canvas._pagesize
    canvas.setFont(FACE_B, 50)
    canvas.setFillColor(colors.HexColor("#EEEEEE"))
    canvas.translate(page_w/2, page_h/2)
    canvas.rotate(30)
    canvas.drawCentredString(0, 0, text)
    canvas.restoreState()

def _draw_debug_grid(canvas: "Canvas", doc):
    canvas.saveState()
    page_w, page_h = canvas._pagesize
    canvas.setStrokeColor(colors.HexColor("#EEEEEE"))
    x0, x1 = doc.leftMargin, page_w - doc.rightMargin
    y0, y1 = doc.bottomMargin, page_h - doc.topMargin
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

# -----------------------------------------------------------------------------
# Flowable builders
# -----------------------------------------------------------------------------
def _make_para(text: str, style: ParagraphStyle) -> Paragraph:
    """
    Safe Paragraph builder: try rich text; on failure, strip tags and retry.
    Prevents 'unclosed tags' crashes from ReportLab's mini-markup.
    """
    try:
        return Paragraph(text, style)
    except Exception:
        try:
            plain = re.sub(r"<[^>]+>", "", text or "")
            return Paragraph(_sanitize_for_font(plain), style)
        except Exception:
            return Paragraph(_sanitize_for_font("[content error]"), style)

def _platform_banner(name: str) -> "Table":
    txt = f"  {name}  "
    tbl = Table([[txt]], colWidths=["*"])
    col = _platform_color(name)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,-1), col),
        ("TEXTCOLOR",   (0,0), (-1,-1), colors.white),
        ("FONTNAME",    (0,0), (-1,-1), FACE_B),
        ("FONTSIZE",    (0,0), (-1,-1), 11.5),
        ("ALIGN",       (0,0), (-1,-1), "LEFT"),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING",(0,0), (-1,-1), 6),
        ("TOPPADDING",  (0,0), (-1,-1), 4),
        ("BOTTOMPADDING",(0,0),(-1,-1), 3),
        ("BOX",         (0,0), (-1,-1), 0.0, col),
    ]))
    return tbl

def _cta_card(text: str, accent_hex: str) -> Table:
    p = _make_para(_auto_link(_sanitize_for_font(_safe_html(text))), CTA)
    box = Table([[p]], colWidths=["*"])
    box.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,-1), colors.HexColor("#F3F6FF")),
        ("BOX",         (0,0), (-1,-1), 1.0, colors.HexColor(accent_hex)),
        ("LEFTPADDING", (0,0), (-1,-1), 10),
        ("RIGHTPADDING",(0,0), (-1,-1), 10),
        ("TOPPADDING",  (0,0), (-1,-1), 8),
        ("BOTTOMPADDING",(0,0), (-1,-1), 8),
    ]))
    return box

def _qr_block(data: str, size: int = 90) -> Optional[Any]:
    try:
        if not data or rl_qr is None or Drawing is object:
            return None
        widget = rl_qr.QrCodeWidget(data)
        b = widget.getBounds()
        w = b[2] - b[0]
        h = b[3] - b[1]
        d = Drawing(size, size, transform=[size / w, 0, 0, size / h, 0, 0])
        d.add(widget)
        return d
    except Exception:
        return None

# -----------------------------------------------------------------------------
# HTML → Flowables
# -----------------------------------------------------------------------------
_IMG_TAG_RE   = re.compile(r'<img\b[^>]*?>', re.I)
_IMG_CLOSE_RE = re.compile(r"</img\s*>", re.I)

# Normalize stray <p> wrappers that confuse ReportLab's mini-markup parser
_PARA_OPEN_RE  = re.compile(r'^\s*<p[^>]*>\s*', re.I)
_PARA_CLOSE_RE = re.compile(r'\s*</p>\s*$', re.I)

def _strip_p_wrappers(s: str) -> str:
    if not s:
        return s
    s = _PARA_OPEN_RE.sub('', s)
    s = _PARA_CLOSE_RE.sub('', s)
    return s

# Normalize to clean blocks for Paragraphs
_PTAG_OPEN_RE  = re.compile(r'<\s*p[^>]*>', re.I)
_PTAG_CLOSE_RE = re.compile(r'</\s*p\s*>', re.I)
_BR_RE         = re.compile(r'<\s*br\s*/?\s*>', re.I)

def _normalize_blocks(html: str) -> str:
    """Flatten paragraph markup to plain blocks and collapse whitespace."""
    if not html:
        return ""
    s = _safe_html(html)
    s = _BR_RE.sub("\n", s)
    s = _PTAG_OPEN_RE.sub("", s)
    s = _PTAG_CLOSE_RE.sub("\n\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def _extract_images(html: str) -> Tuple[str, List[Tuple[str, Optional[str]]]]:
    """Return (html_without_img_tags, [(path, alt)]). Only local/relative paths kept."""
    pairs: List[Tuple[str, Optional[str]]] = []

    def _repl(m):
        tag = m.group(0)
        src_m = re.search(r'src=(?:"|\')([^"\']+)(?:"|\')', tag, flags=re.I)
        alt_m = re.search(r'alt=(?:"|\')([^"\']*)(?:"|\')', tag, flags=re.I)
        if src_m:
            src = src_m.group(1)
            if src and not src.lower().startswith(("http://", "https://", "data:")):
                alt = alt_m.group(1) if alt_m else None
                pairs.append((src, alt))
        return ""  # remove the <img ...> tag entirely

    html2 = _IMG_TAG_RE.sub(_repl, html or "")
    html2 = _IMG_CLOSE_RE.sub("", html2)
    return html2, pairs

def _paragraphs_from_html(fragment: str) -> List[Any]:
    normalized = _normalize_blocks(fragment)  # handles <p>, </p>, <br>
    chunks = [c.strip() for c in re.split(r"\n{2,}", normalized) if c.strip()]
    return [_make_para(_auto_link(_sanitize_for_font(c)), BODY) for c in chunks]

def _list_from_html(list_html: str) -> Optional[ListFlowable]:
    is_ordered = bool(re.match(r"\s*<ol", list_html, flags=re.I))
    items = re.findall(r"<li[^>]*>(.*?)</li>", list_html, flags=re.I | re.S)
    if not items:
        return None
    list_items = [ListItem(_make_para(_sanitize_for_font(_safe_html(i)), BODY), leftIndent=6) for i in items]
    return ListFlowable(list_items, bulletType=("1" if is_ordered else "bullet"), leftIndent=10)

def _make_image_flowable(p: Path, max_img_w: float) -> Optional[RLImage]:
    """Create a robust RLImage, fixing broken images with PIL; returns None on failure."""
    img = None
    if Image is not None:
        try:
            with Image.open(str(p)) as im:
                im.load()
                if im.mode not in ("RGB", "RGBA"):
                    im = im.convert("RGB")
                buf = io.BytesIO()
                im.save(buf, format="PNG")
                buf.seek(0)
                img = RLImage(buf)
        except Exception:
            img = None

    if img is None:
        try:
            img = RLImage(str(p))
        except Exception:
            return None

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

    # images at the end (each as block)
    for pth, alt in imgs:
        try:
            img_path = Path(pth)
            if not img_path.exists():
                msg = f'[missing image: {pth}]' if not alt else f'[missing image: {pth} — {alt}]'
                flows.append(_make_para(_sanitize_for_font(f'<font color="#888888">{msg}</font>'), SMALL))
                continue

            img = _make_image_flowable(img_path, max_img_w)
            if img is not None:
                flows.append(Spacer(1, 6))
                flows.append(img)
                # optional centered caption
                if alt and alt.strip():
                    flows.append(Spacer(1, 2))
                    flows.append(_make_para(_sanitize_for_font(alt.strip()), CAPTION))
                flows.append(Spacer(1, 4))
            else:
                msg = f'[unreadable image: {pth}]' if not alt else f'[unreadable image: {pth} — {alt}]'
                flows.append(_make_para(_sanitize_for_font(f'<font color="#888888">{msg}</font>'), SMALL))
        except Exception:
            msg = f'[image error: {pth}]' if not alt else f'[image error: {pth} — {alt}]'
            flows.append(_make_para(_sanitize_for_font(f'<font color="#888888">{msg}</font>'), SMALL))
            continue
    return flows

# -----------------------------------------------------------------------------
# Main export (premium)
# -----------------------------------------------------------------------------
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

    watermark_text = payload.get("watermark") or ""  # optional
    debug_grid     = bool(payload.get("debug_grid"))

    primary = colors.HexColor(_hex(brand.get("primary_color"), "#0B6BF2"))
    accent  = _hex(brand.get("accent_color"),  "#0B6BF2")

    doc = SimpleDocTemplate(
        str(final_path), pagesize=LETTER,
        leftMargin=0.8*inch, rightMargin=0.8*inch, topMargin=0.9*inch, bottomMargin=0.9*inch,
        title=_sanitize_for_font(title), author="Content365", subject="Marketing Content Pack", creator="Content365 PDF Engine",
    )

    story: List[Any] = []

    # Title block
    story.append(Spacer(1, 6))
    story.append(KeepTogether([_make_para(_sanitize_for_font(title), TITLE)]))
    if subtitle:
        story.append(_make_para(_sanitize_for_font(subtitle), SUB))

    # Prepared-for subline (brand-aware)
    _bf_name = _sanitize_for_font(brand.get("brand_name", "Content365"))
    _bf_site = _sanitize_for_font(brand.get("website", "content365.xyz"))
    story.append(_make_para(f"Prepared for: <b>{_bf_name}</b> · {_bf_site}", SMALL))
    story.append(Spacer(1, 2))
    story.append(HRFlowable(width="100%", color=primary, thickness=1.2, spaceBefore=6, spaceAfter=10))

    # Body (with images/lists)
    if blog_html:
        story.extend(_html_to_flowables(blog_html, max_img_w=doc.width))

    # Bullets (explicit field)
    if bullets:
        items: List[ListItem] = []
        for b in bullets:
            items.append(ListItem(_make_para(_sanitize_for_font(_safe_html(str(b))), BODY), leftIndent=6))

        lst = ListFlowable(
            items,
            bulletType="bullet",
            bulletChar="•",
            leftIndent=10
        )
        story.append(lst)
        story.append(Spacer(1, 4))

    # CTA
    if cta_text:
        story.append(Spacer(1, 4))
        story.append(_cta_card(cta_text, accent))

    # Optional QR block in body (separate from footer QR)
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

            story.append(_platform_banner(_sanitize_for_font(name)))
            story.append(Spacer(1, 4))

            if caption:
                story.append(_make_para(_auto_link(_sanitize_for_font(_safe_html(caption))), BODY))

            if hashtags:
                tag_line = " ".join(
                    (h.strip() if h.strip().startswith("#") else f"#{h.strip()}")
                    for h in hashtags
                    if isinstance(h, str) and h.strip()
                )
                if tag_line:
                    story.append(_make_para(_sanitize_for_font(tag_line), TAGS))
                    story.append(Spacer(1, 4))

            story.append(Spacer(1, 6))

    # Page callbacks
    def _on_page(c: Canvas, d):
        if debug_grid:
            _draw_debug_grid(c, d)
        _draw_watermark(c, d, watermark_text)
        _draw_header(c, d, brand, "Content365 · Marketing Pack")
        _draw_footer(c, d, footer, brand)

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
# Tiny pure-Python fallback (no external deps)
# -----------------------------------------------------------------------------
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
            f.write(b"startxref\n")
            f.write(f"{xref_pos}\n".encode("ascii"))
            f.write(b"%%EOF")

def _generate_pdf_fallback(payload: Dict[str, Any], output_path: str, brand: Dict[str, Any]) -> str:
    """Minimal dependency-free PDF if premium engine fails."""
    lines: List[str] = []
    title = payload.get("title") or (payload.get("blog", {}) or {}).get("headline") or "Content365 Pack"
    lines += [_sanitize_for_font(title.upper()), ""]
    intro = (payload.get("blog", {}) or {}).get("intro") or ""
    if intro: lines += [_sanitize_for_font(intro), ""]
    for p in (payload.get("blog", {}) or {}).get("body") or []:
        lines += [_sanitize_for_font(str(p)), ""]
    for b in payload.get("bullets", []) or (payload.get("blog", {}) or {}).get("bullets") or []:
        lines.append(_sanitize_for_font(f"- {b}"))
    cta = payload.get("cta_text") or (payload.get("blog", {}) or {}).get("cta") or ""
    if cta: lines += ["", _sanitize_for_font(cta)]
    # social
    social = payload.get("social") or []
    platforms = payload.get("platforms") or {}
    if not social and platforms:
        for name, data in platforms.items():
            social.append({"name": name, "caption": data.get("caption",""), "hashtags": data.get("hashtags",[])})
    if social:
        lines += ["", "SOCIAL CAPTIONS:"]
        for s in social:
            lines.append(_sanitize_for_font(f"{s.get('name', 'Platform')}: {s.get('caption','')}"))
            hts = s.get("hashtags") or []
            if hts: lines.append(_sanitize_for_font("  " + " ".join(str(h) for h in hts)))
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
        newp = dict(payload)
    else:
        blog = payload.get("blog") or {}
        title = blog.get("headline") or blog.get("title") or payload.get("title") or "Content365 Pack"
        subtitle = payload.get("subtitle") or ""
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
            for plat, cap in captions.items():
                text = cap.get("text") if isinstance(cap, dict) else str(cap or "")
                hts = hashtags.get(plat) or []
                social.append({"name": plat, "caption": text, "hashtags": hts})
        elif platforms:
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
    accent     = str(_cfg.get("accent_color")  or "#0B6BF2").strip() or "#0B6BF2"

    newp["brand"] = {
        "brand_name":    brand_name,
        "website":       website,
        "logo_path":     logo_path,
        "logo_max_h":    logo_max_h,
        "primary_color": primary,
        "accent_color":  accent,
        "qr_url":        _cfg.get("qr_url"),
        "qr_size":       _cfg.get("qr_size", 0.7*inch),
    }

    if "footer" not in newp:
        newp["footer"] = payload.get("footer") or f"© {datetime.now().year} {newp['brand']['brand_name']} · {newp['brand']['website']}"

    return newp

# -----------------------------------------------------------------------------
# Compatibility wrapper for main.py + graceful fallback
# -----------------------------------------------------------------------------
def generate_pdf(payload: Dict[str, Any], output_path: str, brand_config: Optional[Dict[str, Any]] = None) -> str:
    """
    Entry point expected by main.py.
    - Adapts legacy payloads to the premium shape.
    - Uses premium ReportLab engine when available; otherwise uses the tiny pure-Python fallback.
    - Writes exactly to `output_path`.
    """
    _g = globals()
    adapt    = _g.get("_adapt_payload_legacy")
    export   = _g.get("export_pdf_response")
    fallback = _g.get("_generate_pdf_fallback")

    if not (callable(adapt) and callable(fallback)):
        raise RuntimeError(
            "Internal wiring error: missing helpers — "
            f"adapt={bool(callable(adapt))}, fallback={bool(callable(fallback))}"
        )

    output_path = str(output_path)
    out_dir = str(Path(output_path).parent or "generated_pdfs")

    # Normalize payload to the premium/new shape (works for legacy too)
    premium_payload = adapt(payload or {}, brand_config or {})

    # If ReportLab isn't actually available, skip premium entirely.
    if not globals().get("_HAS_REPORTLAB", False):
        return fallback(payload or {}, output_path, premium_payload.get("brand", {}))

    # Premium path: build to a temp file in out_dir, then move to the exact requested path.
    if not callable(export):
        # Defensive: if export isn't callable for some reason, drop to fallback.
        return fallback(payload or {}, output_path, premium_payload.get("brand", {}))

    try:
        tmp_path = export(premium_payload, out_dir=out_dir)
        if os.path.abspath(tmp_path) != os.path.abspath(output_path):
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            shutil.move(tmp_path, output_path)
        return output_path
    except Exception:
        # Any premium failure gracefully falls back to the minimal writer.
        return fallback(payload or {}, output_path, premium_payload.get("brand", {}))

__all__ = ["export_pdf_response", "generate_pdf"]

if __name__ == "__main__":  # lightweight self-test harness
    import sys, json, argparse, subprocess
    from pathlib import Path

    def _placeholders():
        """Create tiny placeholder logo/sample image if missing."""
        static = Path("static"); static.mkdir(exist_ok=True)
        logo = static / "logo.png"
        sample = static / "sample.jpg"
        if not logo.exists():
            import base64
            logo.write_bytes(base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMB/XSF3d0AAAAASUVORK5CYII="
            ))
        if not sample.exists():
            import base64
            sample.write_bytes(base64.b64decode(
                "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABALCwsLCxAQEBAQFBEUFRUVGBgYGBweHh4eHiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiL/2wBDARESEhISEhQVFBUaGhocHBwcIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiL/wAARCAAQABADASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAb/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAwT/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCPgA//2Q=="
            ))

    def _run_premium(out_dir: Path):
        """Generate a premium PDF via export_pdf_response and the compat wrapper."""
        _placeholders()
        payload = {
            "title": "Premium OK",
            "subtitle": "Self-test (premium)",
            "blog_html": """<p>Hello <b>premium</b></p><p><img src="static/sample.jpg" alt="Sample"/></p>""",
            "cta_text": "https://content365.xyz",
            "social": [{"name":"LinkedIn","caption":"Launching today","hashtags":["AI","SaaS"]}],
            "footer": "© 2025 Content365 · content365.xyz",
            "brand": {
                "brand_name": "Content365",
                "website": "content365.xyz",
                "logo_path": "static/logo.png",
                "logo_max_h": 22,
                "primary_color": "#0B6BF2",
                "accent_color": "#0B6BF2",
                "qr_url": "https://content365.xyz",
                "qr_size": 50,
            },
        }
        out_dir.mkdir(parents=True, exist_ok=True)
        p1 = export_pdf_response(payload, out_dir=str(out_dir))
        dest = out_dir / "compat_test.pdf"
        p2 = generate_pdf(payload, str(dest))
        print("Premium export OK  ->", p1)
        print("Compat wrapper OK ->", p2)

    def _run_fallback(out_dir: Path):
        """Simulate missing ReportLab in a child process to exercise tiny fallback writer."""
        legacy_payload = {
            "blog": {"headline": "LEGACY FALLBACK", "body": ["Line A", "Line B"]},
            "footer": "© 2025 Content365 · content365.xyz",
            "brand": {"brand_name": "Content365", "website": "content365.xyz"},
        }
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = (out_dir / "fallback_test.pdf").resolve()

        # Child script: poison 'reportlab' import, then import our module and run generate_pdf
        child_code = r"""
import sys, types, json
from pathlib import Path
sys.modules['reportlab'] = types.ModuleType('reportlab')  # force fallback path
from utils.pdf_generator import generate_pdf
payload = json.loads(sys.argv[1])
out = generate_pdf(payload, sys.argv[2])
print(out)
"""
        proc = subprocess.run(
            [sys.executable, "-c", child_code, json.dumps(legacy_payload), str(dest)],
            cwd=str(Path.cwd()),
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            print(proc.stdout)
            print(proc.stderr, file=sys.stderr)
            raise SystemExit(proc.returncode)
        print("Fallback writer OK ->", proc.stdout.strip())

    parser = argparse.ArgumentParser(description="Content365 PDF self-test harness")
    parser.add_argument("--premium", action="store_true", help="Run only the premium (ReportLab) test")
    parser.add_argument("--fallback", action="store_true", help="Run only the tiny fallback test")
    parser.add_argument("--outdir", default="generated_pdfs", help="Output directory (default: generated_pdfs)")
    args = parser.parse_args()

    out_dir = Path(args.outdir)

    if args.premium and args.fallback:
        _run_premium(out_dir)
        _run_fallback(out_dir)
    elif args.premium:
        _run_premium(out_dir)
    elif args.fallback:
        _run_fallback(out_dir)
    else:
        # default: run both
        _run_premium(out_dir)
        _run_fallback(out_dir)
