import time
from threading import Event

from web.backend.catalog_cache import CatalogCache
from web.backend.providers.baostock import BaoStockAdapter
from web.backend.providers.registry import ProviderRegistry
from web.backend.schemas import InstrumentOption


INDEX = InstrumentOption(market='cn', instrument='sh.000001', name='上证指数', exchange='sh', kind='index')
STOCK = InstrumentOption(market='cn', instrument='sh.600000', name='浦发银行', exchange='sh', kind='stock')


def test_search_uses_catalog_saved_by_previous_process(tmp_path):
    path = tmp_path / 'market.sqlite3'
    fetched = []

    def load_catalog():
        fetched.append(1)
        return [INDEX, STOCK]

    first = ProviderRegistry([BaoStockAdapter(catalog_loader=load_catalog,
                                               catalog_cache=CatalogCache(path, now=lambda: 1000))])
    assert [item.instrument for item in first.search('cn', '0')] == ['sh.000001', 'sh.600000']

    def unavailable():
        raise AssertionError('remote catalog should not be requested again')

    restarted = ProviderRegistry([BaoStockAdapter(catalog_loader=unavailable,
                                                   catalog_cache=CatalogCache(path, now=lambda: 1000))])
    assert [item.instrument for item in restarted.search('cn', '600000')] == ['sh.600000']
    assert fetched == [1]


def test_stale_catalog_returns_immediately_then_refreshes_in_background(tmp_path):
    path = tmp_path / 'market.sqlite3'
    CatalogCache(path, now=lambda: 0).get('baostock', lambda: [INDEX])
    started, release = Event(), Event()

    def refresh():
        started.set()
        assert release.wait(3)
        return [STOCK]

    cache = CatalogCache(path, now=lambda: 86401)
    assert cache.get('baostock', refresh) == [INDEX]
    assert started.wait(2)
    release.set()
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline and cache.get('baostock', refresh) != [STOCK]:
        time.sleep(0.01)
    assert cache.get('baostock', refresh) == [STOCK]
