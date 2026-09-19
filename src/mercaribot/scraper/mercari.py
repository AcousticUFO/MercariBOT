"""Asynchronous Mercari Japan API client."""

from __future__ import annotations

import asyncio
import logging
import uuid

import httpx

from mercaribot.models import MercariItem, SearchConfig
from mercaribot.scraper.dpop import DPoPGenerator

logger = logging.getLogger(__name__)

MERCARI_SEARCH_URL = "https://api.mercari.jp/v2/entities:search"


class MercariClient:
    """High-level async client for querying Mercari Japan search API."""

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        max_retries: int = 2,
    ):
        self._external_client = client is not None
        self._client = client or httpx.AsyncClient(
            timeout=15.0,
            headers={
                "X-Platform": "web",
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "*/*",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            },
        )
        self.dpop = DPoPGenerator()
        self.max_retries = max_retries

    async def aclose(self) -> None:
        """Close the underlying HTTP client if created internally."""
        if not self._external_client:
            await self._client.aclose()

    async def search(self, config: SearchConfig, page_size: int = 120) -> list[MercariItem]:
        """
        Search for items on Mercari Japan matching the query configuration.
        """
        payload = {
            "userId": f"BOT_{uuid.uuid4().hex[:8]}",
            "pageSize": page_size,
            "pageToken": "v1:0",
            "searchSessionId": uuid.uuid4().hex,
            "indexRouting": "INDEX_ROUTING_UNSPECIFIED",
            "searchCondition": {
                "keyword": config.keywords,
                "sort": "SORT_CREATED_TIME",
                "order": "ORDER_DESC",
                "status": ["STATUS_ON_SALE"],
                "excludeKeyword": config.exclude_keywords,
            },
            "defaultDatasets": ["DATASET_TYPE_MERCARI", "DATASET_TYPE_BEYOND"],
        }

        if config.min_price is not None or config.max_price is not None:
            if config.min_price is not None:
                payload["searchCondition"]["priceMin"] = config.min_price
            if config.max_price is not None:
                payload["searchCondition"]["priceMax"] = config.max_price

        for attempt in range(self.max_retries + 1):
            try:
                dpop_token = self.dpop.generate(url=MERCARI_SEARCH_URL, method="POST")
                headers = {"DPOP": dpop_token}

                response = await self._client.post(
                    MERCARI_SEARCH_URL,
                    json=payload,
                    headers=headers,
                )

                if response.status_code == 200:
                    data = response.json()
                    raw_items = data.get("items", [])
                    items: list[MercariItem] = []
                    for raw in raw_items:
                        item = MercariItem.from_api_dict(raw, keyword=config.keywords)
                        if item:
                            items.append(item)
                    return items

                elif response.status_code == 401:
                    logger.warning(
                        f"Mercari 401 Unauthorized for '{config.keywords}' (attempt {attempt + 1}/{self.max_retries + 1}). "
                        "Renewing DPoP token..."
                    )
                    self.dpop.rotate_key()
                    await asyncio.sleep(2.0)
                    continue

                elif response.status_code == 429:
                    logger.warning(
                        f"Mercari 429 Too Many Requests for '{config.keywords}'. Sleeping 5s..."
                    )
                    await asyncio.sleep(5.0)
                    continue

                else:
                    logger.error(
                        f"Mercari HTTP error {response.status_code} for '{config.keywords}': {response.text[:200]}"
                    )
                    return []

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                logger.warning(
                    f"Mercari network error for '{config.keywords}' (attempt {attempt + 1}): {e}"
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(2.0)
                else:
                    logger.error(f"Permanent scan failure for '{config.keywords}'.")
                    return []
            except (ValueError, KeyError) as e:
                logger.error(f"JSON decode error during Mercari scan ({config.keywords}): {e}")
                return []

        return []
