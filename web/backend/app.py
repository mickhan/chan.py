from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .routes import router
from .analysis_service import map_analysis_error
from .providers.errors import ProviderError
from .static_app import mount_static_app


def create_app(registry, analysis_service) -> FastAPI:
    app = FastAPI()
    @app.exception_handler(RequestValidationError)
    async def invalid_request(_request: Request, _error: RequestValidationError):
        return JSONResponse(status_code=422, content={
            'code': 'INVALID_REQUEST', 'message': '请求参数无效，请检查标的、日期和周期',
        })
    @app.exception_handler(ProviderError)
    async def provider_failure(_request: Request, error: ProviderError):
        mapped = map_analysis_error(error)
        status = {'UNSUPPORTED_PERIOD': 400, 'DATE_RANGE_UNAVAILABLE': 400,
                  'SOURCE_TIMEOUT': 504, 'SOURCE_ERROR': 502}[mapped.code]
        return JSONResponse(status_code=status, content=mapped.model_dump(mode='json', exclude_none=True))
    app.state.registry = registry
    app.state.analysis_service = analysis_service
    app.include_router(router, prefix="/api/v1")
    mount_static_app(app)
    return app


def _default_app() -> FastAPI:
    from .analysis_service import AnalysisService
    from .kline_cache import KlineCache
    from .providers.registry import default_registry
    registry = default_registry()
    return create_app(registry, AnalysisService(registry, cache=KlineCache()))


app = _default_app()
