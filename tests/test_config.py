from __future__ import annotations

from pathlib import Path

from usage_monitor import config


def test_defaults_without_any_file(home: Path) -> None:
    assert config.load_config() == config.Config()


def test_toml_is_read_and_prefs_take_precedence(home: Path) -> None:
    config.config_file().parent.mkdir(parents=True)
    config.config_file().write_text(
        'claude_order = ["a@x"]\nalert_at = 90\nrefresh_seconds = 5\nlanguage = "es"\n', encoding="utf-8"
    )
    cfg = config.load_config()
    assert (cfg.claude_order, cfg.alert_at, cfg.language) == (("a@x",), 90.0, "es")
    assert cfg.refresh_seconds == 60  # never below a minute

    config.save_prefs(language="zh")
    config.save_prefs(auto_switch=True)  # later changes keep earlier ones
    cfg = config.load_config()
    assert (cfg.language, cfg.auto_switch, cfg.alert_at) == ("zh", True, 90.0)


def test_example_file_is_valid_and_matches_the_defaults(home: Path) -> None:
    config.config_file().parent.mkdir(parents=True)
    config.config_file().write_text(config.EXAMPLE, encoding="utf-8")
    assert config.load_config() == config.Config()


def test_broken_prefs_are_ignored(home: Path) -> None:
    config.prefs_file().parent.mkdir(parents=True)
    config.prefs_file().write_text("{not json", encoding="utf-8")
    assert config.load_config() == config.Config()
