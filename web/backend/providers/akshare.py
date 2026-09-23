from __future__ import annotations

from collections.abc import Callable

from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE

from web.backend.capabilities import ADJUSTMENT_TO_AUTYPE, PERIOD_TO_KL_TYPE
from web.backend.providers.base import read_klines
from web.backend.instruments import filter_instruments, instrument_kind, normalize_akshare_record
from web.backend.schemas import InstrumentOption, PeriodCapability


class AkShareAdapter:
    source_id = "akshare"
    chan_data_source = DATA_SRC.AKSHARE
    _stock_periods = ("1d", "1w", "1mo")

    def __init__(self, catalog_loader: Callable[[], list[InstrumentOption]] | None = None, api_cls=None):
        self.catalog_loader = catalog_loader or self._load_catalog
        self.api_cls = api_cls
        self._catalog_cache: list[InstrumentOption] | None = None

    def supports(self, instrument: str, period: str, adjustment: str) -> bool:
        try:
            kind = instrument_kind(instrument)
        except ValueError:
            return False
        return kind == "stock" and period in self._stock_periods and adjustment in ADJUSTMENT_TO_AUTYPE

    def capabilities(self, market: str, instrument: str | None = None) -> list[PeriodCapability]:
        if market != "cn":
            return []
        if instrument and instrument_kind(instrument) != "stock":
            return []
        return [PeriodCapability(
            market="cn", source=self.source_id, kind="stock", period=period,
            adjustments=["none", "qfq", "hfq"], instrument=instrument,
        ) for period in self._stock_periods]

    def _load_catalog(self) -> list[InstrumentOption]:
        import akshare as ak
        rows = ak.stock_info_a_code_name()
        result = []
        for row in rows.to_dict("records"):
            try:
                result.append(normalize_akshare_record(row))
            except ValueError:
                continue
        return result

    def search_instruments(self, market: str, query: str, limit: int) -> list[InstrumentOption]:
        if market != "cn":
            return []
        if self._catalog_cache is None:
            self._catalog_cache = self.catalog_loader()
        return filter_instruments(self._catalog_cache, query, limit)

    def period_to_kl_type(self, period: str) -> KL_TYPE:
        return PERIOD_TO_KL_TYPE[period]

    def adjustment_to_autype(self, adjustment: str) -> AUTYPE:
        return ADJUSTMENT_TO_AUTYPE[adjustment]

    def fetch_klines(self, request, max_bars: int):
        from DataAPI.AkshareAPI import CAkshare

        if not self.supports(request.instrument, request.period, request.adjustment):
            from .errors import UnsupportedPeriodError
            raise UnsupportedPeriodError("AkShare 不支持该标的和周期")
        return read_klines(
            self.api_cls or CAkshare, max_bars,
            code=request.instrument.split(".", 1)[1],
            k_type=self.period_to_kl_type(request.period),
            begin_date=request.begin_time.isoformat(),
            end_date=request.end_time.isoformat(),
            autype=self.adjustment_to_autype(request.adjustment),
        )
