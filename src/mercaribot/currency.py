"""Currency conversion service for MercariBOT."""

from __future__ import annotations

import logging
import time

import httpx

logger = logging.getLogger(__name__)

CURRENCY_SYMBOLS = {
    "EUR": "€",
    "USD": "$",
    "GBP": "£",
    "CAD": "CA$",
    "AUD": "AU$",
    "CHF": "CHF",
    "JPY": "¥",
}


class CurrencyService:
    """Handles JPY currency conversion with live fetching, caching, and fallback."""

    def __init__(
        self,
        fallback_rate: float = 0.0055,
        target_currency: str = "EUR",
        auto_fetch: bool = True,
        cache_duration_seconds: float = 43200.0,  # 12 hours
    ):
        self.fallback_rate = fallback_rate
        self.target_currency = target_currency.upper()
        self.auto_fetch = auto_fetch
        self.cache_duration_seconds = cache_duration_seconds

        self._cached_rate: float | None = None
        self._last_fetch_time: float = 0.0

    @property
    def symbol(self) -> str:
        """Return the symbol for the target currency."""
        return CURRENCY_SYMBOLS.get(self.target_currency, self.target_currency)

    async def get_exchange_rate(self, client: httpx.AsyncClient | None = None) -> float:
        """
        Get the current exchange rate (1 JPY -> X Target Currency).
        Returns cached rate if valid, otherwise attempts to fetch, falling back to fallback_rate.
        """
        now = time.time()
        if (
            self._cached_rate is not None
            and (now - self._last_fetch_time) < self.cache_duration_seconds
        ):
            return self._cached_rate

        if not self.auto_fetch or self.target_currency == "JPY":
            return 1.0 if self.target_currency == "JPY" else self.fallback_rate

        url = f"https://api.frankfurter.dev/v1/latest?from=JPY&to={self.target_currency}"
        try:
            should_close = False
            if client is None:
                client = httpx.AsyncClient(timeout=10.0, follow_redirects=True)
                should_close = True

            try:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    rate = float(data["rates"][self.target_currency])
                    self._cached_rate = rate
                    self._last_fetch_time = now
                    logger.info(
                        f"Exchange rate updated: 1 JPY = {rate:.6f} {self.target_currency}"
                    )
                    return rate
                else:
                    logger.warning(
                        f"Exchange rate API failed (HTTP {response.status_code}), using fallback rate."
                    )
            finally:
                if should_close:
                    await client.aclose()

        except (httpx.HTTPError, ValueError, KeyError) as e:
            logger.warning(
                f"Unable to reach currency API ({e}). Using fallback rate ({self.fallback_rate})."
            )

        self._cached_rate = self.fallback_rate
        self._last_fetch_time = now
        return self.fallback_rate

    async def convert(
        self, price_jpy: int, client: httpx.AsyncClient | None = None
    ) -> tuple[float, str]:
        """
        Convert JPY price to target currency.
        Returns: (converted_price_rounded, currency_symbol)
        """
        rate = await self.get_exchange_rate(client)
        converted = round(price_jpy * rate, 2)
        return converted, self.symbol
