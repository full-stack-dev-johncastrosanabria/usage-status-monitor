"""Default model and effort of Claude Code (~/.claude/settings.json).

Every account shares that file through a symlink, so it is written at its real location,
atomically, keeping every other key and with a backup made first.
"""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import HOME
from .i18n import tr

SETTINGS = HOME / ".claude" / "settings.json"
EFFORTS = ("low", "medium", "high", "xhigh", "max")
DEFAULT = "default"  # no `model` key: Claude Code picks the recommended one for the plan


@dataclass(frozen=True, slots=True)
class Model:
    id: str  # the value of `model` in settings.json (alias or full identifier)
    label: str
    more: bool = False  # listed under "More models", as in the /model picker

    def to_json(self) -> dict[str, Any]:
        return {"id": self.id, "label": self.label, "more": self.more}


# shortcut: fixed catalogue, the same as Claude Code 2.1's /model picker (ids checked against its binary);
# update it when new models ship. A model outside the catalogue is shown as is.
CATALOG = (
    Model("opus", "Opus 5.5"),
    Model("sonnet", "Sonnet 5.5"),
    Model("fable", "Fable 5.2"),
    Model("haiku", "Haiku 5.5"),
    Model("claude-fable-5-1", "Fable 5.1", more=True),
    Model("claude-haiku-4-5", "Haiku 4.5", more=True),
    Model("claude-sonnet-5", "Sonnet 5", more=True),
    Model("claude-opus-5", "Opus 5", more=True),
    Model("claude-fable-5", "Fable 5", more=True),
    Model("claude-opus-4-8", "Opus 4.8", more=True),
    Model("claude-opus-4-7", "Opus 4.7", more=True),
    Model("claude-opus-4-6", "Opus 4.6", more=True),
    Model("claude-sonnet-4-6", "Sonnet 4.6", more=True),
)
KNOWN = {DEFAULT, *(m.id for m in CATALOG)}
ALIASES = {
    "opus": "claude-opus-5-5",
    "sonnet": "claude-sonnet-5-5",
    "fable": "claude-fable-5-2",
    "haiku": "claude-haiku-5-5",
}


@dataclass(frozen=True, slots=True)
class ClaudeSettings:
    model: str
    effort: str | None
    models: tuple[Model, ...]
    efforts: tuple[str, ...] = EFFORTS

    @property
    def label(self) -> str:
        return next((m.label for m in self.models if m.id == self.model), self.model)

    def to_json(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "effort": self.effort,
            "models": [m.to_json() for m in self.models],
            "efforts": list(self.efforts),
        }


def _from_dict(d: dict[str, Any]) -> ClaudeSettings:
    model = d.get("model") or DEFAULT
    per_model = (d.get("modelSettings") or {}).get(ALIASES.get(model, model)) or {}
    effort = per_model.get("effortLevel") or d.get("effortLevel")
    extra = () if model in KNOWN else (Model(model, model, more=True),)
    return ClaudeSettings(model, effort, (Model(DEFAULT, tr("Default")), *CATALOG, *extra))


def read(path: Path | None = None) -> ClaudeSettings:
    return _from_dict(json.loads((path or SETTINGS).read_text(encoding="utf-8")))


def write(model: str | None = None, effort: str | None = None, path: Path | None = None) -> ClaudeSettings:
    real = Path(os.path.realpath(path or SETTINGS))  # os.replace on the symlink would turn it into a file
    d: dict[str, Any] = json.loads(real.read_text(encoding="utf-8"))
    if model is not None and model not in KNOWN | set(d.get("modelSettings") or {}):
        raise ValueError(tr("unknown model: {model}", model=model))
    if effort is not None and effort not in EFFORTS:
        raise ValueError(tr("unknown effort: {effort}", effort=effort))

    backup = real.with_name(real.name + ".bak-usage-monitor")
    if not backup.exists():
        shutil.copy2(real, backup)
    if model == DEFAULT:
        d.pop("model", None)
    elif model:
        d["model"] = model
    if effort:
        # which one wins is not documented, so both are updated
        d["effortLevel"] = effort
        current = d.get("model")
        per_model = (d.get("modelSettings") or {}).get(ALIASES.get(current, current) if current else None)
        if per_model is not None and "effortLevel" in per_model:
            per_model["effortLevel"] = effort

    tmp = real.with_name(real.name + ".tmp-usage-monitor")
    tmp.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(real)
    return _from_dict(d)
