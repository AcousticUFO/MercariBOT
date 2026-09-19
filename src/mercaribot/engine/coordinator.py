"""Scan coordinator: orchestrates search tasks, deduplication, and alerting."""

from __future__ import annotations

import asyncio
import logging

from mercaribot.models import AppConfig, MercariItem, SearchConfig
from mercaribot.notifier.telegram import TelegramNotifier
from mercaribot.scraper.mercari import MercariClient
from mercaribot.storage.database import SQLiteStorage

logger = logging.getLogger(__name__)


class ScanCoordinator:
    """Coordinates periodic scans across multiple Mercari search queries."""

    def __init__(
        self,
        config: AppConfig,
        storage: SQLiteStorage,
        scraper: MercariClient,
        notifier: TelegramNotifier,
        stop_event: asyncio.Event | None = None,
    ):
        self.config = config
        self.storage = storage
        self.scraper = scraper
        self.notifier = notifier
        self.stop_event = stop_event or asyncio.Event()

    async def scan_single_query(
        self,
        search_cfg: SearchConfig,
        semaphore: asyncio.Semaphore,
        dry_run: bool = False,
    ) -> list[MercariItem]:
        """Scan a single search query with concurrency control and deduplication."""
        async with semaphore:
            if self.stop_event.is_set():
                return []

            logger.info(f"Scanning: '{search_cfg.keywords}'")
            items = await self.scraper.search(search_cfg)

            if not items:
                await asyncio.sleep(self.config.request_delay)
                return []

            new_items = self.storage.filter_new_items(items)

            if new_items:
                logger.info(
                    f"-> '{search_cfg.keywords}': {len(new_items)} new item(s) found!"
                )

                if dry_run:
                    for item in new_items:
                        logger.info(f"[DRY-RUN] Item detected: {item.name} ({item.price}¥)")
                else:
                    for item in new_items:
                        if self.stop_event.is_set():
                            break
                        await self.notifier.notify_item(item)

                self.storage.mark_as_seen(new_items)
            else:
                logger.debug(f"-> '{search_cfg.keywords}': no new items.")

            await asyncio.sleep(self.config.request_delay)
            return new_items

    async def run_once(self, dry_run: bool = False) -> int:
        """Execute one complete sweep over all configured searches."""
        if not self.config.searches:
            logger.warning("No searches configured.")
            return 0

        semaphore = asyncio.Semaphore(self.config.max_concurrent_requests)
        total_new = 0

        for search_cfg in self.config.searches:
            if self.stop_event.is_set():
                break
            found = await self.scan_single_query(search_cfg, semaphore, dry_run=dry_run)
            total_new += len(found)

        return total_new

    async def start(self, dry_run: bool = False) -> None:
        """Main loop: scans repeatedly until stop_event is triggered."""
        logger.info(
            f"Starting scan loop ({len(self.config.searches)} searches, delay={self.config.delay}s)..."
        )

        while not self.stop_event.is_set():
            cycle_start = asyncio.get_running_loop().time()
            try:
                new_items_count = await self.run_once(dry_run=dry_run)
                if new_items_count == 0:
                    logger.info("No new items found on Mercari.")
            except Exception:
                logger.exception("Unexpected error during scan cycle")

            if self.stop_event.is_set():
                break

            elapsed = asyncio.get_running_loop().time() - cycle_start
            remaining_sleep = max(0.0, self.config.delay - elapsed)

            logger.info(f"Sleeping for {remaining_sleep:.1f}s before next scan...")

            try:
                await asyncio.wait_for(self.stop_event.wait(), timeout=remaining_sleep)
                break
            except asyncio.TimeoutError:
                pass

        logger.info("Scan loop finished.")
