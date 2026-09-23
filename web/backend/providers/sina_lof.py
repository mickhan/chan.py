"""Listed LOF catalog and unadjusted daily K-lines from Sina."""
from __future__ import annotations

from collections.abc import Callable

from Common.CEnum import AUTYPE, KL_TYPE
from DataAPI.SinaFundAPI import CSinaFund
from web.backend.catalog_cache import CatalogCache
from web.backend.instruments import filter_instruments, instrument_kind, normalize_sina_lof_record
from web.backend.providers.base import read_klines
from web.backend.schemas import InstrumentOption, PeriodCapability

from .errors import UnsupportedPeriodError


class SinaLofAdapter:
    source_id = 'sina-lof'
    chan_data_source = 'custom:SinaFundAPI.CSinaFund'

    def __init__(self, catalog_loader: Callable[[], list[InstrumentOption]] | None = None,
                 api_cls=None, catalog_cache: CatalogCache | None = None):
        self.catalog_loader = catalog_loader or self._load_catalog
        self.catalog_cache = catalog_cache or (CatalogCache() if catalog_loader is None else None)
        self.api_cls = api_cls or CSinaFund
        self._catalog_cache: list[InstrumentOption] | None = None

    def supports(self, instrument: str, period: str, adjustment: str) -> bool:
        try:
            return instrument_kind(instrument) == 'lof' and period == '1d' and adjustment == 'none'
        except ValueError:
            return False

    def capabilities(self, market: str, instrument: str | None = None) -> list[PeriodCapability]:
        if market != 'cn' or (instrument and not self.supports(instrument, '1d', 'none')):
            return []
        return [PeriodCapability(market='cn', source=self.source_id, kind='lof', period='1d',
                                 adjustments=['none'], instrument=instrument)]

    @staticmethod
    def _load_catalog() -> list[InstrumentOption]:
        import akshare as ak
        rows = ak.fund_etf_category_sina(symbol='LOF基金')
        result = []
        for row in rows.to_dict('records'):
            try:
                result.append(normalize_sina_lof_record(row))
            except ValueError:
                continue
        return result

    def search_instruments(self, market: str, query: str, limit: int) -> list[InstrumentOption]:
        if market != 'cn':
            return []
        if self.catalog_cache is not None:
            from .registry import source_lock
            self._catalog_cache = self.catalog_cache.get(
                self.source_id, self.catalog_loader, lambda: source_lock(self.source_id))
        elif self._catalog_cache is None:
            self._catalog_cache = self.catalog_loader()
        return filter_instruments(self._catalog_cache, query, limit)

    def period_to_kl_type(self, period: str) -> KL_TYPE:
        if period != '1d':
            raise UnsupportedPeriodError('新浪 LOF 仅支持日线')
        return KL_TYPE.K_DAY

    def adjustment_to_autype(self, adjustment: str) -> AUTYPE:
        if adjustment != 'none':
            raise UnsupportedPeriodError('新浪 LOF 不支持复权')
        return AUTYPE.NONE

    def fetch_klines(self, request, max_bars: int):
        if not self.supports(request.instrument, request.period, request.adjustment):
            raise UnsupportedPeriodError('新浪 LOF 不支持该标的或周期')
        return read_klines(self.api_cls, max_bars, code=request.instrument.replace('.', ''),
                           k_type=KL_TYPE.K_DAY, begin_date=request.begin_time.isoformat(),
                           end_date=request.end_time.isoformat(), autype=AUTYPE.NONE)
