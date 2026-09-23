from fastapi import APIRouter, Request

from .schemas import AnalysisRequest, CapabilityResponse, ChartResponse, InstrumentOption

router = APIRouter()


@router.get("/capabilities", response_model=CapabilityResponse)
def get_capabilities(request: Request, market: str = "cn", instrument: str | None = None):
    return request.app.state.registry.capabilities(market, instrument)


@router.get("/instruments", response_model=list[InstrumentOption])
def get_instruments(request: Request, market: str, q: str, limit: int = 20):
    return request.app.state.registry.search(market, q, limit)


@router.post("/analysis", response_model=ChartResponse)
def analyze(request_body: AnalysisRequest, request: Request):
    return request.app.state.analysis_service.analyze(request_body)
