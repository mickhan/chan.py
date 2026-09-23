from __future__ import annotations

from collections.abc import Callable
from datetime import date

from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE

from web.backend.capabilities import ADJUSTMENT_TO_AUTYPE, PERIOD_TO_KL_TYPE
from web.backend.providers.base import read_klines
from web.backend.instruments import filter_instruments, instrument_kind, normalize_baostock_record
from web.backend.schemas import InstrumentOption, PeriodCapability


class BaoStockAdapter:
    source_id = "baostock"
    chan_data_source = DATA_SRC.BAO_STOCK
    _stock_periods = ("5m", "15m", "30m", "60m", "1d", "1w", "1mo")
    _index_periods = ("1d", "1w", "1mo")

    def __init__(self, catalog_loader: Callable[[], list[InstrumentOption]] | None = None, api_cls=None,
                 metadata_loader: Callable[[str], date | None] | None = None):
        self.catalog_loader = catalog_loader or self._load_catalog
        self.api_cls = api_cls
        self.metadata_loader = metadata_loader or self._load_listing_date
        self._listing_cache: dict[str, date | None] = {}
        self._catalog_cache: list[InstrumentOption] | None = None

    def supports(self, instrument: str, period: str, adjustment: str) -> bool:
        try:
            kind = instrument_kind(instrument)
        except ValueError:
            return False
        if kind == "index":
            return period in self._index_periods and adjustment == "none"
        return period in self._stock_periods and adjustment in ADJUSTMENT_TO_AUTYPE

    def capabilities(self, market: str, instrument: str | None = None) -> list[PeriodCapability]:
        if market != "cn":
            return []
        kinds = (instrument_kind(instrument),) if instrument else ("stock", "index")
        result = []
        first = self.available_since(instrument) if instrument else None
        for kind in kinds:
            periods = self._stock_periods if kind == "stock" else self._index_periods
            adjustments = ["none", "qfq", "hfq"] if kind == "stock" else ["none"]
            result.extend(PeriodCapability(
                market="cn", source=self.source_id, kind=kind, period=period,
                adjustments=adjustments, first_available=first if kind == "stock" else None, instrument=instrument,
            ) for period in periods)
        return result

    def available_since(self, instrument: str) -> date | None:
        if instrument_kind(instrument) != "stock":
            return None
        if instrument not in self._listing_cache:
            self._listing_cache[instrument] = self.metadata_loader(instrument)
        return self._listing_cache[instrument]

    @staticmethod
    def _load_listing_date(instrument: str) -> date | None:
        import baostock as bs
        from DataAPI.BaoStockAPI import CBaoStock
        from .errors import SourceDataError

        try:
            CBaoStock.do_init()
            rows = bs.query_stock_basic(code=instrument)
            if rows.error_code != "0":
                raise SourceDataError("标的上市日期读取失败")
            if not rows.next():
                raise SourceDataError("找不到标的上市日期")
            value = rows.get_row_data()[rows.fields.index("ipoDate")]
            return date.fromisoformat(value) if value else None
        except SourceDataError:
            raise
        except Exception as exc:
            raise SourceDataError("标的上市日期读取失败") from exc
        finally:
            CBaoStock.do_close()

    def _load_catalog(self) -> list[InstrumentOption]:
        import baostock as bs
        from DataAPI.BaoStockAPI import CBaoStock

        result = []
        CBaoStock.do_init()
        try:
            rows = bs.query_stock_basic()
            if rows.error_code != "0":
                raise RuntimeError(rows.error_msg)
            while rows.next():
                try:
                    result.append(normalize_baostock_record(rows.get_row_data()))
                except ValueError:
                    continue
        finally:
            CBaoStock.do_close()
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
        from DataAPI.BaoStockAPI import CBaoStock

        if not self.supports(request.instrument, request.period, request.adjustment):
            from .errors import UnsupportedPeriodError
            raise UnsupportedPeriodError("BaoStock 不支持该标的和周期")
        return read_klines(
            self.api_cls or CBaoStock, max_bars,
            code=request.instrument,
            k_type=self.period_to_kl_type(request.period),
            begin_date=request.begin_time.isoformat(),
            end_date=request.end_time.isoformat(),
            autype=self.adjustment_to_autype(request.adjustment),
        )
