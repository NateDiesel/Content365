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
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, Flowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.utils import ImageReader

# =============================================================================
# Configuration
# =============================================================================
LOGO_MAX_W = 56   # points
LOGO_MAX_H = 56   # points
HEADER_GUTTER = 10  # space between logo and title block

PLATFORM_ORDER = ["Instagram", "LinkedIn", "TikTok", "Twitter", "Facebook"]

PLATFORM_COLORS: Dict[str, colors.Color] = {
    "Instagram": colors.Color(0.91, 0.33, 0.48),
    "LinkedIn":  colors.Color(0.00, 0.44, 0.71),
    "TikTok":    colors.Color(0.10, 0.10, 0.10),
    "Twitter":   colors.Color(0.11, 0.63, 0.95),
    "Facebook":  colors.Color(0.23, 0.35, 0.60),
}

# =============================================================================
# Safe logo loader (prevents layout explosions)
# =============================================================================
def _safe_logo_image(path: str, max_w: int = LOGO_MAX_W, max_h: int = LOGO_MAX_H) -> Optional[Image]:
    if not path or not os.path.exists(path):
        return None
    try:
        reader = ImageReader(path)
        iw, ih = reader.getSize()
        if not iw or not ih:
            return None
        scale = min(max_w / float(iw), max_h / float(ih), 1.0)
        dw, dh = iw * scale, ih * scale
        img = Image(path, width=dw, height=dh, mask='auto')
        img.hAlign = "LEFT"
        return img
    except Exception:
        return None

def _resolve_logo_path(p: str) -> Optional[str]:
    if p and os.path.isabs(p) and os.path.exists(p):
        return p
    for c in [p or "", "assets/logo.png", "static/logo.png",
              os.path.join(os.getcwd(), "assets", "logo.png"),
              os.path.join(os.getcwd(), "static", "logo.png")]:
        if c and os.path.exists(c):
            return c
    return None

# =============================================================================
# Font registration (DejaVu with safe fallbacks)
# =============================================================================
_FONT_REG_DONE = False
_BASE_FONT = "Helvetica"
_BASE_FONT_BOLD = "Helvetica-Bold"

def _try_register_ttf(name: str, path_candidates: List[str]) -> Optional[str]:
    for p in path_candidates:
        try:
            if not p or not os.path.exists(p):
                continue
            if os.path.getsize(p) < 1024:
                continue
            pdfmetrics.registerFont(TTFont(name, p))
            return name
        except Exception:
            continue
    return None

def _register_fonts_once():
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
# Helpers (platforms, links, hashtags, emoji)
# =============================================================================
def _norm_platform(p: str) -> str:
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
            out.append(key)
    return out

def _hashline(tags: List[str]) -> str:
    deduped = _dedupe_preserve(tags)
    cleaned = [f"#{str(t).lstrip('#').strip()}" for t in deduped if str(t).strip()]
    return " ".join(cleaned)

def _safe_text(x: Any) -> str:
    return "" if x is None else str(x)

# Emoji sanitization (map common emoji to safe text, strip the rest)
_EMOJI_MAP = {
    "💡": "(tip)", "🚀": "(launch)", "✅": "(done)", "🔥": "(hot)", "🎯": "(goal)",
    "📣": "(announce)", "📈": "(growth)", "👇": "(below)", "🔗": "(link)", "✨": "*",
    "🧠": "(insight)", "⚡": "(fast)", "❓": "?", "⭐": "*", "🔍": "(search)",
}
_EMOJI_RX = re.compile(
    r"[\U0001F000-\U0001FAFF\U00002600-\U000026FF\U00002700-\U000027BF]",
    flags=re.UNICODE
)

def _emoji_to_text(s: str) -> str:
    if not s:
        return ""
    return "".join(_EMOJI_MAP.get(ch, ch) for ch in s)

def _sanitize_for_pdf(s: str) -> str:
    t = (s or "").replace("\u00A0", " ")
    t = _emoji_to_text(t)
    t = _EMOJI_RX.sub("", t)
    return t

_LINK_RX = re.compile(r'((?:https?://|www\.)\S+|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})')

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

_INLINE_TAG_RX = re.compile(r'(?:#|\uFF03)[A-Za-z0-9_]+')

def _strip_inline_hashtags(text: str) -> str:
    if not text:
        return ""
    t = _INLINE_TAG_RX.sub("", text)
    return re.sub(r"\s{2,}", " ", t).strip()

def _fallback_hashtag_rules(platform_slug: str, tags: List[str], caption_text: str = "") -> List[str]:
    p = (_norm_platform(platform_slug) or "").strip().lower()
    caps = {"instagram": 12, "tiktok": 5, "linkedin": 3, "twitter": 2, "facebook": 3}
    max_n = caps.get(p, 8)
    cleaned = []
    for t in tags or []:
        tt = str(t).lstrip("#").strip().lower()
        if tt:
            cleaned.append(tt)
    cleaned = _dedupe_preserve(cleaned)
    if caption_text:
        inline = set(_extract_tags_from_text(caption_text))
        cleaned = [t for t in cleaned if t not in inline]
    return cleaned[:max_n]

def _apply_hashtag_rules(platform_slug: str, tags: List[str], caption_text: str = "") -> List[str]:
    try:
        from utils.hashtag_rules import enforce_hashtag_rules as _ehr
        return _ehr(platform_slug, tags, caption_text)
    except Exception:
        return _fallback_hashtag_rules(platform_slug, tags, caption_text)

# =============================================================================
# Flowables
# =============================================================================
class PlatformBanner(Flowable):
    def __init__(self, platform: str, avail_width: float, height: float = 28.0, radius: float = 6.0):
        super().__init__()
        self.platform = _norm_platform(platform)
        self.avail_width = float(avail_width or 0)
        self.height = float(height)
        self.radius = float(radius)
        self.padding_x = 10.0
        self.bg = PLATFORM_COLORS.get(self.platform, colors.Color(0.85, 0.85, 0.85))
        self._icon_reader: Optional[ImageReader] = None
        self._icon_w = self._icon_h = 0.0
        try:
            ip = _icon_path(self.platform)
            if ip:
                self._icon_reader = ImageReader(ip)
                iw, ih = self._icon_reader.getSize()
                target_h = max(0.0, self.height - 10.0)
                scale = min(target_h / float(ih or 1), 1.0)
                self._icon_w = (iw or 0) * scale
                self._icon_h = (ih or 0) * scale
        except Exception:
            self._icon_reader = None
        self.width = self.avail_width

    def wrap(self, availWidth, availHeight):
        self.width = min(self.avail_width or availWidth, availWidth)
        return self.width, self.height

    def draw(self):
        c = self.canv
        c.saveState()
        c.setFillColor(self.bg)
        c.setStrokeColor(self.bg)
        c.roundRect(0, 0, self.width, self.height, self.radius, stroke=0, fill=1)
        if self._icon_reader and self._icon_w > 0 and self._icon_h > 0:
            x = self.padding_x
            y = (self.height - self._icon_h) / 2.0
            try:
                c.drawImage(self._icon_reader, x, y, width=self._icon_w, height=self._icon_h,
                            mask='auto', preserveAspectRatio=True, anchor='sw')
            except Exception:
                pass
        c.restoreState()

class CTACard(Flowable):
    def __init__(self, text: str, avail_width: float, style: ParagraphStyle):
        super().__init__()
        self.text = text or ""
        self.avail_width = float(avail_width or 0)
        self.style = style
        self.padding = 10
        self.radius = 8
        self.bg_color = colors.HexColor("#EEF6FF")
        self.border_color = colors.HexColor("#C7E1FF")
        self.border_width = 0.8
        self._para: Optional[Paragraph] = None
        self.width = self.avail_width
        self.height = 0

    def wrap(self, availWidth, availHeight):
        box_width = min(self.avail_width or availWidth, availWidth)
        inner_width = max(0, box_width - 2 * self.padding)
        self._para = Paragraph(self.text, self.style)
        pw, ph = self._para.wrap(inner_width, availHeight)
        self.width = box_width
        self.height = ph + 2 * self.padding
        return self.width, self.height

    def draw(self):
        c = self.canv
        c.saveState()
        c.setFillColor(self.bg_color)
        c.setStrokeColor(self.border_color)
        c.setLineWidth(self.border_width)
        c.roundRect(0, 0, self.width, self.height, self.radius, stroke=1, fill=1)
        c.translate(self.padding, self.padding)
        if self._para is not None:
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
            "Brand", parent=base["Heading2"], fontName=_BASE_FONT_BOLD,
            fontSize=13.5, leading=17.0, textColor=colors.black
        ),
        "BrandSub": ParagraphStyle(
            "BrandSub", parent=base["BodyText"], fontName=_BASE_FONT,
            fontSize=10.0, leading=13.5, textColor=colors.Color(0, 0, 0, 0.6),
            spaceBefore=1.5
        ),
    }
    return styles

# =============================================================================
# Header/Footer
# =============================================================================
def _header_table(brand_config: Dict[str, Any], styles: Dict[str, ParagraphStyle], width: float):
    raw_logo = brand_config.get("logo_path") or ""
    logo_path = _resolve_logo_path(raw_logo)

    brand_name = brand_config.get("brand_name", "Content365")
    website = (brand_config.get("website") or "content365.xyz").strip()
    website_href = ("https://" + website) if website and not website.startswith(("http://", "https://")) else website

    # Logo (scaled safely) or tiny spacer
    logo_img = _safe_logo_image(logo_path, max_w=LOGO_MAX_W, max_h=LOGO_MAX_H) or Spacer(0.01, 0.01)

    # Right block: name + site
    name_para = Paragraph(brand_name, styles["Brand"])
    site_para = Paragraph(f'<a href="{website_href}">{website}</a>', styles["BrandSub"])
    right_tbl = Table([[name_para], [site_para]])
    right_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    # Layout math
    try:
        logo_w = getattr(logo_img, "drawWidth", LOGO_MAX_W)
        logo_h = getattr(logo_img, "drawHeight", LOGO_MAX_H)
    except Exception:
        logo_w, logo_h = LOGO_MAX_W, LOGO_MAX_H

    left_col_w  = max(logo_w, 0.6 * inch) + 6  # breathing room inside logo col
    spacer_w    = float(HEADER_GUTTER or 10)   # explicit gap between logo and text
    right_col_w = max(0, width - left_col_w - spacer_w)

    # ensure right_tbl wraps correctly at computed width
    right_tbl._argW = [right_col_w]  # type: ignore[attr-defined]

    row_h = max(logo_h, 0.6 * inch)

    # 3 columns: [logo] [gutter] [name+site]
    data = [[logo_img, "", right_tbl]]
    col_widths = [left_col_w, spacer_w, right_col_w]

    tbl = Table(data, colWidths=col_widths, rowHeights=[row_h], hAlign="LEFT")
    tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("BACKGROUND", (1, 0), (1, 0), colors.white),  # keep gutter transparent
    ]))
    return tbl

def _footer(canvas: Canvas, doc, brand_config: Dict[str, Any]):
    footer_text = brand_config.get("footer_text", "Generated by Content365.xyz — Create your own AI marketing packs in minutes.")
    canvas.saveState()
    canvas.setFont(_BASE_FONT, 8.5)
    canvas.setFillColor(colors.Color(0, 0, 0, 0.55))
    x = doc.leftMargin
    y = 0.5 * inch
    if footer_text:
        canvas.drawString(x, y, footer_text)
    try:
        canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, y, f"Page {doc.page}")
    except Exception:
        pass
    canvas.restoreState()

# =============================================================================
# Normalizers for incoming payload (fixes X/Twitter key issues)
# =============================================================================
def _normalize_platform_map(d: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns a dict keyed by normalized platform names (Instagram, LinkedIn, TikTok, Twitter, Facebook).
    If duplicates normalize to the same key, later entries win.
    """
    out: Dict[str, Any] = {}
    for k, v in (d or {}).items():
        out[_norm_platform(k)] = v
    return out

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
                    styles: Dict[str, ParagraphStyle], width: float, fallback_text: str = "") -> List[Any]:
    parts: List[Any] = []

    plat = _norm_platform(platform)

    # Banner
    parts.append(PlatformBanner(plat, width, height=28))
    parts.append(Spacer(1, 4))

    # Caption text (string or dict with 'text' key)
    if isinstance(caption_block, dict):
        text = caption_block.get("text") or caption_block.get("caption") or ""
    else:
        text = caption_block or ""
    text = _sanitize_for_pdf(_safe_text(text))

    # Inline tags -> collect & strip
    inline_from_caption = set(_extract_tags_from_text(text))
    caption_clean = _strip_inline_hashtags(text)

    # Merge explicit tags with inline
    merged_tags: List[str] = list(tag_list or [])
    merged_tags += [f"#{t}" for t in inline_from_caption if t]

    # Apply platform-specific rules
    clamped_tags = _apply_hashtag_rules(plat, merged_tags, caption_clean)

    # Fallback caption if truly empty after stripping
    if not caption_clean and not clamped_tags:
        caption_clean = _sanitize_for_pdf(_safe_text(fallback_text))

    # If still nothing, skip this platform block entirely
    if not caption_clean and not clamped_tags:
        return []

    if caption_clean:
        parts.append(Paragraph(_autolink(caption_clean), styles["Caption"]))
    if clamped_tags:
        parts.append(Paragraph(_hashline(clamped_tags), styles["Hashtags"]))

    return parts

# =============================================================================
# Main builder
# =============================================================================
def generate_pdf(payload: Dict[str, Any], output_path: str, brand_config: Optional[Dict[str, Any]] = None) -> str:
    """
    Build a branded, professional PDF for Content365.

    Expected payload format (flexible):
    {
      "blog": {
        "headline": "...",
        "intro": "...",
        "body": ["para1", "para2"],
        "bullets": ["...", "..."],
        "cta": "..."
      },
      "captions": { "Instagram": "...", "LinkedIn": {"text": "..."}, ... },
      "hashtags": { "Instagram": ["#one", "#two"], "LinkedIn": [...] }
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
    story.append(_header_table(brand_config, styles, doc.width))
    story.append(Spacer(1, 10))

    # Blog
    blog = (payload.get("blog") or {})
    headline = _sanitize_for_pdf(_safe_text(blog.get("headline") or blog.get("title") or "Your Content Pack"))
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

    # Social: normalize maps so 'x'/'X' keys feed 'Twitter'
    captions_in = _normalize_platform_map(payload.get("captions") or {})
    hashtags_in = _normalize_platform_map(payload.get("hashtags") or {})

    platforms_seen = list(captions_in.keys() | hashtags_in.keys()) if hasattr(captions_in, "keys") else list(captions_in.keys())
    ordered = [p for p in PLATFORM_ORDER if p in platforms_seen] + [p for p in platforms_seen if p not in PLATFORM_ORDER]

    # Fallback caption seed (so a platform never renders totally empty)
    fallback_seed = headline

    for plat in ordered:
        cap_block = captions_in.get(plat) or {}
        tag_list = hashtags_in.get(plat) or []
        parts = _platform_block(plat, cap_block, tag_list, styles, doc.width, fallback_seed)
        if parts:
            story += parts
            story.append(Spacer(1, 10))

    def _on_page(canvas: Canvas, doc_obj):
        try:
            if getattr(doc_obj, "page", 0) == 1:
                canvas.setAuthor(brand_config.get("brand_name", "Content365"))
                canvas.setTitle(headline)
                canvas.setSubject("Social content pack")
        except Exception:
            pass
        _footer(canvas, doc_obj, brand_config)

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return output_path
