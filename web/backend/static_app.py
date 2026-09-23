"""Serve the built Vue app from the API origin when assets are present."""
from pathlib import Path

from fastapi.staticfiles import StaticFiles

_DIST = Path(__file__).resolve().parents[1] / 'frontend' / 'dist'


def mount_static_app(app) -> None:
    if (_DIST / 'index.html').is_file():
        app.mount('/', StaticFiles(directory=_DIST, html=True), name='frontend')
