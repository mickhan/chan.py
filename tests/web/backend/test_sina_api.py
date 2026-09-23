import json
from pathlib import Path

import pytest

from web.backend.providers.errors import SourceDataError
from DataAPI.SinaAPI import parse_sina_jsonp

FIXTURE = Path(__file__).parent / "fixtures" / "sina_30m.jsonp"


def test_parser_accepts_ordered_jsonp_ohlcv():
    rows = parse_sina_jsonp(FIXTURE.read_text())
    assert [row["day"] for row in rows] == [
        "2026-09-01 10:00:00", "2026-09-01 10:30:00", "2026-09-01 11:00:00",
    ]
    assert rows[0]["close"] == 12.0
    assert rows[0]["volume"] == 100.0


@pytest.mark.parametrize("change", [
    lambda rows: rows[0].pop("day"),
    lambda rows: rows[0].pop("close"),
    lambda rows: rows.__setitem__(1, dict(rows[0])),
    lambda rows: rows.reverse(),
    lambda rows: rows[0].update(low="14"),
])
def test_parser_rejects_missing_duplicate_unordered_or_invalid_bars(change):
    rows = json.loads(FIXTURE.read_text().split("=(", 1)[1].rsplit(");", 1)[0])
    change(rows)
    with pytest.raises(SourceDataError):
        parse_sina_jsonp(f"=({json.dumps(rows)});")


class FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


def test_sina_request_filters_unfinished_bar_and_maps_symbol():
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from Common.CEnum import AUTYPE, KL_TYPE
    from DataAPI.SinaAPI import CSina

    called = {}

    def get(url, params, timeout):
        called.update(url=url, params=params, timeout=timeout)
        return FakeResponse(FIXTURE.read_text())

    api = CSina("sh.000001", KL_TYPE.K_30M, "2026-09-01", "2026-09-01", AUTYPE.NONE,
                http_get=get, now=lambda: datetime(2026, 9, 1, 10, 35, tzinfo=ZoneInfo("Asia/Shanghai")))
    bars = list(api.get_kl_data())
    assert [bar.time.hour for bar in bars] == [10, 10]
    assert [bar.time.minute for bar in bars] == [0, 30]
    assert all(bar.time.auto is False for bar in bars)
    assert called["params"] == {"symbol": "sh000001", "scale": "30", "ma": "no", "datalen": "1970"}
    assert called["timeout"] == 15
    assert "CN_MarketDataService.getKLineData" in called["url"]


def test_sina_rejects_dates_older_than_returned_window():
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from Common.CEnum import AUTYPE, KL_TYPE
    from DataAPI.SinaAPI import CSina
    from web.backend.providers.errors import DateRangeUnavailableError

    api = CSina("sh.000001", KL_TYPE.K_30M, "2026-08-31", "2026-09-01", AUTYPE.NONE,
                http_get=lambda **kwargs: FakeResponse(FIXTURE.read_text()),
                now=lambda: datetime(2026, 9, 2, tzinfo=ZoneInfo("Asia/Shanghai")))
    with pytest.raises(DateRangeUnavailableError):
        list(api.get_kl_data())


def test_sina_empty_and_timeout_have_distinct_outcomes():
    from datetime import datetime
    from zoneinfo import ZoneInfo

    import requests

    from Common.CEnum import AUTYPE, KL_TYPE
    from DataAPI.SinaAPI import CSina
    from web.backend.providers.errors import SourceTimeoutError
    from web.backend.providers.sina import SinaAdapter
    from web.backend.schemas import AnalysisRequest

    now = lambda: datetime(2026, 9, 2, tzinfo=ZoneInfo("Asia/Shanghai"))
    empty = CSina("sh.000001", KL_TYPE.K_30M, "2026-09-01", "2026-09-01", AUTYPE.NONE,
                  http_get=lambda **kwargs: FakeResponse("=([]);"), now=now)
    assert list(empty.get_kl_data()) == []

    def timeout(**kwargs):
        raise requests.Timeout("delayed")

    request = AnalysisRequest(market="cn", instrument="sh.000001", period="30m",
                              begin_time="2026-09-01", end_time="2026-09-01", adjustment="none")
    with pytest.raises(SourceTimeoutError):
        SinaAdapter(http_get=timeout, now=now).fetch_klines(request, max_bars=5000)


def test_sina_capability_does_not_treat_remote_window_as_local_history_limit():
    from web.backend.providers.sina import SinaAdapter

    def unexpected_fetch(**_kwargs):
        raise AssertionError('capabilities should not fetch live bars')

    adapter = SinaAdapter(http_get=unexpected_fetch)
    capability = adapter.capabilities('cn', 'sh.000001')[0]
    assert capability.source == 'sina'
    assert capability.period == '30m'
    assert capability.first_available is None
    assert capability.last_available is None
    assert capability.max_bars == 5000


def test_sina_custom_source_loads():
    from Chan import CChan
    from ChanConfig import CChanConfig
    from Common.CEnum import KL_TYPE
    from DataAPI.SinaAPI import CSina

    chan = CChan(code='sh.000001', data_src='custom:SinaAPI.CSina',
                 lv_list=[KL_TYPE.K_30M], config=CChanConfig({'trigger_step': True}))
    assert chan.GetStockAPI() is CSina


def test_default_registry_routes_index_intraday_to_sina():
    from web.backend.providers.registry import default_registry
    from web.backend.providers.sina import SinaAdapter

    provider = default_registry().resolve("cn", "sh.000001", "30m", "none")
    assert isinstance(provider, SinaAdapter)
