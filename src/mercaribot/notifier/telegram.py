"""Asynchronous Telegram notification client with HTML formatting, SSRF filtering, and rate limiting."""

from __future__ import annotations

import asyncio
import html
import logging
import re

import httpx

from mercaribot.currency import CurrencyService
from mercaribot.models import MercariItem
from mercaribot.security.validators import is_safe_image_url

logger = logging.getLogger(__name__)

DEFAULT_HTML_TEMPLATE = """⭕️ <b>{name}</b>
💰 {price_jpy}¥ (~{price_converted}{currency_symbol})
🔍 Keyword: <code>{keyword}</code>
🔗 <a href="{url}">View listing on Mercari</a>"""


class TelegramNotifier:
    """Sends secure, rich alerts to Telegram via direct Bot API calls."""

    def __init__(
        self,
        token: str,
        chat_id: str,
        currency_service: CurrencyService,
        download_photos: bool = True,
        template: str = "",
        client: httpx.AsyncClient | None = None,
        throttle_seconds: float = 1.2,
    ):
        self.token = token
        self.chat_id = chat_id
        self.currency_service = currency_service
        self.download_photos = download_photos
        self.template = template or DEFAULT_HTML_TEMPLATE
        self.throttle_seconds = throttle_seconds

        self._external_client = client is not None
        self._client = client or httpx.AsyncClient(timeout=20.0)

    async def aclose(self) -> None:
        """Close HTTP client if created internally."""
        if not self._external_client:
            await self._client.aclose()

    async def send_startup_message(self) -> bool:
        """Send startup announcement with HTML formatting."""
        text = "🚀 <b>MercariBOT is online!</b>\nMercari Japan monitoring is active."
        return await self.send_message(text, parse_mode="HTML")

    async def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """Send a formatted text message to Telegram."""
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "disable_web_page_preview": False,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode

        return await self._execute_request("sendMessage", payload)

    async def send_photo(
        self, photo_url: str, caption: str, parse_mode: str = "HTML"
    ) -> bool:
        """Send a photo with caption to Telegram after SSRF verification."""
        if not is_safe_image_url(photo_url):
            logger.warning(
                f"Suspicious or disallowed image URL rejected (anti-SSRF): {photo_url[:60]}"
            )
            return False

        payload = {
            "chat_id": self.chat_id,
            "photo": photo_url,
            "caption": caption,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode

        return await self._execute_request("sendPhoto", payload)

    async def _execute_request(self, endpoint: str, payload: dict) -> bool:
        """Execute request with rate limiting and retry on 429."""
        api_url = f"https://api.telegram.org/bot{self.token}/{endpoint}"

        for attempt in range(3):
            try:
                response = await self._client.post(api_url, json=payload)
                if response.status_code == 200:
                    await asyncio.sleep(self.throttle_seconds)
                    return True

                elif response.status_code == 429:
                    retry_after = int(
                        response.json().get("parameters", {}).get("retry_after", 5)
                    )
                    logger.warning(
                        f"Telegram rate limit (429). Waiting {retry_after}s before retrying..."
                    )
                    await asyncio.sleep(retry_after)
                    continue

                else:
                    logger.error(
                        f"Telegram error ({endpoint} - HTTP {response.status_code}): {response.text}"
                    )
                    if payload.get("parse_mode") and attempt == 0:
                        logger.info("Retrying with plain text fallback...")
                        payload.pop("parse_mode", None)
                        continue
                    return False

            except httpx.HTTPError as e:
                logger.error(f"HTTP error during Telegram dispatch: {e}")
                await asyncio.sleep(2.0)
            except (ValueError, KeyError) as e:
                logger.error(f"Data error during Telegram dispatch: {e}")
                return False

        return False

    async def notify_item(self, item: MercariItem) -> bool:
        """Format and securely send notification for a new Mercari item."""
        converted_price, currency_symbol = await self.currency_service.convert(
            item.price, client=self._client
        )

        safe_name = html.escape(item.name)
        safe_keyword = html.escape(item.keyword)
        safe_url = html.escape(item.product_url)

        msg = (
            self.template.replace("{name}", safe_name)
            .replace("{price_jpy}", str(item.price))
            .replace("{price_converted}", f"{converted_price:.2f}")
            .replace("{currency_symbol}", currency_symbol)
            .replace("{keyword}", safe_keyword)
            .replace("{url}", safe_url)
            .replace("$productName", safe_name)
            .replace("$price", str(item.price))
            .replace("$productURL", safe_url)
            .replace("$id", item.id)
            .replace("$priceCurrency", f"{converted_price:.2f} {currency_symbol}")
        )

        if "*" in msg and "<b>" not in msg:
            msg = re.sub(r"\*(.*?)\*", r"<b>\1</b>", msg)
            msg = re.sub(r"`(.*?)`", r"<code>\1</code>", msg)

        if self.download_photos and item.image_url:
            success = await self.send_photo(
                photo_url=item.image_url,
                caption=msg,
                parse_mode="HTML",
            )
            if success:
                return True
            logger.debug(
                f"Falling back to plain text for item {item.id}..."
            )

        return await self.send_message(msg, parse_mode="HTML")
