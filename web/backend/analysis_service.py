"""Fetch one period, compute Chan structures, and return a stable chart DTO."""
import logging
from datetime import date

from Chan import CChan
from ChanConfig import CChanConfig
from Common.ChanException import CChanException

from .providers.errors import ProviderError, DateRangeUnavailableError, SourceDataError
from .schemas import ErrorResponse
from .serializers import serialize_chan
from .market_calendar import has_missing_trading_period

_log = logging.getLogger(__name__)


class AnalysisFailure(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def map_analysis_error(error: Exception) -> ErrorResponse:
    if isinstance(error, (ProviderError, AnalysisFailure)):
        message = '行情数据源读取失败，请稍后重试' if isinstance(error, SourceDataError) else error.message
        return ErrorResponse(code=error.code, message=message,
                             supported_options=getattr(error, 'supported_options', None))
    if isinstance(error, CChanException):
        return ErrorResponse(code='ANALYSIS_ERROR', message='缠论计算失败，请调整标的或时间范围后重试')
    return ErrorResponse(code='ANALYSIS_ERROR', message='分析失败，请稍后重试')


class AnalysisService:
    def __init__(self, registry, chan_factory=CChan, max_bars: int = 5000,
                 calendar_checker=has_missing_trading_period):
        self.registry = registry
        self.chan_factory = chan_factory
        self.max_bars = max_bars
        self.calendar_checker = calendar_checker

    def analyze(self, request):
        provider = self.registry.resolve(request.market, request.instrument,
                                         request.period, request.adjustment)
        with self.registry.guard(provider):
            available_since = getattr(provider, 'available_since', lambda _code: None)(request.instrument)
            if available_since and request.begin_time < available_since:
                raise DateRangeUnavailableError('请求开始日期早于标的上市日期')
            klines = provider.fetch_klines(request, self.max_bars)
        if not klines:
            raise AnalysisFailure('NO_DATA', '所选区间没有 K 线数据')
        if len(klines) > self.max_bars:
            raise AnalysisFailure('INVALID_REQUEST', f'最多可分析 {self.max_bars} 根 K 线，请缩短时间范围')
        first = klines[0].time
        first_date = date(first.year, first.month, first.day)
        if first_date > request.begin_time:
            with self.registry.guard_source('baostock'):
                missing = self.calendar_checker(request.begin_time, first_date, request.period)
            if missing:
                raise DateRangeUnavailableError('请求开始日期早于数据源可提供的历史范围')
        kl_type = provider.period_to_kl_type(request.period)
        autype = provider.adjustment_to_autype(request.adjustment)
        try:
            chan = self.chan_factory(code=request.instrument, lv_list=[kl_type],
                                     config=CChanConfig(), autype=autype,
                                     defer_load=True)
            chan.trigger_load({kl_type: klines})
            return serialize_chan(chan, request, provider.source_id, kl_type)
        except Exception:
            _log.exception('Chan analysis failed for %s %s', request.instrument, request.period)
            raise
