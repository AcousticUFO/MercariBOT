"""Configuration loader for MercariBOT with strict validation."""

from __future__ import annotations

import logging
import os
import stat
from pathlib import Path

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        import toml as tomllib  # type: ignore

from dotenv import dotenv_values, load_dotenv

from mercaribot.models import AppConfig, SearchConfig
from mercaribot.security.validators import (
    validate_telegram_chat_id,
    validate_telegram_token,
)

logger = logging.getLogger(__name__)


def enforce_file_permissions(file_path: Path) -> None:
    """On POSIX systems, ensure sensitive secret files (.env) are restricted to 0600."""
    if os.name == "posix" and file_path.exists():
        current_mode = stat.S_IMODE(file_path.stat().st_mode)
        if current_mode & 0o077:
            try:
                file_path.chmod(0o600)
                logger.debug(f"Restricted permissions of {file_path.name} to 0600.")
            except OSError as e:
                logger.warning(f"Unable to restrict permissions of {file_path}: {e}")


def load_config(
    config_file: Path | None = None,
    env_file: Path | None = None,
    base_dir: Path | None = None,
) -> AppConfig:
    """Load and strictly validate configuration from .env and config.toml."""
    if base_dir is None:
        base_dir = Path.cwd()

    if env_file is None:
        env_file = base_dir / ".env"

    env_values = {}
    if env_file.exists():
        enforce_file_permissions(env_file)
        env_values = dotenv_values(dotenv_path=env_file)
    else:
        load_dotenv()

    raw_token = (
        env_values.get("TELEGRAM_TOKEN")
        or os.getenv("TELEGRAM_TOKEN", "")
    ).strip()

    raw_chat_id = (
        env_values.get("TELEGRAM_CHAT_ID")
        or os.getenv("TELEGRAM_CHAT_ID", "")
    ).strip()

    telegram_token = validate_telegram_token(raw_token)
    telegram_chat_id = validate_telegram_chat_id(raw_chat_id)

    if config_file is None:
        config_file = base_dir / "config.toml"

    if not config_file.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_file}. "
            "Copy config.toml.example to config.toml and configure it."
        )

    with open(config_file, "rb") as f:
        data = tomllib.load(f)

    raw_searches = data.get("searches", [])
    if not raw_searches:
        logger.warning("No searches configured in config.toml ([[searches]]).")

    searches: list[SearchConfig] = []
    for s in raw_searches:
        kw = s.get("keywords", "").strip()
        if kw:
            searches.append(
                SearchConfig(
                    keywords=kw,
                    exclude_keywords=s.get("exclude_keywords", "").strip(),
                    min_price=s.get("min_price"),
                    max_price=s.get("max_price"),
                )
            )

    db_filename = data.get("database_file", "mercaribot.db")
    db_path = base_dir / db_filename

    return AppConfig(
        telegram_token=telegram_token,
        telegram_chat_id=telegram_chat_id,
        searches=searches,
        delay=max(10, int(data.get("delay", 60))),
        request_delay=max(0.5, float(data.get("request_delay", 1.5))),
        max_concurrent_requests=max(1, min(5, int(data.get("max_concurrent_requests", 2)))),
        change_rate=float(data.get("changerate", 0.0055)),
        auto_currency=bool(data.get("auto_currency", True)),
        target_currency=str(data.get("target_currency", "EUR")).upper(),
        download_photos=bool(data.get("downloadphotos", True)),
        message_template=str(data.get("message", "")).strip(),
        db_path=db_path,
    )
