from web.backend.providers.akshare import AkShareAdapter
from web.backend.providers.baostock import BaoStockAdapter
from web.backend.providers.registry import ProviderRegistry


def test_baostock_index_has_no_intraday_capability():
    adapter = BaoStockAdapter(catalog_loader=lambda: [])
    periods = adapter.capabilities("cn", "sh.000001")
    assert {item.period for item in periods} == {"1d", "1w", "1mo"}
    assert all(item.adjustments == ["none"] for item in periods)
    assert adapter.supports("sh.000001", "30m", "none") is False


def test_stock_capabilities_follow_each_provider():
    bao = BaoStockAdapter(catalog_loader=lambda: [])
    ak = AkShareAdapter(catalog_loader=lambda: [])
    assert bao.supports("sh.600000", "30m", "qfq") is True
    assert ak.supports("sh.600000", "30m", "qfq") is False
    assert ak.supports("sh.600000", "1w", "qfq") is True
    assert ak.capabilities("cn", "sh.000001") == []
    combined = ProviderRegistry([bao, ak]).capabilities("cn", "sh.600000")
    assert combined.sources == ["baostock", "akshare"]
    assert any(x.source == "akshare" and x.period == "1w" for x in combined.periods)


def test_unknown_instrument_capability_returns_no_options():
    registry = ProviderRegistry([BaoStockAdapter(catalog_loader=lambda: []),
                                 AkShareAdapter(catalog_loader=lambda: [])])
    result = registry.capabilities("cn", "not-a-code")
    assert result.periods == []
    assert result.sources == []
