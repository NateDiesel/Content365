# utils/pdf_generator.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import re
from typing import Dict, Any, List, Optional, Tuple

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, Flowable, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.utils import ImageReader

# =============================================================================
# Safe logo loader (prevents layout explosions)
# =============================================================================
def _safe_logo_image(path: str, max_px: int = 48):
    """
    Load a logo image and hard-clamp its draw size so it can never blow up layout.
    Returns a ReportLab Image or None.
    """
    if not path or not os.path.exists(path):
        return None
    try:
        _ = ImageReader(path)  # force-parse to validate
        img = Image(path)
        img.drawWidth = max_px
        img.drawHeight = max_px
        if hasattr(img, "_restrictSize"):
            img._restrictSize(max_px, max_px)
        img.hAlign = "LEFT"
        return img
    except Exception:
        return None

# =============================================================================
# Font registration (DejaVu with safe fallbacks)
# =============================================================================
_FONT_REG_DONE = False
_BASE_FONT = "Helvetica"         # Fallbacks if DejaVu not found
_BASE_FONT_BOLD = "Helvetica-Bold"

def _try_register_ttf(name: str, path_candidates: List[str]) -> Optional[str]:
    """
    Attempt to register a TTF font, ignoring corrupt/empty files.
    Returns the font name on success, else None.
    """
    for p in path_candidates:
        try:
            if not p:
                continue
            if not os.path.exists(p):
                continue
            # Extremely common failure case: 0-byte or tiny file masquerading as TTF
            if os.path.getsize(p) < 1024:  # <1 KB is never a real TTF
                continue
            pdfmetrics.registerFont(TTFont(name, p))
            return name
        except Exception:
            continue
    return None

def _register_fonts_once():
    """
    Try to register DejaVuSans / DejaVuSans-Bold if present & valid. Otherwise,
    keep Helvetica/Helvetica-Bold so we never crash. Idempotent.
    """
    global _FONT_REG_DONE, _BASE_FONT, _BASE_FONT_BOLD
    if _FONT_REG_DONE:
        return

    dvn = _try_register_ttf("DejaVuSans", [
        "assets/fonts/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/DejaVuSans.ttf",
        "C:/Windows/Fonts/DejaVuSans.ttf",
    ])
    dvb = _try_register_ttf("DejaVuSans-Bold", [
        "assets/fonts/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/Library/Fonts/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/DejaVuSans-Bold.ttf",
    ])

    if dvn and dvb:
        _BASE_FONT = "DejaVuSans"
        _BASE_FONT_BOLD = "DejaVuSans-Bold"

    _FONT_REG_DONE = True

# =============================================================================
# Helpers
# =============================================================================
PLATFORM_ORDER = ["Instagram", "LinkedIn", "TikTok", "Twitter", "Facebook"]

PLATFORM_COLORS: Dict[str, colors.Color] = {
    "Instagram": colors.Color(0.91, 0.33, 0.48),   # pinkish
    "LinkedIn":  colors.Color(0.00, 0.44, 0.71),
    "TikTok":    colors.Color(0.10, 0.10, 0.10),
    "Twitter":   colors.Color(0.11, 0.63, 0.95),
    "Facebook":  colors.Color(0.23, 0.35, 0.60),
}

def _norm_platform(p: str) -> str:
    """
    Normalize user/platform keys:
    - "x" -> "Twitter" (we keep 'twitter.png' assets)
    - Case normalize to Title
    """
    if not p:
        return p
    pl = p.strip()
    if pl.lower() in {"x", "twitter"}:
        return "Twitter"
    return pl[:1].upper() + pl[1:].lower()

def _icon_path(platform: str) -> Optional[str]:
    base = "assets/icons"
    candidates = [
        os.path.join(base, f"{platform.lower()}.png"),
        os.path.join(base, f"{platform.capitalize()}.png"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None

# --- Hashtag helpers (dedupe + extract inline) ---
_TAG_RX = re.compile(r"(?:#|\uFF03)([A-Za-z0-9_]+)")

def _extract_tags_from_text(text: str) -> List[str]:
    return [m.lower() for m in _TAG_RX.findall(text or "")]

def _dedupe_preserve(seq: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for t in seq:
        key = str(t).lstrip("#").strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(t)
    return out

def _hashline(tags: List[str]) -> str:
    # Render as #tag1 #tag2 … (deduped, preserved order)
    deduped = _dedupe_preserve(tags)
    cleaned = [f"#{str(t).lstrip('#').strip()}" for t in deduped if str(t).strip()]
    return " ".join(cleaned)

def _safe_text(x: Any) -> str:
    return "" if x is None else str(x)

# --- Emoji sanitization (prevents � boxes) ---
# Common emoji → short text replacements
_EMOJI_MAP = {
    "💡": "(tip)", "🚀": "(launch)", "✅": "(done)", "🔥": "(hot)", "🎯": "(goal)",
    "📣": "(announce)", "📈": "(growth)", "👇": "(below)", "🔗": "(link)", "✨": "*",
    "🧠": "(insight)", "⚡": "(fast)", "❓": "?", "⭐": "*", "🔍": "(search)",
}
# Broad emoji ranges (BMP symbols + Supplemental)
_EMOJI_RX = re.compile(
    r"[\U0001F000-\U0001FAFF\U00002600-\U000026FF\U00002700-\U000027BF]",
    flags=re.UNICODE
)

def _emoji_to_text(s: str) -> str:
    if not s:
        return ""
    # Replace known emojis, leave others for the regex to strip
    return "".join(_EMOJI_MAP.get(ch, ch) for ch in s)

def _sanitize_for_pdf(s: str) -> str:
    """
    Replace common emojis with text and strip the rest so ReportLab never draws �.
    Also normalize NBSP to regular space.
    """
    t = (s or "").replace("\u00A0", " ")
    t = _emoji_to_text(t)
    t = _EMOJI_RX.sub("", t)
    return t

# --- Auto-link (URLs + emails) ---
_LINK_RX = re.compile(
    r'((?:https?://|www\.)\S+|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})'
)

def _autolink(text: str) -> str:
    def _wrap(m):
        s = m.group(1)
        href = s
        if s.startswith('www.'):
            href = 'https://' + s
        if '@' in s and not s.startswith(('http://', 'https://', 'www.')):
            href = 'mailto:' + s
        return f'<a href="{href}">{s}</a>'
    return _LINK_RX.sub(_wrap, text or '')

# =============================================================================
# Custom Flowables
# =============================================================================
class PlatformBanner(Flowable):
    """
    Colored rounded bar with platform icon (no large text).
    """
    def __init__(self, platform: str, width: float, height: float = 28):
        super().__init__()
        self.platform = platform
        self.width = width
        self.height = height

    def wrap(self, availWidth, availHeight):
        return (self.width, self.height)

    def draw(self):
        plat = _norm_platform(self.platform)
        bar_color = PLATFORM_COLORS.get(plat, colors.HexColor("#444"))
        c = self.canv
        x, y, w, h = 0, 0, self.width, self.height
        r = 9

        # bar
        c.setFillColor(bar_color)
        c.setStrokeColor(bar_color)
        c.roundRect(x, y, w, h, r, stroke=0, fill=1)

        # icon
        icon_path = _icon_path(plat)
        if icon_path:
            try:
                pad = 6
                size = h - 2 * pad  # square icon
                c.drawImage(icon_path, x + pad, y + pad, width=size, height=size,
                            preserveAspectRatio=True, mask='auto')
            except Exception:
                self._draw_fallback_icon(c, x, y, h)
        else:
            self._draw_fallback_icon(c, x, y, h)

    def _draw_fallback_icon(self, canvas: Canvas, x: float, y: float, h: float):
        canvas.setFillColor(colors.white)
        canvas.circle(x + h/2, y + h/2, h*0.32, stroke=0, fill=1)
        canvas.setFillColor(colors.black)
        canvas.setFont(_BASE_FONT_BOLD, 10)
        canvas.drawCentredString(x + h/2, y + h/2 - 3, (self.platform or "?")[:1].upper())

class CTACard(Flowable):
    """
    Rounded highlight card for CTA line.
    """
    def __init__(self, text: str, width: float, style: ParagraphStyle):
        super().__init__()
        self.text = text
        self.width = width
        self.style = style
        self._para = Paragraph(text, style)
        self.content_height = 0

    def wrap(self, availWidth, availHeight):
        w, h = self._para.wrap(self.width - 16, availHeight)
        self.content_height = h
        return (self.width, h + 16)

    def draw(self):
        c = self.canv
        w, h = self.width, self.content_height + 16
        r = 8
        c.setFillColor(colors.Color(0.97, 0.98, 1.0))
        c.setStrokeColor(colors.Color(0.75, 0.83, 0.95))
        c.roundRect(0, 0, w, h, r, stroke=1, fill=1)
        c.saveState()
        c.translate(8, 8)
        self._para.drawOn(c, 0, 0)
        c.restoreState()

# =============================================================================
# Styles
# =============================================================================
def _build_styles(brand_color: Tuple[float, float, float]) -> Dict[str, ParagraphStyle]:
    _register_fonts_once()
    base = getSampleStyleSheet()

    styles = {
        "H1": ParagraphStyle(
            "H1", parent=base["Heading1"], fontName=_BASE_FONT_BOLD, fontSize=20, leading=24,
            textColor=colors.black, spaceAfter=10
        ),
        "H2": ParagraphStyle(
            "H2", parent=base["Heading2"], fontName=_BASE_FONT_BOLD, fontSize=14, leading=18,
            textColor=colors.black, spaceBefore=12, spaceAfter=6
        ),
        "P": ParagraphStyle(
            "P", parent=base["BodyText"], fontName=_BASE_FONT, fontSize=11.2, leading=15.2,
            textColor=colors.black, spaceAfter=6
        ),
        "Bullet": ParagraphStyle(
            "Bullet", parent=base["BodyText"], fontName=_BASE_FONT, fontSize=11.2, leading=15.2,
            leftIndent=14, bulletIndent=4, spaceBefore=0, spaceAfter=4
        ),
        "Caption": ParagraphStyle(
            "Caption", parent=base["BodyText"], fontName=_BASE_FONT, fontSize=11.5, leading=15.5,
            textColor=colors.black, spaceBefore=6, spaceAfter=4
        ),
        "Hashtags": ParagraphStyle(
            "Hashtags", parent=base["BodyText"], fontName=_BASE_FONT, fontSize=9.7, leading=13.3,
            textColor=colors.Color(0.25, 0.25, 0.28), spaceAfter=10
        ),
        "CTA": ParagraphStyle(
            "CTA", parent=base["BodyText"], fontName=_BASE_FONT_BOLD, fontSize=11.5, leading=14.5,
            textColor=colors.Color(*brand_color)
        ),
        "Small": ParagraphStyle(
            "Small", parent=base["BodyText"], fontName=_BASE_FONT, fontSize=8.8, leading=11.5,
            textColor=colors.Color(0.28, 0.28, 0.3)
        ),
        "Brand": ParagraphStyle(
            "Brand", parent=base["Heading2"], fontName=_BASE_FONT_BOLD, fontSize=13.5, leading=16,
            textColor=colors.black
        ),
        "BrandSub": ParagraphStyle(
            "BrandSub", parent=base["BodyText"], fontName=_BASE_FONT, fontSize=9.7, leading=12.5,
            textColor=colors.Color(0, 0, 0, 0.6)
        ),
    }
    return styles

# =============================================================================
# Header/Footer
# =============================================================================
def _header_table(brand_config: Dict[str, Any], styles: Dict[str, ParagraphStyle], width: float):
    logo_path = brand_config.get("logo_path") or ""
    brand_name = brand_config.get("brand_name", "Content365")
    website = (brand_config.get("website") or "content365.xyz").strip()
    # ensure clickable and not a bare "127.0.0.1"
    if website and not website.startswith(("http://", "https://")):
        website_href = "https://" + website
    else:
        website_href = website

    # Left cell: logo (hard-clamped). If missing, keep layout with a tiny spacer.
    logo_img = _safe_logo_image(logo_path, max_px=48) or Spacer(0.01, 0.01)

    # Right cell: 2-row inner table (name on top, site below)
    name_para = Paragraph(brand_name, styles["Brand"])
    site_para = Paragraph(f'<a href="{website_href}">{website}</a>', styles["BrandSub"])

    right_tbl = Table(
        [[name_para],
         [site_para]],
        colWidths=[width - 0.6 * inch]
    )
    right_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    # Outer header table: fixed row height to prevent layout explosions
    data = [[logo_img, right_tbl]]
    col_widths = [0.6 * inch, width - 0.6 * inch]

    tbl = Table(data, colWidths=col_widths, rowHeights=[0.6 * inch], hAlign="LEFT")
    tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return tbl

def _footer(canvas: Canvas, doc, brand_config: Dict[str, Any]):
    footer_text = brand_config.get("footer_text", "")
    canvas.saveState()
    canvas.setFont(_BASE_FONT, 8.5)
    canvas.setFillColor(colors.Color(0, 0, 0, 0.55))
    x = doc.leftMargin
    y = 0.5 * inch
    if footer_text:
        canvas.drawString(x, y, footer_text)
    canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, y, f"Page {doc.page}")
    canvas.restoreState()

# =============================================================================
# Main builder
# =============================================================================
def generate_pdf(payload: Dict[str, Any], output_path: str, brand_config: Optional[Dict[str, Any]] = None):
    """
    payload schema (normalized by main.py):
      {
        "blog": {"headline": str, "intro": str, "body": [str], "bullets": [str], "cta": str},
        "captions": {PlatformName: str|{"text": str, ...}},
        "hashtags": {PlatformName: [str]}
      }
    """
    brand_config = brand_config or {}
    brand_color = brand_config.get("primary_color", (0.12, 0.46, 0.95))

    _register_fonts_once()
    styles = _build_styles(brand_color)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title=brand_config.get("brand_name", "Content365")
    )

    story: List[Any] = []

    # Header
    story.append(_header_table(brand_config, styles, doc.width))
    story.append(Spacer(1, 10))

    # --- Blog section ---
    blog = payload.get("blog") or {}
    headline = _sanitize_for_pdf(_safe_text(blog.get("headline") or "Your Content Pack"))
    intro = _safe_text(blog.get("intro"))
    body_list = blog.get("body") or []
    bullets = blog.get("bullets") or []
    cta = _safe_text(blog.get("cta"))

    story.append(Paragraph(headline, styles["H1"]))
    if intro:
        story.append(Paragraph(_autolink(_sanitize_for_pdf(intro)), styles["P"]))
        story.append(Spacer(1, 2))
    if body_list:
        for p in body_list:
            s = _safe_text(p)
            if s:
                story.append(Paragraph(_autolink(_sanitize_for_pdf(s)), styles["P"]))
        story.append(Spacer(1, 2))
    if bullets:
        for b in bullets:
            s = _safe_text(b)
            story.append(Paragraph("• " + _autolink(_sanitize_for_pdf(s)), styles["Bullet"]))
        story.append(Spacer(1, 2))
    if cta:
        story.append(CTACard(_autolink(_sanitize_for_pdf(cta)), doc.width, styles["CTA"]))
        story.append(Spacer(1, 12))

    # Divider
    story.append(_thin_divider(doc.width))
    story.append(Spacer(1, 6))

    # --- Social sections ---
    captions = payload.get("captions") or {}
    hashtags = payload.get("hashtags") or {}

    # Normalize keys and preserve input order preference
    platforms_seen: List[str] = []
    for k in captions.keys():
        platforms_seen.append(_norm_platform(k))

    # Merge with preferred order
    ordered = [p for p in PLATFORM_ORDER if p in platforms_seen] + \
              [p for p in platforms_seen if p not in PLATFORM_ORDER]

    for plat in ordered:
        cap_block = captions.get(plat) or captions.get(plat.lower()) or captions.get(plat.upper()) or {}
        tag_list = hashtags.get(plat) or hashtags.get(plat.lower()) or hashtags.get(plat.upper()) or []

        story += _platform_block(
            plat,
            cap_block,
            tag_list,
            styles,
            doc.width
        )
        story.append(Spacer(1, 10))

    # Build
    def _on_page(canvas: Canvas, doc_obj):
        # Light metadata; harmless if repeated, but we can do it once on page 1
        try:
            if getattr(doc_obj, "page", 0) == 1:
                canvas.setAuthor(brand_config.get("brand_name", "Content365"))
                canvas.setTitle(headline)
                canvas.setSubject("Social content pack")
        except Exception:
            pass
        _footer(canvas, doc_obj, brand_config)

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)

# =============================================================================
# Pieces
# =============================================================================
def _thin_divider(width: float) -> Table:
    t = Table([[""]], colWidths=[width], rowHeights=[0.6])
    t.setStyle(TableStyle([
        ("LINEBEFORE", (0, 0), (-1, -1), 0, colors.white),
        ("LINEAFTER",  (0, 0), (-1, -1), 0, colors.white),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("BACKGROUND", (0, 0), (-1, -1), colors.Color(0, 0, 0, 0.08)),
    ]))
    return t

def _platform_block(platform: str, caption_block: Any, tag_list: List[str],
                    styles: Dict[str, ParagraphStyle], width: float) -> List[Any]:
    plat = _norm_platform(platform)
    parts: List[Any] = []

    # Banner with icon (no big label)
    parts.append(PlatformBanner(plat, width, height=28))
    parts.append(Spacer(1, 4))

    # Caption text (string or dict with 'text' key)
    if isinstance(caption_block, dict):
        text = caption_block.get("text") or caption_block.get("caption") or ""
    else:
        text = caption_block or ""
    text = _sanitize_for_pdf(_safe_text(text))

    # Remove hashtags already present inline in caption
    inline = set(_extract_tags_from_text(text))
    filtered_tags = [t for t in (tag_list or []) if t and t.lstrip("#").strip().lower() not in inline]

    if text:
        parts.append(Paragraph(_autolink(text), styles["Caption"]))

    # Hashtags
    if filtered_tags:
        parts.append(Paragraph(_hashline(filtered_tags), styles["Hashtags"]))

    return parts
