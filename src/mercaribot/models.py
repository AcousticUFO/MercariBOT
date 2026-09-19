"""Data models for MercariBOT."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MercariItem:
    """Represents a product item listed on Mercari Japan."""

    id: str
    name: str
    price: int
    image_url: str
    product_url: str
    status: str = "ITEM_STATUS_ON_SALE"
    keyword: str = ""

    @classmethod
    def from_api_dict(cls, data: dict, keyword: str = "") -> MercariItem | None:
        """Parse raw API dictionary into MercariItem with boundary validation."""
        try:
            item_id = str(data.get("id", "")).strip()
            # Truncate to 500 characters max to prevent memory DoS
            raw_name = str(data.get("name", "Untitled")).strip()[:500]
            price = max(int(data.get("price", 0)), 0)

            thumbnails = data.get("thumbnails", [])
            image_url = thumbnails[0] if thumbnails and isinstance(thumbnails[0], str) else ""
            product_url = f"https://jp.mercari.com/item/{item_id}"
            status = str(data.get("status", "ITEM_STATUS_ON_SALE"))

            if not item_id:
                return None

            return cls(
                id=item_id,
                name=raw_name,
                price=price,
                image_url=image_url,
                product_url=product_url,
                status=status,
                keyword=keyword,
            )
        except (ValueError, TypeError, KeyError):
            return None


@dataclass
class SearchConfig:
    """Configuration for an individual search query."""

    keywords: str
    exclude_keywords: str = ""
    min_price: int | None = None
    max_price: int | None = None


@dataclass
class AppConfig:
    """Global application configuration."""

    telegram_token: str
    telegram_chat_id: str
    searches: list[SearchConfig] = field(default_factory=list)
    delay: int = 60
    request_delay: float = 1.5
    max_concurrent_requests: int = 2
    change_rate: float = 0.0055
    auto_currency: bool = True
    target_currency: str = "EUR"
    download_photos: bool = True
    message_template: str = ""
    db_path: Path = field(default_factory=lambda: Path("mercaribot.db"))
