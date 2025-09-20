# utils/prompt_builder.py
from typing import List

def build_prompt(
    topic: str,
    tone: str,
    audience_type: str,
    post_style: str,
    word_count: str,
<<<<<<< HEAD
    platforms: str  # already formatted string, e.g., "Instagram, LinkedIn"
) -> str:
    """
    Single source of truth for your model instruction.
    Keeps wording tight for JSON-only behavior and high-quality output.
=======
    platforms: str  # e.g., "Instagram, LinkedIn"
) -> str:
    """
    Single source of truth for JSON-only generation.
    Keep wording tight for reliability across providers.
>>>>>>> 5a37524 (Initial commit of Content365 project)
    """
    post_style_line = f"\nPost Style: {post_style}" if post_style else ""
    return f"""You are a professional marketing strategist and copywriter.

Generate a branded content pack for the following:
Topic: {topic}
Tone: {tone or "Professional"}
Audience Type: {audience_type or "B2C"}{post_style_line}
Preferred Word Count: {word_count or "medium"}
Platforms: {platforms or "Instagram, LinkedIn"}

<<<<<<< HEAD
Return ONLY valid JSON with this exact structure:
{{
  "blog": {{
    "title": "string",
    "intro": "string",
    "bullets": ["string", "string"],
    "CTA": "string"
  }},
  "captions_by_platform": {{
    "Instagram": {{ "text": "string", "hashtags": ["tag1","tag2"] }},
    "LinkedIn": {{ "text": "string", "hashtags": ["tag1","tag2"] }},
    "TikTok": {{ "text": "string", "hashtags": ["tag1","tag2"] }},
    "Twitter": {{ "text": "string", "hashtags": ["tag1","tag2"] }},
    "Facebook": {{ "text": "string", "hashtags": ["tag1","tag2"] }}
  }},
  "hashtags": {{
    "Instagram": ["tag1","tag2"],
=======
Return ONLY valid JSON with exactly this structure (no markdown, no comments, no code fences):

{{
  "blog": {{
    "headline": "string",
    "intro": "string",
    "body": ["string", "string"],
    "bullets": ["string", "string"],
    "cta": "string"
  }},
  "captions": {{
    "Instagram": "string",
    "LinkedIn": "string",
    "TikTok": "string",
    "Twitter": "string",
    "Facebook": "string"
  }},
  "hashtags": {{
    "Instagram": ["tag1","tag2","tag3"],
>>>>>>> 5a37524 (Initial commit of Content365 project)
    "LinkedIn": ["tag1","tag2"],
    "TikTok": ["tag1","tag2"],
    "Twitter": ["tag1","tag2"],
    "Facebook": ["tag1","tag2"]
  }}
<<<<<<< HEAD
}}

Rules:
- Keep captions concise and platform-appropriate.
- Include emojis only where natural (Instagram/TikTok). Avoid on LinkedIn unless minimal.
- Hashtags should be relevant, non-generic, and within platform best practices.
- Do NOT include markdown fences or explanations; output JSON only.
"""
=======
}}"""
>>>>>>> 5a37524 (Initial commit of Content365 project)
