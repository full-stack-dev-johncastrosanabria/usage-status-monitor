from __future__ import annotations

import json
from pathlib import Path

import pytest

from usage_monitor import settings


@pytest.fixture
def linked(tmp_path: Path) -> tuple[Path, Path]:
    """A real settings.json plus a symlink to it, as in each account's folder."""
    real, link = tmp_path / "real.json", tmp_path / "link.json"
    original = {
        "model": "opus",
        "effortLevel": "xhigh",
        "hooks": {"x": 1},
        "modelSettings": {"claude-opus-5-5": {"effortLevel": "high", "autoCompactWindow": 1}},
    }
    real.write_text(json.dumps(original))
    link.symlink_to(real)
    return real, link


def test_read_prefers_per_model_effort(linked: tuple[Path, Path]) -> None:
    s = settings.read(linked[1])
    assert (s.model, s.effort, s.label) == ("opus", "high", "Opus 5.5")
    assert {"default", "sonnet", "claude-opus-4-8"} <= {m.id for m in s.models}


@pytest.mark.parametrize("bad", [{"model": "gpt-9"}, {"effort": "turbo"}])
def test_write_rejects_unknown_values(linked: tuple[Path, Path], bad: dict[str, str]) -> None:
    real, link = linked
    before = real.read_text()
    with pytest.raises(ValueError):
        settings.write(path=link, **bad)
    assert real.read_text() == before


def test_write_keeps_symlink_other_keys_and_backup(linked: tuple[Path, Path]) -> None:
    real, link = linked
    s = settings.write(effort="max", path=link)
    data = json.loads(real.read_text())
    assert link.is_symlink() and s.effort == "max"
    assert data["effortLevel"] == "max" and data["hooks"] == {"x": 1}
    assert data["modelSettings"]["claude-opus-5-5"] == {"effortLevel": "max", "autoCompactWindow": 1}

    settings.write(model="sonnet", path=link)
    assert json.loads(real.read_text())["model"] == "sonnet"
    backup = json.loads(real.with_name("real.json.bak-usage-monitor").read_text())
    assert backup["effortLevel"] == "xhigh"  # the backup keeps the original state


def test_default_model_removes_the_key_and_unknown_models_stay_visible(linked: tuple[Path, Path]) -> None:
    real, link = linked
    assert settings.write(model="default", path=link).model == "default"
    assert "model" not in json.loads(real.read_text())

    real.write_text(json.dumps({"model": "opus[1m]"}))
    s = settings.read(link)
    assert s.model == "opus[1m]" and s.models[-1].id == "opus[1m]"  # outside the catalogue: shown as is
