from web.backend.instruments import normalize_akshare_record, normalize_baostock_record
from web.backend.providers.baostock import BaoStockAdapter
from web.backend.providers.registry import ProviderRegistry
from web.backend.schemas import InstrumentOption


def test_catalog_rows_become_canonical_instruments():
    stock = normalize_baostock_record(("sh.600000", "浦发银行", "1999-11-10", "", "1", "1"))
    index = normalize_baostock_record(("sh.000001", "上证指数", "1991-07-15", "", "2", "1"))
    ak_stock = normalize_akshare_record({"code": "000001", "name": "平安银行"})
    assert (stock.instrument, stock.kind) == ("sh.600000", "stock")
    assert (index.instrument, index.kind) == ("sh.000001", "index")
    assert (ak_stock.instrument, ak_stock.exchange) == ("sz.000001", "sz")


def test_search_matches_code_and_name_and_limits_empty_query():
    catalog = [
        InstrumentOption(market="cn", instrument="sh.600000", name="浦发银行", exchange="sh", kind="stock"),
        InstrumentOption(market="cn", instrument="sh.000001", name="上证指数", exchange="sh", kind="index"),
        InstrumentOption(market="cn", instrument="sz.000001", name="平安银行", exchange="sz", kind="stock"),
    ]
    registry = ProviderRegistry([BaoStockAdapter(catalog_loader=lambda: catalog)])
    assert [x.instrument for x in registry.search("cn", "600000")] == ["sh.600000"]
    assert [x.instrument for x in registry.search("cn", "指数")] == ["sh.000001"]
    assert [x.instrument for x in registry.search("cn", "", limit=2)] == ["sh.600000", "sh.000001"]
    assert registry.search("cn", "unknown") == []
