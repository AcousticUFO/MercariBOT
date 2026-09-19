from pathlib import Path

import pytest

from mercaribot.config import load_config


def test_load_config_valid(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "TELEGRAM_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11\n"
        "TELEGRAM_CHAT_ID=987654321\n",
        encoding="utf-8",
    )

    config_file = tmp_path / "config.toml"
    config_file.write_text(
        'delay = 120\n'
        'changerate = 0.0062\n'
        'downloadphotos = false\n'
        '[[searches]]\n'
        'keywords = "sega saturn"\n'
        'exclude_keywords = "broken"\n',
        encoding="utf-8",
    )

    cfg = load_config(config_file=config_file, env_file=env_file, base_dir=tmp_path)
    assert cfg.telegram_token == "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    assert cfg.telegram_chat_id == "987654321"
    assert cfg.delay == 120
    assert cfg.change_rate == 0.0062
    assert cfg.download_photos is False
    assert len(cfg.searches) == 1
    assert cfg.searches[0].keywords == "sega saturn"
    assert cfg.searches[0].exclude_keywords == "broken"


def test_load_config_missing_env(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text("", encoding="utf-8")

    config_file = tmp_path / "config.toml"
    config_file.write_text('delay = 60\n', encoding="utf-8")

    with pytest.raises(ValueError, match="TELEGRAM_TOKEN"):
        load_config(config_file=config_file, env_file=env_file, base_dir=tmp_path)
