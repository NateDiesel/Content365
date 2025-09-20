<<<<<<< HEAD
<<<<<<< HEAD
def load_prompt_template():
    with open("utils/prompt_template.txt", "r", encoding="utf-8") as f:
        return f.read()
=======
def load_prompt_template(path="prompt_template.txt") -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return (
            "Create a blog post and grouped social captions for:\n"
            "- Topic: {topic}\n"
            "- Audience: {audience}\n"
            "- Tone: {tone}\n"
            "- Platforms: {platforms}\n"
            "- Word Count: {word_count}\n"
            "Return blog as structured JSON with fields: title, intro, bullets, CTA.\n"
            "Group captions and hashtags by platform.\n"
        )
>>>>>>> 2ed0c2a (chore: wire Gemini provider + provider_router)
=======
# -*- coding: utf-8 -*-
import os

def load_prompt_template() -> str:
    """Load a prompt template from disk if available; otherwise return a sane default."""
    candidates = [
        os.path.join("templates", "prompt.txt"),
        os.path.join("utils", "prompt_template.txt"),
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception:
                pass
    return (
        "You are a senior marketing strategist. Return ONLY valid JSON with keys: "
        "blog, captions_by_platform, hashtags.\n"
        "Topic: {topic}\n"
        "Tone: {tone}\n"
        "Audience Type: {audience_type}\n"
        "Post Style: {post_style}\n"
        "Preferred Word Count: {word_count}\n"
        "Platforms: {platforms}\n"
        "JSON rules: double quotes, no markdown fences."
    )
>>>>>>> 5a37524 (Initial commit of Content365 project)
