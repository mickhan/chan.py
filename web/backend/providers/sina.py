from __future__ import annotations

from datetime import date

from Common.CEnum import AUTYPE, KL_TYPE
from DataAPI.SinaAPI import CSina

from web.backend.instruments import instrument_kind
from web.backend.providers.base import read_klines
from web.backend.schemas import PeriodCapability

from .errors import UnsupportedPeriodError


class SinaAdapter:
    source_id = "sina"
    chan_data_source = "custom:SinaAPI.CSina"

    def __init__(self, http_get=None, now=None, api_cls=None):
        self.http_get = http_get
        self.now = now
        self.api_cls = api_cls or CSina

    def supports(self, instrument: str, period: str, adjustment: str) -> bool:
        try:
            kind = instrument_kind(instrument)
        except ValueError:
            return False
        return kind == "index" and period == "30m" and adjustment == "none"

    def capabilities(self, market: str, instrument: str | None = None) -> list[PeriodCapability]:
        if market != "cn" or (instrument and not self.supports(instrument, "30m", "none")):
            return []
        first = last = None
        if instrument:
            bars = read_klines(
                self.api_cls, 1970, code=instrument, k_type=KL_TYPE.K_30M,
                begin_date=None, end_date=None, autype=AUTYPE.NONE,
                http_get=self.http_get, now=self.now,
            )
            if not bars:
                return []
            first = date(bars[0].time.year, bars[0].time.month, bars[0].time.day)
            last = date(bars[-1].time.year, bars[-1].time.month, bars[-1].time.day)
        return [PeriodCapability(
            market="cn", source=self.source_id, kind="index", period="30m",
            adjustments=["none"], first_available=first, last_available=last,
            max_bars=1970, instrument=instrument,
        )]

    def search_instruments(self, market, query, limit):
        return []

    def period_to_kl_type(self, period: str) -> KL_TYPE:
        if period != "30m":
            raise UnsupportedPeriodError("新浪指数行情仅支持 30 分钟线")
        return KL_TYPE.K_30M

    def adjustment_to_autype(self, adjustment: str) -> AUTYPE:
        if adjustment != "none":
            raise UnsupportedPeriodError("指数不支持复权")
        return AUTYPE.NONE

    def fetch_klines(self, request, max_bars: int):
        if not self.supports(request.instrument, request.period, request.adjustment):
            raise UnsupportedPeriodError("新浪指数行情不支持该标的或周期")
        return read_klines(
            self.api_cls, max_bars, code=request.instrument, k_type=KL_TYPE.K_30M,
            begin_date=request.begin_time.isoformat(), end_date=request.end_time.isoformat(),
            autype=AUTYPE.NONE, http_get=self.http_get, now=self.now,
        )
