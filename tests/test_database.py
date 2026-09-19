import json
from pathlib import Path

import pytest

from mercaribot.models import MercariItem
from mercaribot.storage.database import SQLiteStorage


@pytest.fixture
def storage(tmp_path: Path) -> SQLiteStorage:
    db_file = tmp_path / "test_mercaribot.db"
    return SQLiteStorage(db_file)


def test_sqlite_storage_basic(storage: SQLiteStorage):
    item1 = MercariItem(
        id="m11111111",
        name="Item 1",
        price=1000,
        image_url="http://example.com/1.jpg",
        product_url="http://example.com/1",
        keyword="test",
    )
    item2 = MercariItem(
        id="m22222222",
        name="Item 2",
        price=2000,
        image_url="http://example.com/2.jpg",
        product_url="http://example.com/2",
        keyword="test",
    )

    assert not storage.is_seen("m11111111")
    assert storage.get_total_seen_count() == 0

    new_items = storage.filter_new_items([item1, item2])
    assert len(new_items) == 2

    # Mark item1 as seen
    storage.mark_as_seen([item1])
    assert storage.is_seen("m11111111")
    assert not storage.is_seen("m22222222")
    assert storage.get_total_seen_count() == 1

    # Filter again: only item2 should be returned
    new_items_2 = storage.filter_new_items([item1, item2])
    assert len(new_items_2) == 1
    assert new_items_2[0].id == "m22222222"


def test_import_from_json(storage: SQLiteStorage, tmp_path: Path):
    json_path = tmp_path / "legacy_cache.json"
    dummy_data = {
        "manga": ["item_a", "item_b"],
        "games": "item_c,item_d",
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(dummy_data, f)

    imported = storage.import_from_json(json_path)
    assert imported == 4
    assert storage.get_total_seen_count() == 4
    assert storage.is_seen("item_a")
    assert storage.is_seen("item_d")

    # Re-import should not create duplicates
    imported_again = storage.import_from_json(json_path)
    assert imported_again == 0
    assert storage.get_total_seen_count() == 4
