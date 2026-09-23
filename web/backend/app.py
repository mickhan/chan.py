from fastapi import FastAPI

from .routes import router


def create_app(registry, analysis_service) -> FastAPI:
    app = FastAPI()
    app.state.registry = registry
    app.state.analysis_service = analysis_service
    app.include_router(router, prefix="/api/v1")
    return app
