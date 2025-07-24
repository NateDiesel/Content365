def load_prompt_template():
    with open("utils/prompt_template.txt", "r", encoding="utf-8") as f:
        return f.read()