import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
import requests

from web.backend.live_quotes import SinaLiveQuotes

TZ = ZoneInfo('Asia/Shanghai')


def row(at, close=10):
    return dict(day=at, open=10, high=max(11, close), low=9, close=close, volume=100)


class Response:
    def __init__(self, rows):
        self.text = f'=({json.dumps(rows)});'

    def raise_for_status(self):
        pass


def test_shared_snapshot_cools_down_and_replaces_unclosed_bar_with_small_tail(tmp_path):
    clock = [datetime(2026, 9, 24, 9, 54, tzinfo=TZ)]
    calls = []
    def get(**kwargs):
        calls.append(kwargs['params'])
        return Response([row('2026-09-24 09:50:00'), row('2026-09-24 09:55:00', 10 + len(calls))])
    client = SinaLiveQuotes(tmp_path / 'quotes.db', http_get=get, now=lambda: clock[0], min_interval=0)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: client.get('sh.563360', '5m'), range(4)))
    assert len(calls) == 1
    assert results[0].rows[-1]['close'] == 11
    assert calls[0]['datalen'] == '1970'
    clock[0] += timedelta(seconds=31)
    latest = client.get('sh.563360', '5m')
    assert len(latest.rows) == 2
    assert latest.rows[-1]['close'] == 12
    assert calls[1]['datalen'] == '32'
    restarted = SinaLiveQuotes(tmp_path / 'quotes.db', http_get=get, now=lambda: clock[0], min_interval=0)
    assert restarted.get('sh.563360', '5m').rows[-1]['close'] == 12
    assert len(calls) == 2


def test_failure_returns_stale_data_and_backs_off_without_looping(tmp_path):
    clock = [datetime(2026, 9, 24, 10, 1, tzinfo=TZ)]
    calls = []
    def get(**kwargs):
        calls.append(kwargs)
        if len(calls) > 1:
            raise requests.Timeout('timeout')
        return Response([row('2026-09-24 10:00:00')])
    client = SinaLiveQuotes(tmp_path / 'quotes.db', http_get=get, now=lambda: clock[0], min_interval=0)
    client.get('sh.563360', '30m')
    clock[0] += timedelta(seconds=31)
    result = client.get('sh.563360', '30m')
    assert result.stale
    assert result.fetched_at < clock[0]
    clock[0] += timedelta(seconds=31)
    assert client.get('sh.563360', '30m').stale
    assert len(calls) == 2


def test_disconnected_tail_requests_full_window_and_does_not_hide_gap(tmp_path):
    clock = [datetime(2026, 9, 24, 10, 1, tzinfo=TZ)]
    calls = []
    def get(**kwargs):
        calls.append(kwargs['params']['datalen'])
        if len(calls) == 1:
            return Response([row('2026-09-24 09:35:00')])
        return Response([row('2026-09-24 10:00:00')])
    client = SinaLiveQuotes(tmp_path / 'quotes.db', http_get=get, now=lambda: clock[0], min_interval=0)
    client.get('sh.563360', '5m')
    clock[0] += timedelta(seconds=31)
    result = client.get('sh.563360', '5m')
    assert calls == ['1970', '32', '1970']
    assert [r['day'] for r in result.rows] == ['2026-09-24 10:00:00']
    assert result.warning


@pytest.mark.parametrize('hour,minute', [(11,30), (15,0)])
def test_session_end_refreshes_preclose_snapshot_before_off_hours_cooldown(tmp_path, hour, minute):
    close = datetime(2026,9,24,hour,minute,tzinfo=TZ)
    clock = [close - timedelta(seconds=10)]
    calls = []
    def get(**kwargs):
        calls.append(1)
        return Response([row(close.strftime('%Y-%m-%d %H:%M:%S'),10+len(calls))])
    client = SinaLiveQuotes(tmp_path / 'quotes.db', http_get=get, now=lambda: clock[0], min_interval=0)
    client.get('sh.563360','30m')
    clock[0] = close + timedelta(minutes=1)
    assert client.get('sh.563360','30m').rows[-1]['close'] == 12
    clock[0] += timedelta(minutes=1)
    client.get('sh.563360','30m')
    assert len(calls) == 2
