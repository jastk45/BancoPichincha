"""Adaptador web: sirve la página de demo. La clave la ingresa el usuario en el navegador."""
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

_INDEX = Path(__file__).parent / "static" / "index.html"


def create_web_router() -> APIRouter:
    router = APIRouter()

    @router.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(_INDEX, media_type="text/html")

    return router
