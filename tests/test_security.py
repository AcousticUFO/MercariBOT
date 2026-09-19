import logging

import pytest

from mercaribot.security.logging import SecretMaskingFilter
from mercaribot.security.validators import (
    is_safe_image_url,
    validate_telegram_chat_id,
    validate_telegram_token,
)


def test_secret_masking_filter():
    filt = SecretMaskingFilter()
    token = "1234567890:abcdefghijklmnopqrstuvwxyzABCDEFGHI"

    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg=f"Calling https://api.telegram.org/bot{token}/sendMessage with token {token}",
        args=(),
        exc_info=None,
    )
    filt.filter(record)
    assert token not in record.msg
    assert "[REDACTED_TELEGRAM_TOKEN]" in record.msg
    assert "/bot[REDACTED_TELEGRAM_TOKEN]/" in record.msg


def test_ssrf_image_url_protection():
    assert is_safe_image_url("https://static.mercdn.net/item/detail/orig/photos/m123456_1.jpg")
    assert is_safe_image_url("https://jp.mercari.com/assets/img/logo.png")

    # SSRF / non-HTTPS / dangerous attempts
    assert not is_safe_image_url("http://static.mercdn.net/item.jpg")
    assert not is_safe_image_url("http://169.254.169.254/latest/meta-data/")
    assert not is_safe_image_url("http://127.0.0.1:8080/admin")
    assert not is_safe_image_url("http://[::1]/secret")
    assert not is_safe_image_url("file:///etc/passwd")
    assert not is_safe_image_url("https://attacker-controlled-site.com/photo.jpg")
    assert not is_safe_image_url("")


def test_validate_telegram_token():
    valid = "1234567890:abcdefghijklmnopqrstuvwxyzABCDEFGHI"
    assert validate_telegram_token(valid) == valid

    with pytest.raises(ValueError, match="Invalid TELEGRAM_TOKEN format"):
        validate_telegram_token("invalid_token")

    with pytest.raises(ValueError, match="Invalid TELEGRAM_TOKEN format"):
        validate_telegram_token("12345:short")


def test_validate_telegram_chat_id():
    assert validate_telegram_chat_id("123456789") == "123456789"
    assert validate_telegram_chat_id("-1001234567890") == "-1001234567890"

    with pytest.raises(ValueError, match="Invalid TELEGRAM_CHAT_ID format"):
        validate_telegram_chat_id("chat_id_text")
