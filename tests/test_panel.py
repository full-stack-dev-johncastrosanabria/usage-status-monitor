from __future__ import annotations

import re
from importlib import resources

HTML = resources.files("usage_monitor.web").joinpath("panel.html").read_text(encoding="utf-8")


def test_panel_has_the_same_keys_in_every_language() -> None:
    block = HTML[HTML.index("const I18N = {") : HTML.index("\n};\n")]
    languages = dict(re.findall(r"^  (\w+): \{\n(.*?)^  \},", block, flags=re.S | re.M))
    keys = {code: set(re.findall(r"^    (\w+):", body, flags=re.M)) for code, body in languages.items()}
    assert set(keys) == {"en", "es", "zh"}
    assert keys["es"] == keys["en"] == keys["zh"] and len(keys["en"]) > 30

    used = set(re.findall(r'\bT\("(\w+)"', HTML))
    assert used <= keys["en"], used - keys["en"]
