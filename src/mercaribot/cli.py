"""Command-line interface, logging setup with secret redaction, and application lifecycle."""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys
from pathlib import Path

from mercaribot import __version__
from mercaribot.config import load_config
from mercaribot.currency import CurrencyService
from mercaribot.engine.coordinator import ScanCoordinator
from mercaribot.notifier.telegram import TelegramNotifier
from mercaribot.scraper.mercari import MercariClient
from mercaribot.security.logging import SecretMaskingFilter
from mercaribot.storage.database import SQLiteStorage

logger = logging.getLogger("mercaribot")


def setup_logging(verbose: bool = False) -> None:
    """Configure structured logging to console with automatic secret redaction."""
    level = logging.DEBUG if verbose else logging.INFO

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    # OWASP A09: automatic redaction of all sensitive API tokens in logs
    handler.addFilter(SecretMaskingFilter())

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Reduce verbosity of httpx and httpcore to prevent leaking raw URLs
    logging.getLogger("httpx").setLevel(logging.WARNING if not verbose else logging.DEBUG)
    logging.getLogger("httpcore").setLevel(logging.WARNING if not verbose else logging.DEBUG)


async def async_main(args: argparse.Namespace) -> int:
    """Main async entry point."""
    base_dir = Path.cwd()
    config_file = Path(args.config) if args.config else base_dir / "config.toml"
    env_file = Path(args.env) if args.env else base_dir / ".env"

    try:
        cfg = load_config(config_file=config_file, env_file=env_file, base_dir=base_dir)
    except (ValueError, FileNotFoundError, OSError) as e:
        logger.error(f"Configuration error: {e}")
        return 1

    storage = SQLiteStorage(db_path=cfg.db_path)

    legacy_cache = base_dir / "scraped_cache.json"
    if args.import_cache:
        target = Path(args.import_cache)
        count = storage.import_from_json(target)
        logger.info(f"Manual import completed: {count} items imported.")
        return 0

    if storage.get_total_seen_count() == 0 and legacy_cache.exists():
        logger.info(f"Empty database detected. Automatic migration from {legacy_cache.name}...")
        storage.import_from_json(legacy_cache)

    currency_service = CurrencyService(
        fallback_rate=cfg.change_rate,
        target_currency=cfg.target_currency,
        auto_fetch=cfg.auto_currency,
    )

    scraper = MercariClient()
    notifier = TelegramNotifier(
        token=cfg.telegram_token,
        chat_id=cfg.telegram_chat_id,
        currency_service=currency_service,
        download_photos=cfg.download_photos,
        template=cfg.message_template,
    )

    if args.test_telegram:
        logger.info("Testing Telegram connection...")
        ok = await notifier.send_message(
            "🔔 <b>MercariBOT Test</b>\nTelegram connection successful!",
            parse_mode="HTML",
        )
        await scraper.aclose()
        await notifier.aclose()
        if ok:
            logger.info("Test message sent successfully to Telegram!")
            return 0
        else:
            logger.error("Failed to send test message. Check your TELEGRAM_TOKEN and TELEGRAM_CHAT_ID.")
            return 1

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def handle_signal():
        logger.info("Interrupt signal received. Graceful shutdown in progress...")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, handle_signal)
        except NotImplementedError:
            pass

    coordinator = ScanCoordinator(
        config=cfg,
        storage=storage,
        scraper=scraper,
        notifier=notifier,
        stop_event=stop_event,
    )

    try:
        if not args.dry_run:
            await notifier.send_startup_message()
        else:
            logger.info("--- DRY-RUN MODE ACTIVE: No Telegram alerts will be sent ---")

        await coordinator.start(dry_run=args.dry_run)
    except asyncio.CancelledError:
        pass
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt detected.")
    finally:
        logger.info("Cleaning up network connections...")
        await scraper.aclose()
        await notifier.aclose()
        logger.info("MercariBOT stopped cleanly. See you soon!")

    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description=f"MercariBOT v{__version__} - Monitors Mercari Japan listings and notifies via Telegram."
    )
    parser.add_argument(
        "-c", "--config", type=str, help="Path to custom config.toml file."
    )
    parser.add_argument(
        "-e", "--env", type=str, help="Path to custom .env file."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate search without sending alerts to Telegram.",
    )
    parser.add_argument(
        "--test-telegram",
        action="store_true",
        help="Send a test notification to Telegram and exit.",
    )
    parser.add_argument(
        "--import-cache",
        type=str,
        help="Migrate IDs from legacy JSON cache to SQLite and exit.",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose debug logs."
    )
    return parser.parse_args(argv)


def run() -> None:
    """Standard console entrypoint."""
    args = parse_args(sys.argv[1:])
    setup_logging(verbose=args.verbose)

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        exit_code = asyncio.run(async_main(args))
        sys.exit(exit_code)
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    run()
