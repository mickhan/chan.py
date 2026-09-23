from __future__ import annotations

from threading import Lock, RLock

from .base import ProviderAdapter
from .errors import ProviderError, SourceDataError, UnsupportedPeriodError


_lock_init = Lock()
_locks: dict[str, RLock] = {}


class ProviderRegistry:
    def __init__(self, providers: list[ProviderAdapter]):
        self.providers = list(providers)

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
        try:
            periods = []
            for provider in self.providers:
                with self.guard(provider):
                    periods.extend(provider.capabilities(market, instrument))
        except ProviderError:
            raise
        except Exception as exc:
            raise SourceDataError('行情能力读取失败') from exc
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
                try:
                    options = provider.search_instruments(market, query, limit)
                except ProviderError:
                    raise
                except Exception as exc:
                    raise SourceDataError('标的目录读取失败') from exc
            for item in options:
                if item.instrument not in seen:
                    seen.add(item.instrument)
                    found.append(item)
                if len(found) >= limit:
                    return found
        return found

    def guard_source(self, source_id: str) -> RLock:
        with _lock_init:
            return _locks.setdefault(source_id, RLock())

    def guard(self, provider: ProviderAdapter) -> RLock:
        return self.guard_source(provider.source_id)


def default_registry() -> ProviderRegistry:
    from .akshare import AkShareAdapter
    from .baostock import BaoStockAdapter
    from .sina import SinaAdapter
    return ProviderRegistry([BaoStockAdapter(), AkShareAdapter(), SinaAdapter()])
