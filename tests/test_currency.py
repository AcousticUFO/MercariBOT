import pytest

from mercaribot.currency import CurrencyService


@pytest.mark.asyncio
async def test_currency_fallback():
    # When auto_fetch = False, it should use the fallback rate
    service = CurrencyService(fallback_rate=0.006, target_currency="EUR", auto_fetch=False)
    assert service.symbol == "€"

    rate = await service.get_exchange_rate()
    assert rate == 0.006

    converted, symbol = await service.convert(1000)
    assert converted == 6.0
    assert symbol == "€"


@pytest.mark.asyncio
async def test_currency_symbols():
    service_usd = CurrencyService(target_currency="USD", auto_fetch=False)
    assert service_usd.symbol == "$"

    service_gbp = CurrencyService(target_currency="GBP", auto_fetch=False)
    assert service_gbp.symbol == "£"
