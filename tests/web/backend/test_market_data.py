from contextlib import nullcontext
from datetime import datetime
from unittest.mock import Mock
from zoneinfo import ZoneInfo

from Common.CEnum import DATA_FIELD
from Common.CTime import CTime
from KLine.KLine_Unit import CKLine_Unit
from web.backend.live_quotes import QuoteSnapshot
from web.backend.market_data import MarketDataService
from web.backend.schemas import AnalysisRequest

NOW = datetime(2026, 9, 24, 9, 54, tzinfo=ZoneInfo('Asia/Shanghai'))


def quote(at, close=10, volume=100):
    return dict(day=at, open=10, high=max(11, close), low=9, close=close, volume=volume)


def bar(at, close=10, volume=100):
    t = datetime.fromisoformat(at)
    return CKLine_Unit({DATA_FIELD.FIELD_TIME: CTime(t.year,t.month,t.day,t.hour,t.minute,auto=False),
        DATA_FIELD.FIELD_OPEN:10, DATA_FIELD.FIELD_HIGH:max(11,close), DATA_FIELD.FIELD_LOW:9,
        DATA_FIELD.FIELD_CLOSE:close, DATA_FIELD.FIELD_VOLUME:volume})


def request(period='5m', adjustment='none'):
    return AnalysisRequest(market='cn', instrument='sh.563360', period=period,
                           begin_time='2026-09-23', end_time='2026-09-24', adjustment=adjustment)


def setup(history, quotes):
    provider = Mock(source_id='baostock')
    provider.fetch_klines.side_effect = lambda req, limit: history.get(req.period, [])
    registry = Mock()
    registry.resolve.return_value = provider
    registry.guard.return_value = nullcontext()
    live = Mock()
    live.get.return_value = QuoteSnapshot(quotes, NOW)
    return MarketDataService(registry, None, live, now=lambda: NOW, min_interval=0), provider, live


def test_minute_merge_reuses_history_and_marks_forming_bar_without_caching_it_as_history():
    service, provider, live = setup({'5m':[bar('2026-09-23 15:00:00')]}, [
        quote('2026-09-23 15:00:00'), quote('2026-09-24 09:50:00'), quote('2026-09-24 09:55:00', 12)])
    result = service.load(request(), provider, 5000)
    assert len(result.rows) == 3
    assert result.rows[-1].close == 12
    assert result.provisional == {'2026-09-24T09:55:00+08:00'}
    assert result.source == 'baostock+sina'
    assert str(provider.fetch_klines.call_args.args[0].end_time) == '2026-09-23'


def test_price_mismatch_does_not_splice_incompatible_series():
    service, provider, _ = setup({'5m':[bar('2026-09-23 15:00:00')]}, [
        quote('2026-09-23 15:00:00', 20), quote('2026-09-24 09:55:00', 21)])
    result = service.load(request(), provider, 5000)
    assert len(result.rows) == 1
    assert result.status == 'delayed'
    assert any('不一致' in warning for warning in result.warnings)


def test_adjusted_history_never_receives_unadjusted_live_prices():
    service, provider, live = setup({'5m':[bar('2026-09-23 15:00:00')]}, [])
    result = service.load(request(adjustment='qfq'), provider, 5000)
    live.get.assert_not_called()
    assert result.source == 'baostock'
    assert result.status == 'delayed'
    assert result.warnings


def test_daily_aggregation_includes_current_partial_day_and_checks_full_prior_day():
    times = ['10:00','10:30','11:00','11:30','13:30','14:00','14:30','15:00']
    quotes = [quote(f'2026-09-23 {t}:00') for t in times] + [quote('2026-09-24 10:00:00', 12, 350)]
    service, provider, live = setup({'1d':[bar('2026-09-23',volume=800)]}, quotes)
    result = service.load(request('1d'), provider, 5000)
    assert len(result.rows) == 2
    assert result.rows[-1].close == 12
    assert result.rows[-1].trade_info.metric[DATA_FIELD.FIELD_VOLUME] == 350
    assert result.provisional == {'2026-09-24T00:00:00+08:00'}
    live.get.assert_called_once_with('sh.563360', '30m')
    # A recent window starting at 10:30 cannot produce a full daily candle.
    live.get.return_value = QuoteSnapshot([quote('2026-09-24 10:30:00')], NOW)
    assert len(service.load(request('1d'), provider, 5000).rows) == 1


def test_weekly_aggregation_keeps_full_week_open_high_low_close_and_volume():
    quotes = [quote(f'2026-09-23 {t}:00') for t in ['10:00','10:30','11:00','11:30','13:30','14:00','14:30','15:00']]
    quotes.append(quote('2026-09-24 10:00:00', 12, 350))
    daily = [bar(f'2026-09-{day}', volume=800) for day in [21,22,23]]
    service, provider, _ = setup({'1w':[], '1d':daily}, quotes)
    result = service.load(request('1w').model_copy(update={'begin_time':datetime(2026,9,21).date()}), provider, 5000)
    assert len(result.rows) == 1
    assert result.rows[0].close == 12
    assert result.rows[0].trade_info.metric[DATA_FIELD.FIELD_VOLUME] == 2750
    assert result.provisional == {'2026-09-24T00:00:00+08:00'}


def test_historical_only_request_does_not_query_live_source():
    service, provider, live = setup({'5m':[bar('2026-09-23 15:00:00')]}, [])
    result = service.load(request().model_copy(update={'end_time':datetime(2026,9,23).date()}), provider, 5000)
    live.get.assert_not_called()
    assert result.status == 'historical'


def test_cached_forming_candle_is_not_finalized_just_because_wall_clock_passed_its_end():
    service, provider, live = setup({'30m':[bar('2026-09-23 15:00:00')]}, [])
    service.now = lambda: NOW.replace(hour=10, minute=0, second=5)
    live.get.return_value = QuoteSnapshot([quote('2026-09-23 15:00:00'), quote('2026-09-24 10:00:00')],
                                         NOW.replace(hour=9, minute=59, second=50))
    result = service.load(request('30m'), provider, 5000)
    assert result.provisional == {'2026-09-24T10:00:00+08:00'}


def test_index_live_request_preserves_closed_history_in_existing_cache(tmp_path):
    from datetime import date
    from web.backend.kline_cache import KlineCache
    cache = KlineCache(tmp_path / 'market.db', today=lambda: date(2026,9,30))
    item = request('30m').model_copy(update={'instrument':'sh.000001', 'begin_time':date(2026,9,1)})
    history = [bar('2026-09-01 10:00:00'), bar('2026-09-23 15:00:00')]
    cache.get('sina', item.model_copy(update={'end_time':date(2026,9,23)}), 5000, lambda *_: history)
    service, provider, _ = setup({}, [quote('2026-09-23 15:00:00'), quote('2026-09-24 10:00:00')])
    provider.source_id = 'sina'
    service.cache = cache
    result = service.load(item, provider, 5000)
    assert [r.time.day for r in result.rows] == [1,23,24]
    provider.fetch_klines.assert_not_called()


def test_history_failures_back_off_instead_of_repeating_requests():
    import pytest
    from datetime import timedelta
    from web.backend.providers.errors import SourceTimeoutError
    service, provider, _ = setup({}, [])
    provider.fetch_klines.side_effect = SourceTimeoutError('timeout')
    item = request().model_copy(update={'end_time':datetime(2026,9,23).date()})
    for _ in range(2):
        with pytest.raises(SourceTimeoutError):
            service.load(item,provider,5000)
    assert provider.fetch_klines.call_count == 1
    service.now = lambda: NOW + timedelta(seconds=61)
    with pytest.raises(SourceTimeoutError):
        service.load(item,provider,5000)
    assert provider.fetch_klines.call_count == 2
