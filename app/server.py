"""Entrypoint para Vercel (tool.vercel.entrypoint en pyproject.toml).

Vercel busca una instancia FastAPI llamada `app`. En local se sigue usando
`uvicorn app.main:build_app --factory`.
"""
from app.main import build_app

app = build_app()
