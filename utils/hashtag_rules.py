# utils/hashtag_rules.py
# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import List

def _norm_platform(slug: str) -> str:
    s = (slug or "").strip().lower()
    return "x" if s in {"x", "twitter"} else s

def _clean_tag(t: str) -> str:
    # remove leading '#', spaces, and control chars; keep a-z0-9+underscore
    t = (t or "").strip().lstrip("#")
    out = []
    for ch in t:
        if ch.isalnum() or ch == "_":
            out.append(ch.lower())
    return "".join(out)

def _dedupe_preserve(seq: List[str]) -> List[str]:
    seen = set()
    out = []
    for t in seq:
        k = t.lower()
        if k and k not in seen:
            seen.add(k)
            out.append(t)
    return out

def _extract_inline_hashtags(text: str) -> List[str]:
    if not text:
        return []
    out, cur = [], []
    i = 0
    while i < len(text):
        if text[i] == "#":
            i += 1
            cur = []
            while i < len(text) and (text[i].isalnum() or text[i] == "_"):
                cur.append(text[i].lower()); i += 1
            if cur:
                out.append("".join(cur))
        else:
            i += 1
    return out

def enforce_hashtag_rules(platform_slug: str,
                          tags: List[str],
                          caption_text: str = "") -> List[str]:
    """
    Normalize and clamp hashtags by platform.
    Returns a *list without leading #*, caller can render with '#'+tag.
    """
    p = _norm_platform(platform_slug)

    # recommended caps (conservative, revenue-safe)
    caps = {
        "instagram": 12,  # rec. 8–12; hard cap 12 to avoid spammy look
        "tiktok": 5,
        "linkedin": 5,
        "x": 2,           # Twitter/X: keep it ultra short
        "facebook": 5,
    }
    max_n = caps.get(p, 8)

    # clean + dedupe
    cleaned = [_clean_tag(t) for t in (tags or [])]
    cleaned = [t for t in cleaned if t]
    cleaned = _dedupe_preserve(cleaned)

    # drop tags already inline in the caption
    if caption_text:
        inline = set(_extract_inline_hashtags(caption_text))
        cleaned = [t for t in cleaned if t not in inline]

    # clamp count
    return cleaned[:max_n]
