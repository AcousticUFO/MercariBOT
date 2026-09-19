"""Input validation and SSRF mitigation helpers."""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse

# Standard Telegram bot token format: <bot_id>:<token>
TOKEN_PATTERN = re.compile(r"^\d{6,12}:[A-Za-z0-9_-]{30,}$")
CHAT_ID_PATTERN = re.compile(r"^-?\d+$")

# Whitelist of trusted CDN domains allowed for remote image loading
ALLOWED_IMAGE_DOMAINS = (
    "static.mercdn.net",
    "jp.mercari.com",
    "mercdn.net",
)


def validate_telegram_token(token: str) -> str:
    """Validate telegram bot token format."""
    clean = token.strip()
    if not clean or not TOKEN_PATTERN.match(clean):
        raise ValueError(
            "Invalid TELEGRAM_TOKEN format. Expected: '123456789:ABCDefgh...'"
        )
    return clean


def validate_telegram_chat_id(chat_id: str) -> str:
    """Validate telegram chat ID format."""
    clean = str(chat_id).strip()
    if not clean or not CHAT_ID_PATTERN.match(clean):
        raise ValueError(
            "Invalid TELEGRAM_CHAT_ID format. Must be numeric (e.g. 123456789)."
        )
    return clean


def is_safe_image_url(url: str) -> bool:
    """
    Verify that an image URL is strictly safe and points to an official Mercari CDN.
    OWASP A10 Protection (Server-Side Request Forgery - SSRF).
    """
    if not url or not isinstance(url, str):
        return False

    parsed = urlparse(url.strip())

    # 1. Enforce HTTPS
    if parsed.scheme.lower() != "https":
        return False

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return False

    # 2. Block direct IP addresses (loopback, private, link-local, cloud metadata)
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return False
        return False
    except ValueError:
        pass

    # 3. Strict check against trusted Mercari domain whitelist
    for allowed in ALLOWED_IMAGE_DOMAINS:
        if hostname == allowed or hostname.endswith(f".{allowed}"):
            return True

    return False
