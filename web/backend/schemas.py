from __future__ import annotations

from datetime import date
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AnalysisRequest(StrictModel):
    market: Literal["cn"]
    instrument: str = Field(min_length=1)
    period: str = Field(min_length=1)
    begin_time: date
    end_time: date
    adjustment: str = Field(min_length=1)

    @model_validator(mode="after")
    def check_date_range(self) -> Self:
        if self.begin_time > self.end_time:
            raise ValueError("begin_time must not be later than end_time")
        return self


class InstrumentOption(StrictModel):
    market: str
    instrument: str
    name: str
    exchange: str
    kind: Literal["stock", "index"]


class PeriodCapability(StrictModel):
    market: str
    source: str
    kind: Literal["stock", "index"]
    period: str
    adjustments: list[str]
    first_available: date | None = None
    last_available: date | None = None
    max_bars: int = 5000
    instrument: str | None = None


class CapabilityResponse(StrictModel):
    market: str
    sources: list[str]
    periods: list[PeriodCapability]


class Candle(StrictModel):
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class MacdPoint(StrictModel):
    time: str
    diff: float
    dea: float
    histogram: float


class Indicators(StrictModel):
    macd: list[MacdPoint]


class LineOverlay(StrictModel):
    start_time: str
    start_price: float
    end_time: str
    end_price: float
    direction: str
    is_sure: bool | None = None


class ZoneOverlay(StrictModel):
    start_time: str
    end_time: str
    lower: float
    upper: float


class BuySellPoint(StrictModel):
    time: str
    price: float
    side: Literal["buy", "sell"]
    type: str
    bi_is_sure: bool


class Overlays(StrictModel):
    bi: list[LineOverlay]
    segments: list[LineOverlay]
    zones: list[ZoneOverlay]
    buy_sell_points: list[BuySellPoint]


class AnalysisMeta(StrictModel):
    instrument: str
    period: str
    source: str
    first_bar: str
    last_bar: str
    bar_count: int


class ChartResponse(StrictModel):
    schema_version: Literal[1]
    request: AnalysisRequest
    meta: AnalysisMeta
    candles: list[Candle]
    indicators: Indicators
    overlays: Overlays


class ErrorResponse(StrictModel):
    code: str
    message: str
    supported_options: list[str] | None = None
