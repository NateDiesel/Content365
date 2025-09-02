def enforce_hashtag_rules(hashtags: dict) -> dict:
    limits = {
        "Instagram": 15,
        "TikTok": 5,
        "LinkedIn": 5,
        "Twitter": 2,
        "Facebook": 3
    }

    cleaned = {}
    for platform, tags in hashtags.items():
        # Defensive: if string, convert to list
        if isinstance(tags, str):
            tags = [tag.strip().lstrip("#") for tag in tags.split() if tag]
        # Enforce limits
        max_count = limits.get(platform, 5)
        cleaned[platform] = tags[:max_count]
    return cleaned
