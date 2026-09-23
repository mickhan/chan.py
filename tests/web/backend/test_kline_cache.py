from datetime import date

import pytest

from web.backend.kline_cache import KlineCache
from web.backend.schemas import AnalysisRequest
from test_chan_prefetched import bar


def request(begin, end):
    return AnalysisRequest(market='cn', instrument='sh.000001', period='1d',
        begin_time=begin, end_time=end, adjustment='none')


def test_persists_bars_and_only_fetches_missing_ranges(tmp_path):
    calls = []

    def fetch(item, limit):
        calls.append((item.begin_time, item.end_time))
        return [bar(day, day) for day in range(item.begin_time.day, item.end_time.day + 1)]

    path = tmp_path / 'market.sqlite3'
    cache = KlineCache(path, today=lambda: date(2026, 9, 30))
    first = cache.get('fixture', request(date(2026, 9, 2), date(2026, 9, 4)), 5000, fetch)
    assert [row.close for row in first] == [2.5, 3.5, 4.5]

    restarted = KlineCache(path, today=lambda: date(2026, 9, 30))
    second = restarted.get('fixture', request(date(2026, 9, 3), date(2026, 9, 6)), 5000, fetch)
    assert [row.close for row in second] == [3.5, 4.5, 5.5, 6.5]
    assert calls == [(date(2026, 9, 2), date(2026, 9, 4)),
                     (date(2026, 9, 3), date(2026, 9, 6))]
    restarted.get('fixture', request(date(2026, 9, 2), date(2026, 9, 6)), 5000, fetch)
    assert len(calls) == 2


def test_current_day_is_refreshed_and_failed_fetch_does_not_mark_coverage(tmp_path):
    cache = KlineCache(tmp_path / 'market.sqlite3', today=lambda: date(2026, 9, 5))
    item = request(date(2026, 9, 4), date(2026, 9, 5))
    cache.get('fixture', item, 5000, lambda *_: [bar(4, 4), bar(5, 5)])
    result = cache.get('fixture', item, 5000, lambda *_: [bar(4, 4), bar(5, 50)])
    assert [row.close for row in result] == [4.5, 50.5]

    other = request(date(2026, 9, 1), date(2026, 9, 2))
    def fail(*_):
        raise RuntimeError('source failed')
    with pytest.raises(RuntimeError, match='source failed'):
        cache.get('fixture', other, 5000, fail)
    assert len(cache.get('fixture', other, 5000, lambda *_: [bar(1, 1), bar(2, 2)])) == 2


def test_cache_keys_include_adjustment_and_source(tmp_path):
    cache = KlineCache(tmp_path / 'market.sqlite3', today=lambda: date(2026, 9, 30))
    item = request(date(2026, 9, 1), date(2026, 9, 2))
    calls = []
    def fetch(_item, _limit):
        calls.append(1)
        return [bar(1, 1), bar(2, 2)]
    cache.get('baostock', item, 5000, fetch)
    cache.get('akshare', item, 5000, fetch)
    cache.get('baostock', item.model_copy(update={'adjustment': 'qfq'}), 5000, fetch)
    assert len(calls) == 3


def test_refresh_removes_bars_no_longer_returned_by_source(tmp_path):
    cache = KlineCache(tmp_path / 'market.sqlite3', today=lambda: date(2026, 9, 5))
    item = request(date(2026, 9, 4), date(2026, 9, 5))
    cache.get('fixture', item, 5000, lambda *_: [bar(4, 4), bar(5, 5)])
    rows = cache.get('fixture', item, 5000, lambda *_: [])
    assert rows == []


def test_future_dates_are_not_marked_covered(tmp_path):
    clock = [date(2026, 9, 5)]
    cache = KlineCache(tmp_path / 'market.sqlite3', today=lambda: clock[0])
    item = request(date(2026, 9, 5), date(2026, 9, 7))
    calls = []
    def fetch(part, _):
        calls.append((part.begin_time, part.end_time))
        return [bar(day, day) for day in range(part.begin_time.day, min(part.end_time.day, clock[0].day) + 1)]
    cache.get('fixture', item, 5000, fetch)
    clock[0] = date(2026, 9, 10)
    rows = cache.get('fixture', item, 5000, fetch)
    assert [row.time.day for row in rows] == [5, 6, 7]
    assert len(calls) == 2


def test_recent_past_date_is_refreshed(tmp_path):
    clock = [date(2026, 9, 5)]
    cache = KlineCache(tmp_path / 'market.sqlite3', today=lambda: clock[0])
    item = request(date(2026, 9, 4), date(2026, 9, 5))
    cache.get('fixture', item, 5000, lambda *_: [bar(4, 4), bar(5, 5)])
    clock[0] = date(2026, 9, 6)
    rows = cache.get('fixture', item, 5000, lambda *_: [bar(4, 40), bar(5, 50)])
    assert [row.close for row in rows] == [40.5, 50.5]


def test_truncated_fetch_does_not_claim_full_range(tmp_path):
    cache = KlineCache(tmp_path / 'market.sqlite3', today=lambda: date(2026, 9, 30))
    item = request(date(2026, 9, 1), date(2026, 9, 10))
    calls = []
    def fetch(part, _):
        calls.append(part)
        if len(calls) == 1:
            return [bar(day, day) for day in range(1, 5)]
        return [bar(day, day) for day in range(1, 11)]
    first = cache.get('fixture', item, 3, fetch)
    assert len(first) == 4
    second = cache.get('fixture', item, 10, fetch)
    assert len(second) == 10
    assert len(calls) == 2
