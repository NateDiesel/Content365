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
