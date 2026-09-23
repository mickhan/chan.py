import pytest
from pydantic import ValidationError

from web.backend.schemas import AnalysisRequest


def test_analysis_request_rejects_reversed_dates():
    with pytest.raises(ValidationError):
        AnalysisRequest(
            market="cn", instrument="sh.000001", period="1d",
            begin_time="2026-09-23", end_time="2026-09-01", adjustment="none",
        )


def test_analysis_request_rejects_internal_engine_options():
    with pytest.raises(ValidationError):
        AnalysisRequest(
            market="cn", instrument="sh.000001", period="1d",
            begin_time="2026-09-01", end_time="2026-09-23", adjustment="none",
            chan_config={"bi_algo": "fx"},
        )


def test_chart_response_requires_version_range_and_series():
    from web.backend.schemas import ChartResponse
    request = {
        "market": "cn", "instrument": "sh.000001", "period": "1d",
        "begin_time": "2026-09-01", "end_time": "2026-09-23", "adjustment": "none",
    }
    response = ChartResponse.model_validate({
        "schema_version": 1,
        "request": request,
        "meta": {"instrument": "sh.000001", "period": "1d", "source": "fixture",
                 "first_bar": "2026-09-01T00:00:00+08:00",
                 "last_bar": "2026-09-01T00:00:00+08:00", "bar_count": 1},
        "candles": [{"time": "2026-09-01T00:00:00+08:00", "open": 10,
                     "high": 13, "low": 9, "close": 12, "volume": 100}],
        "indicators": {"macd": []},
        "overlays": {"bi": [], "segments": [], "zones": [], "buy_sell_points": []},
    })
    assert response.schema_version == 1
    assert response.meta.first_bar == response.candles[0].time
    with pytest.raises(ValidationError):
        ChartResponse.model_validate({"schema_version": 2, "request": request})
