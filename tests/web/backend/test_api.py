from fastapi.testclient import TestClient

from web.backend.app import create_app
from web.backend.schemas import AnalysisRequest, CapabilityResponse, InstrumentOption


class FakeRegistry:
    def capabilities(self, market: str, instrument: str | None = None):
        assert market == "cn"
        return CapabilityResponse(market="cn", sources=["fixture"], periods=[])

    def search(self, market: str, query: str, limit: int = 20):
        assert (market, query, limit) == ("cn", "000001", 20)
        return [InstrumentOption(market="cn", instrument="sh.000001", name="上证指数",
                                 exchange="sh", kind="index")]


class FakeAnalysisService:
    def analyze(self, request: AnalysisRequest):
        return {"schema_version": 1, "request": request.model_dump(mode="json"),
                "meta": {"instrument": request.instrument, "period": request.period,
                         "source": "fixture", "first_bar": "2026-09-01T00:00:00+08:00",
                         "last_bar": "2026-09-01T00:00:00+08:00", "bar_count": 1},
                "candles": [{"time": "2026-09-01T00:00:00+08:00", "open": 10,
                             "high": 13, "low": 9, "close": 12, "volume": 100}],
                "indicators": {"macd": []},
                "overlays": {"bi": [], "segments": [], "zones": [], "buy_sell_points": []}}


def test_api_routes_use_injected_services():
    client = TestClient(create_app(FakeRegistry(), FakeAnalysisService()))
    assert client.get("/api/v1/capabilities", params={"market": "cn"}).json()["market"] == "cn"
    found = client.get("/api/v1/instruments", params={"market": "cn", "q": "000001"})
    assert found.json()[0]["instrument"] == "sh.000001"
    analyzed = client.post("/api/v1/analysis", json={
        "market": "cn", "instrument": "sh.000001", "period": "1d",
        "begin_time": "2026-09-01", "end_time": "2026-09-23", "adjustment": "none",
    })
    assert analyzed.status_code == 200
    assert analyzed.json()["meta"]["source"] == "fixture"


def test_catalog_routes_reject_invalid_market_and_query_size():
    client = TestClient(create_app(FakeRegistry(), FakeAnalysisService()))
    assert client.get("/api/v1/capabilities", params={"market": "us"}).status_code == 422
    assert client.get("/api/v1/instruments", params={"market": "us", "q": "x"}).status_code == 422
    assert client.get("/api/v1/instruments", params={"market": "cn", "q": "x" * 65}).status_code == 422
    assert client.get("/api/v1/instruments", params={"market": "cn", "q": "x", "limit": 21}).status_code == 422
