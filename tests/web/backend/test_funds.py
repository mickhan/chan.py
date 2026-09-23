from datetime import date

from Common.CEnum import AUTYPE, KL_TYPE
from web.backend.instruments import instrument_kind, normalize_baostock_record, normalize_sina_lof_record
from web.backend.providers.baostock import BaoStockAdapter
from web.backend.providers.sina_lof import SinaLofAdapter
from web.backend.providers.registry import ProviderRegistry
from web.backend.schemas import AnalysisRequest


def test_etf_and_lof_catalog_and_kind():
    etf = normalize_baostock_record(('sh.510300', '沪深300ETF', '2012-05-28', '', '5', '1'))
    lof = normalize_sina_lof_record({'代码': 'sz160706', '名称': '沪深300LOF'})
    assert (etf.instrument, etf.kind) == ('sh.510300', 'etf')
    assert (lof.instrument, lof.kind) == ('sz.160706', 'lof')
    assert instrument_kind('sz.159919') == 'etf'
    assert instrument_kind('sh.501018') == 'lof'


def test_etf_and_lof_provider_routing_and_capabilities():
    bao = BaoStockAdapter(catalog_loader=lambda: [], metadata_loader=lambda _code: date(2012, 5, 28))
    lof = SinaLofAdapter(catalog_loader=lambda: [])
    registry = ProviderRegistry([bao, lof])
    assert registry.resolve('cn', 'sh.510300', '30m', 'none') is bao
    assert registry.resolve('cn', 'sz.160706', '1d', 'none') is lof
    assert all(x.kind == 'etf' for x in registry.capabilities('cn', 'sh.510300').periods)
    assert [(x.period, x.adjustments) for x in registry.capabilities('cn', 'sz.160706').periods] == [('1d', ['none'])]
    assert not bao.supports('sz.160706', '1d', 'none')
    assert not lof.supports('sz.160706', '1d', 'qfq')


def test_lof_catalog_search_and_daily_fetch():
    class FakeAPI:
        received = []
        @classmethod
        def do_init(cls): pass
        @classmethod
        def do_close(cls): pass
        def __init__(self, **kwargs): self.received.append(kwargs)
        def get_kl_data(self): yield 'bar'
    option = normalize_sina_lof_record({'代码': 'sz160706', '名称': '沪深300LOF'})
    adapter = SinaLofAdapter(catalog_loader=lambda: [option], api_cls=FakeAPI)
    assert adapter.search_instruments('cn', '160706', 20) == [option]
    request = AnalysisRequest(market='cn', instrument='sz.160706', period='1d',
                              begin_time='2026-09-01', end_time='2026-09-23', adjustment='none')
    assert adapter.fetch_klines(request, 5000) == ['bar']
    assert FakeAPI.received[0]['code'] == 'sz160706'
    assert adapter.period_to_kl_type('1d') == KL_TYPE.K_DAY
    assert adapter.adjustment_to_autype('none') == AUTYPE.NONE

def test_every_cached_etf_code_family_routes_as_etf():
    for instrument in ('sh.510300', 'sh.520500', 'sh.530000', 'sh.550000',
                       'sh.560000', 'sh.580000', 'sz.150000', 'sz.159919'):
        assert instrument_kind(instrument) == 'etf'
