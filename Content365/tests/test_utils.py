import re
from main import _fix_ai_casing, _valid_platforms

def test_fix_ai_casing():
    assert _fix_ai_casing("ai helps") == "AI helps"
    assert _fix_ai_casing("This is Ai.") == "This is AI."
    assert _fix_ai_casing("Use AI today") == "Use AI today"

def test_valid_platforms_order_and_dedupe():
    seq = ["Instagram","instagram","LinkedIn","X","X","Facebook"]
    slugs = _valid_platforms([p.lower() for p in seq])
    assert slugs == ["instagram","linkedin","x","facebook"]
