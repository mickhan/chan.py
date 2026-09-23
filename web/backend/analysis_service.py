"""Fetch one period, compute Chan structures, and return a stable chart DTO."""
import logging

from Chan import CChan
from ChanConfig import CChanConfig
from Common.ChanException import CChanException

from .providers.errors import ProviderError
from .schemas import ErrorResponse
from .serializers import serialize_chan

_log = logging.getLogger(__name__)


class AnalysisFailure(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def map_analysis_error(error: Exception) -> ErrorResponse:
    if isinstance(error, (ProviderError, AnalysisFailure)):
        return ErrorResponse(code=error.code, message=error.message,
                             supported_options=getattr(error, 'supported_options', None))
    if isinstance(error, CChanException):
        return ErrorResponse(code='ANALYSIS_ERROR', message='缠论计算失败，请调整标的或时间范围后重试')
    return ErrorResponse(code='ANALYSIS_ERROR', message='分析失败，请稍后重试')


class AnalysisService:
    def __init__(self, registry, chan_factory=CChan, max_bars: int = 5000):
        self.registry = registry
        self.chan_factory = chan_factory
        self.max_bars = max_bars

    def analyze(self, request):
        provider = self.registry.resolve(request.market, request.instrument,
                                         request.period, request.adjustment)
        with self.registry.guard(provider):
            klines = provider.fetch_klines(request, self.max_bars)
        if not klines:
            raise AnalysisFailure('NO_DATA', '所选区间没有 K 线数据')
        if len(klines) > self.max_bars:
            raise AnalysisFailure('INVALID_REQUEST', f'最多可分析 {self.max_bars} 根 K 线，请缩短时间范围')
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
