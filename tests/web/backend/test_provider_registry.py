import pytest

from web.backend.providers.errors import UnsupportedPeriodError
from web.backend.providers.registry import ProviderRegistry


class FakeProvider:
    def __init__(self, source_id: str, periods: set[str]):
        self.source_id = source_id
        self.periods = periods

    def supports(self, instrument: str, period: str, adjustment: str) -> bool:
        return instrument.startswith("sh.") and period in self.periods and adjustment == "qfq"

    def capabilities(self, market: str, instrument: str | None = None):
        return []

    def search_instruments(self, market: str, query: str, limit: int):
        return []


def test_registry_resolves_first_matching_provider():
    first = FakeProvider("first", {"1d"})
    second = FakeProvider("second", {"1d", "1w"})
    registry = ProviderRegistry([first, second])
    assert registry.resolve("cn", "sh.600000", "1d", "qfq") is first
    assert registry.resolve("cn", "sh.600000", "1w", "qfq") is second


def test_registry_rejects_unsupported_before_fetch():
    registry = ProviderRegistry([FakeProvider("daily", {"1d"})])
    with pytest.raises(UnsupportedPeriodError) as err:
        registry.resolve("cn", "sh.600000", "30m", "qfq")
    assert err.value.code == "UNSUPPORTED_PERIOD"
    with pytest.raises(UnsupportedPeriodError):
        registry.resolve("us", "sh.600000", "1d", "qfq")


def test_guard_serializes_same_source_but_not_other_sources():
    from threading import Event, Thread

    first = FakeProvider("baostock", {"1d"})
    second = FakeProvider("akshare", {"1d"})
    registry = ProviderRegistry([first, second])
    entered_first, release_first, entered_same, entered_other = Event(), Event(), Event(), Event()

    def hold_first():
        with registry.guard(first):
            entered_first.set()
            release_first.wait(3)

    def enter_same():
        with registry.guard(first):
            entered_same.set()

    def enter_other():
        with registry.guard(second):
            entered_other.set()

    workers = [Thread(target=hold_first), Thread(target=enter_same), Thread(target=enter_other)]
    workers[0].start()
    assert entered_first.wait(2)
    workers[1].start()
    workers[2].start()
    try:
        assert entered_other.wait(2)
        assert not entered_same.wait(0.05)
    finally:
        release_first.set()
        for worker in workers:
            worker.join(2)
    assert entered_same.is_set()
    assert not any(worker.is_alive() for worker in workers)


def test_baostock_fetch_closes_connection_after_iterator_failure():
    from web.backend.providers.baostock import BaoStockAdapter
    from web.backend.providers.errors import SourceDataError
    from web.backend.schemas import AnalysisRequest

    events = []

    class FailingAPI:
        @classmethod
        def do_init(cls):
            events.append("init")

        @classmethod
        def do_close(cls):
            events.append("close")

        def __init__(self, **kwargs):
            events.append(("construct", kwargs["code"]))

        def get_kl_data(self):
            events.append("read")
            raise RuntimeError("source failed")
            yield

    request = AnalysisRequest(market="cn", instrument="sh.600000", period="1d",
                              begin_time="2026-09-01", end_time="2026-09-23", adjustment="qfq")
    adapter = BaoStockAdapter(catalog_loader=lambda: [], api_cls=FailingAPI)
    with pytest.raises(SourceDataError, match="source failed"):
        adapter.fetch_klines(request, max_bars=5000)
    assert events == ["init", ("construct", "sh.600000"), "read", "close"]


def test_akshare_fetch_converts_canonical_stock_code():
    from web.backend.providers.akshare import AkShareAdapter
    from web.backend.schemas import AnalysisRequest

    received = []

    class FakeAPI:
        @classmethod
        def do_init(cls):
            received.append("init")

        @classmethod
        def do_close(cls):
            received.append("close")

        def __init__(self, **kwargs):
            received.append(kwargs["code"])

        def get_kl_data(self):
            yield "bar"

    request = AnalysisRequest(market="cn", instrument="sz.000001", period="1w",
                              begin_time="2026-09-01", end_time="2026-09-23", adjustment="none")
    adapter = AkShareAdapter(catalog_loader=lambda: [], api_cls=FakeAPI)
    assert adapter.fetch_klines(request, max_bars=5000) == ["bar"]
    assert received == ["init", "000001", "close"]
