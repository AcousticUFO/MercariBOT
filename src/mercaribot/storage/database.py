"""SQLite storage manager with strict parameterized queries and permission hardening."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import stat
from collections.abc import Iterable, Sequence
from pathlib import Path

from mercaribot.models import MercariItem

logger = logging.getLogger(__name__)


class SQLiteStorage:
    """Manages SQLite database for tracking already notified Mercari items."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Create and configure a connection with WAL mode enabled."""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initialize SQLite schema, WAL mode, and secure permissions."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._get_connection() as conn:
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS seen_items (
                    id TEXT PRIMARY KEY,
                    keyword TEXT,
                    name TEXT,
                    price INTEGER,
                    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_seen_items_keyword ON seen_items(keyword);"
            )

        # POSIX Hardening: restrict mercaribot.db to 0600 (OWASP A01)
        if os.name == "posix" and self.db_path.exists():
            try:
                self.db_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
            except OSError as e:
                logger.debug(f"Unable to change permissions on {self.db_path}: {e}")

    def is_seen(self, item_id: str) -> bool:
        """Check if an item id has already been recorded."""
        with self._get_connection() as conn:
            cur = conn.execute("SELECT 1 FROM seen_items WHERE id = ? LIMIT 1;", (item_id,))
            return cur.fetchone() is not None

    def filter_new_items(self, items: Sequence[MercariItem]) -> list[MercariItem]:
        """
        Takes a list of items and returns only those that have not been recorded yet.
        Maintains the original order of items.
        """
        if not items:
            return []

        item_ids = [item.id for item in items]
        seen_set: set[str] = set()

        chunk_size = 500
        with self._get_connection() as conn:
            for i in range(0, len(item_ids), chunk_size):
                chunk = item_ids[i : i + chunk_size]
                placeholders = ",".join("?" * len(chunk))
                query = f"SELECT id FROM seen_items WHERE id IN ({placeholders});"  # nosec: B608
                for row in conn.execute(query, chunk):
                    seen_set.add(row[0])

        new_items = [item for item in items if item.id not in seen_set]
        return new_items

    def mark_as_seen(self, items: Iterable[MercariItem]) -> None:
        """Insert items into the database if not already present."""
        rows = [(item.id, item.keyword, item.name, item.price) for item in items]
        if not rows:
            return

        with self._get_connection() as conn:
            conn.executemany(
                """
                INSERT OR IGNORE INTO seen_items (id, keyword, name, price)
                VALUES (?, ?, ?, ?);
                """,
                rows,
            )

    def mark_id_as_seen(self, item_id: str, keyword: str = "") -> None:
        """Insert a single item id."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO seen_items (id, keyword, name, price)
                VALUES (?, ?, ?, ?);
                """,
                (item_id, keyword, "", 0),
            )

    def get_total_seen_count(self) -> int:
        """Return the total number of unique items tracked."""
        with self._get_connection() as conn:
            cur = conn.execute("SELECT COUNT(*) FROM seen_items;")
            row = cur.fetchone()
            return int(row[0]) if row else 0

    def import_from_json(self, json_path: Path) -> int:
        """
        Migrate items from legacy scraped_cache.json into SQLite.
        Returns the number of newly added records.
        """
        if not json_path.exists():
            return 0

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"Error reading JSON cache ({json_path}): {e}")
            return 0

        rows = []
        for keyword, ids in data.items():
            if isinstance(ids, list):
                for item_id in ids:
                    if item_id:
                        rows.append((str(item_id), keyword, "Imported from JSON cache", 0))
            elif isinstance(ids, str):
                for item_id in ids.split(","):
                    item_id = item_id.strip()
                    if item_id:
                        rows.append((item_id, keyword, "Imported from JSON cache", 0))

        if not rows:
            return 0

        initial_count = self.get_total_seen_count()
        with self._get_connection() as conn:
            conn.executemany(
                """
                INSERT OR IGNORE INTO seen_items (id, keyword, name, price)
                VALUES (?, ?, ?, ?);
                """,
                rows,
            )
        new_count = self.get_total_seen_count()
        imported = new_count - initial_count
        logger.info(f"JSON cache migration completed: {imported} items imported into SQLite.")
        return imported
