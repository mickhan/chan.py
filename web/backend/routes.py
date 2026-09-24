import logging
from typing import Literal

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from .analysis_service import map_analysis_error
from .providers.errors import ProviderError

from .schemas import AnalysisRequest, CapabilityResponse, ChartResponse, InstrumentOption

router = APIRouter()
_log = logging.getLogger(__name__)


@router.get("/capabilities", response_model=CapabilityResponse)
def get_capabilities(request: Request, market: Literal["cn"] = "cn", instrument: str | None = None):
    return request.app.state.registry.capabilities(market, instrument)


@router.get("/instruments", response_model=list[InstrumentOption])
def get_instruments(
    request: Request, market: Literal["cn"],
    q: str = Query("", max_length=64), limit: int = Query(20, ge=1, le=20),
):
    return request.app.state.registry.search(market, q, limit)


@router.post("/analysis", response_model=ChartResponse)
def analyze(request_body: AnalysisRequest, request: Request):
    try:
        return request.app.state.analysis_service.analyze(request_body)
    except Exception as exc:
        error = map_analysis_error(exc)
        if error.code == "ANALYSIS_ERROR":
            _log.exception("Analysis request failed")
        status = {"INVALID_REQUEST": 400, "UNSUPPORTED_PERIOD": 400,
                  "DATE_RANGE_UNAVAILABLE": 400, "NO_DATA": 404,
                  "SOURCE_TIMEOUT": 504, "SOURCE_ERROR": 502,
                  "ANALYSIS_ERROR": 500}[error.code]
        return JSONResponse(status_code=status, content=error.model_dump(mode='json', exclude_none=True))
