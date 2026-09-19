import json

import httpx
import pytest

from mercaribot.currency import CurrencyService
from mercaribot.models import MercariItem
from mercaribot.notifier.telegram import TelegramNotifier


@pytest.mark.asyncio
async def test_notify_item_html_formatting():
    captured_requests = []

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 123}})

    transport = httpx.MockTransport(mock_handler)
    mock_client = httpx.AsyncClient(transport=transport)

    currency = CurrencyService(fallback_rate=0.0055, auto_fetch=False)
    notifier = TelegramNotifier(
        token="123456789:ABCDefghIJKlmnoPQRstuvWXYZ12345678",
        chat_id="12345",
        currency_service=currency,
        download_photos=False,
        client=mock_client,
        throttle_seconds=0.0,
    )

    item = MercariItem(
        id="m123456",
        name="<Script>Test & Alert</Script>",
        price=1000,
        image_url="https://static.mercdn.net/photo.jpg",
        product_url="https://jp.mercari.com/item/m123456",
        keyword="rare test",
    )

    success = await notifier.notify_item(item)
    assert success is True
    assert len(captured_requests) == 1
    req = captured_requests[0]
    assert "sendMessage" in str(req.url)

    body = json.loads(req.content.decode("utf-8"))
    assert body["chat_id"] == "12345"
    assert body["parse_mode"] == "HTML"
    # OWASP A03: verify that arbitrary HTML tags are properly escaped
    assert "&lt;Script&gt;Test &amp; Alert&lt;/Script&gt;" in body["text"]
    assert "1000¥" in body["text"]
    assert "~5.50€" in body["text"]
    assert "<code>rare test</code>" in body["text"]
