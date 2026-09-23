from contextlib import nullcontext
from datetime import date
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from Common.CEnum import AUTYPE, KL_TYPE
from Common.ChanException import CChanException, ErrCode
from web.backend.analysis_service import AnalysisService, AnalysisFailure, map_analysis_error
from web.backend.app import create_app
from web.backend.kline_cache import KlineCache
from web.backend.providers.errors import SourceTimeoutError, UnsupportedPeriodError
from web.backend.schemas import AnalysisRequest
from test_chan_prefetched import bar


def request():
    return AnalysisRequest(market='cn', instrument='sh.000001', period='1d',
        begin_time='2026-09-01', end_time='2026-09-23', adjustment='none')


def setup(rows=None):
    provider = Mock(source_id='fixture')
    provider.available_since.return_value = None
    provider.period_to_kl_type.return_value = KL_TYPE.K_DAY
    provider.adjustment_to_autype.return_value = AUTYPE.NONE
    provider.fetch_klines.return_value = rows if rows is not None else [bar(i, 10 + i % 4) for i in range(1, 17)]
    registry = Mock()
    registry.resolve.return_value = provider
    registry.guard.return_value = nullcontext()
    registry.guard_source.return_value = nullcontext()
    return registry, provider, AnalysisService(registry, calendar_checker=lambda begin, first, period: first > begin)


def test_success_uses_actual_last_bar_and_guard():
    registry, provider, service = setup()
    result = service.analyze(request())
    assert result.meta.last_bar == '2026-09-16T00:00:00+08:00'
    assert result.meta.bar_count == 16
    provider.fetch_klines.assert_called_once_with(request(), 5000)
    registry.guard.assert_called_once_with(provider)


def test_unsupported_combo_never_fetches():
    registry, provider, service = setup()
    registry.resolve.side_effect = UnsupportedPeriodError('unsupported')
    with pytest.raises(UnsupportedPeriodError):
        service.analyze(request())
    provider.fetch_klines.assert_not_called()


def test_empty_timeout_too_many_and_analysis_errors():
    for rows, code in [([], 'NO_DATA'), ([bar(1, 10), bar(2, 12)], 'INVALID_REQUEST')]:
        _, _, service = setup(rows)
        service.max_bars = 1 if code == 'INVALID_REQUEST' else 5000
        with pytest.raises(AnalysisFailure) as exc:
            service.analyze(request())
        assert exc.value.code == code
    assert map_analysis_error(SourceTimeoutError('timeout')).code == 'SOURCE_TIMEOUT'
    assert map_analysis_error(CChanException('private details', ErrCode.BI_ERR)).code == 'ANALYSIS_ERROR'
    assert 'private details' not in map_analysis_error(CChanException('private details')).message


def test_api_returns_safe_structured_errors():
    registry, _, service = setup([])
    client = TestClient(create_app(registry, service))
    response = client.post('/api/v1/analysis', json=request().model_dump(mode='json'))
    assert response.status_code == 404
    assert response.json()['code'] == 'NO_DATA'
    assert 'Traceback' not in response.text


def test_large_gap_before_first_bar_is_unavailable_history():
    registry, provider, service = setup([bar(20, 10), bar(21, 11)])
    from web.backend.providers.errors import DateRangeUnavailableError
    with pytest.raises(DateRangeUnavailableError):
        service.analyze(request())


def test_even_short_prelisting_gap_is_unavailable():
    from web.backend.providers.errors import DateRangeUnavailableError
    _, _, service = setup([bar(8, 10), bar(9, 11)])
    with pytest.raises(DateRangeUnavailableError):
        service.analyze(request())


def test_known_ipo_date_rejects_begin_even_within_same_week():
    from web.backend.providers.errors import DateRangeUnavailableError
    registry, provider, service = setup([bar(8, 10), bar(9, 11)])
    provider.available_since.return_value = date(2026, 9, 8)
    service.calendar_checker = lambda *_: False
    with pytest.raises(DateRangeUnavailableError):
        service.analyze(request())
    provider.fetch_klines.assert_not_called()


def test_analysis_reuses_persisted_klines_after_service_restart(tmp_path):
    registry, provider, service = setup()
    path = tmp_path / 'market.sqlite3'
    service.cache = KlineCache(path, today=lambda: date(2026, 9, 30))
    first = service.analyze(request())
    restarted = AnalysisService(registry, cache=KlineCache(path, today=lambda: date(2026, 9, 30)),
                                calendar_checker=lambda *_: False)
    second = restarted.analyze(request())
    assert first.meta.bar_count == second.meta.bar_count == 16
    provider.fetch_klines.assert_called_once()


def test_default_app_enables_local_cache():
    from web.backend.app import app
    assert isinstance(app.state.analysis_service.cache, KlineCache)
