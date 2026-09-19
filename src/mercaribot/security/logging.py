"""Logging filter for redacting sensitive secrets and tokens."""

from __future__ import annotations

import logging
import re

# Telegram bot token pattern
TELEGRAM_TOKEN_REGEX = re.compile(r"\b\d{6,12}:[A-Za-z0-9_-]{30,}\b")
TELEGRAM_URL_REGEX = re.compile(r"/bot\d{6,12}:[A-Za-z0-9_-]{30,}/")


class SecretMaskingFilter(logging.Filter):
    """
    Intercepts log records and automatically masks sensitive API tokens and URLs.
    OWASP A09 Compliant (Security Logging & Monitoring Failures).
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self._redact(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self._redact(v) if isinstance(v, str) else v for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self._redact(v) if isinstance(v, str) else v for v in record.args)
        return True

    @staticmethod
    def _redact(text: str) -> str:
        text = TELEGRAM_URL_REGEX.sub("/bot[REDACTED_TELEGRAM_TOKEN]/", text)
        text = TELEGRAM_TOKEN_REGEX.sub("[REDACTED_TELEGRAM_TOKEN]", text)
        return text
