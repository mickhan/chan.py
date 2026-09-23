from __future__ import annotations

from threading import Lock, RLock

from .base import ProviderAdapter
from .errors import UnsupportedPeriodError


class ProviderRegistry:
    def __init__(self, providers: list[ProviderAdapter]):
        self.providers = list(providers)
        self._lock_init = Lock()
        self._locks: dict[str, RLock] = {}

    def resolve(self, market: str, instrument: str, period: str, adjustment: str) -> ProviderAdapter:
        if market == "cn":
            for provider in self.providers:
                if provider.supports(instrument, period, adjustment):
                    return provider
        raise UnsupportedPeriodError(
            f"标的 {instrument} 不支持 {period} 周期和 {adjustment} 复权方式"
        )

    def capabilities(self, market: str, instrument: str | None = None):
        from web.backend.schemas import CapabilityResponse
        if market != "cn":
            raise UnsupportedPeriodError(f"不支持市场 {market}")
        if instrument:
            from web.backend.instruments import instrument_kind
            try:
                instrument_kind(instrument)
            except ValueError:
                return CapabilityResponse(market=market, sources=[], periods=[])
        periods = [item for provider in self.providers for item in provider.capabilities(market, instrument)]
        sources = list(dict.fromkeys(item.source for item in periods))
        return CapabilityResponse(market=market, sources=sources, periods=periods)

    def search(self, market: str, query: str, limit: int = 20):
        if market != "cn":
            raise UnsupportedPeriodError(f"不支持市场 {market}")
        if not 1 <= limit <= 20:
            raise ValueError("limit must be between 1 and 20")
        found = []
        seen = set()
        for provider in self.providers:
            with self.guard(provider):
                options = provider.search_instruments(market, query, limit)
            for item in options:
                if item.instrument not in seen:
                    seen.add(item.instrument)
                    found.append(item)
                if len(found) >= limit:
                    return found
        return found

    def guard(self, provider: ProviderAdapter) -> RLock:
        with self._lock_init:
            return self._locks.setdefault(provider.source_id, RLock())
