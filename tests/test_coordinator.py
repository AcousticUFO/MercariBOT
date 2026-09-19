from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from mercaribot.engine.coordinator import ScanCoordinator
from mercaribot.models import AppConfig, MercariItem, SearchConfig
from mercaribot.storage.database import SQLiteStorage


@pytest.mark.asyncio
async def test_coordinator_flow(tmp_path: Path):
    db_file = tmp_path / "coord_test.db"
    storage = SQLiteStorage(db_file)

    cfg = AppConfig(
        telegram_token="dummy",
        telegram_chat_id="123",
        searches=[SearchConfig(keywords="guitar")],
        request_delay=0.0,
        delay=1,
    )

    scraper = AsyncMock()
    scraper.search.return_value = [
        MercariItem(
            id="item1",
            name="Fender Stratocaster",
            price=50000,
            image_url="",
            product_url="http://example.com/1",
            keyword="guitar",
        ),
        MercariItem(
            id="item2",
            name="Gibson Les Paul",
            price=90000,
            image_url="",
            product_url="http://example.com/2",
            keyword="guitar",
        ),
    ]

    notifier = AsyncMock()
    notifier.notify_item.return_value = True

    coordinator = ScanCoordinator(
        config=cfg,
        storage=storage,
        scraper=scraper,
        notifier=notifier,
    )

    # Pass 1: 2 new items detected
    count1 = await coordinator.run_once(dry_run=False)
    assert count1 == 2
    assert notifier.notify_item.call_count == 2
    assert storage.get_total_seen_count() == 2

    # Pass 2: scraper returns the same items, 0 new items alerted
    notifier.notify_item.reset_mock()
    count2 = await coordinator.run_once(dry_run=False)
    assert count2 == 0
    assert notifier.notify_item.call_count == 0
