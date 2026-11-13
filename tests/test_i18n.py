from __future__ import annotations

import ast
import string
from collections.abc import Iterator
from pathlib import Path

import pytest

from usage_monitor import i18n

SRC = Path(i18n.__file__).parent


def source_strings() -> set[str]:
    """Every literal passed to tr() anywhere in the package."""
    found: set[str] = set()
    for path in SRC.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "tr" and node.args:
                arg = node.args[0]
                assert isinstance(arg, ast.Constant), f"{path.name}:{node.lineno}: tr() needs a literal"
                found.add(arg.value)
    return found


def placeholders(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


@pytest.fixture(autouse=True)
def english() -> Iterator[None]:
    yield
    i18n.set_language("en")


@pytest.mark.parametrize("code", sorted(i18n.CATALOGS))
def test_catalogue_is_complete_and_keeps_placeholders(code: str) -> None:
    catalogue, source = i18n.CATALOGS[code], source_strings()
    assert source - set(catalogue) == set(), "strings without a translation"
    assert set(catalogue) - source == set(), "translations of strings that no longer exist"
    for english_text, translated in catalogue.items():
        assert placeholders(english_text) == placeholders(translated), english_text


def test_tr_translates_formats_and_falls_back() -> None:
    assert i18n.tr("There is no account #{n}.", n=7) == "There is no account #7."
    i18n.set_language("es")
    assert i18n.tr("There is no account #{n}.", n=7) == "No hay cuenta #7."
    assert i18n.tr("not in any catalogue") == "not in any catalogue"
    i18n.set_language("zh")
    assert i18n.tr("Weekly ({model})", model="Fable") == "每周（Fable）"
    i18n.set_language("klingon")
    assert i18n.language() == "en"
