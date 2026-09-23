from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from Common.CEnum import AUTYPE, KL_TYPE
from KLine.KLine_Unit import CKLine_Unit

if TYPE_CHECKING:
    from web.backend.schemas import AnalysisRequest, InstrumentOption, PeriodCapability


class ProviderAdapter(Protocol):
    source_id: str
    chan_data_source: str

    def supports(self, instrument: str, period: str, adjustment: str) -> bool: ...
    def capabilities(self, market: str, instrument: str | None = None) -> list[PeriodCapability]: ...
    def search_instruments(self, market: str, query: str, limit: int) -> list[InstrumentOption]: ...
    def fetch_klines(self, request: AnalysisRequest, max_bars: int) -> list[CKLine_Unit]: ...
    def period_to_kl_type(self, period: str) -> KL_TYPE: ...
    def adjustment_to_autype(self, adjustment: str) -> AUTYPE: ...


def read_klines(api_cls, max_bars: int, **kwargs) -> list[CKLine_Unit]:
    """Fully consume a provider under its own init/close lifecycle."""
    import requests

    from .errors import ProviderError, SourceDataError, SourceTimeoutError

    try:
        try:
            api_cls.do_init()
            api = api_cls(**kwargs)
            result = []
            for row in api.get_kl_data():
                result.append(row)
                if len(result) > max_bars:
                    break
            return result
        finally:
            api_cls.do_close()
    except ProviderError:
        raise
    except (TimeoutError, requests.Timeout) as exc:
        raise SourceTimeoutError("行情数据源请求超时") from exc
    except Exception as exc:
        raise SourceDataError(str(exc) or "行情数据源读取失败") from exc
