from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .routes import router
from .static_app import mount_static_app


def create_app(registry, analysis_service) -> FastAPI:
    app = FastAPI()
    @app.exception_handler(RequestValidationError)
    async def invalid_request(_request: Request, _error: RequestValidationError):
        return JSONResponse(status_code=422, content={
            'code': 'INVALID_REQUEST', 'message': '请求参数无效，请检查标的、日期和周期',
        })
    app.state.registry = registry
    app.state.analysis_service = analysis_service
    app.include_router(router, prefix="/api/v1")
    mount_static_app(app)
    return app


def _default_app() -> FastAPI:
    from .analysis_service import AnalysisService
    from .providers.registry import default_registry
    registry = default_registry()
    return create_app(registry, AnalysisService(registry))


app = _default_app()
