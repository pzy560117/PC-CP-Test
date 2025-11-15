"""FastAPI 主入口。"""
from __future__ import annotations

from fastapi import FastAPI

from .api.draws import router as draws_router

app = FastAPI(title="Lottery Analysis Backend")
app.include_router(draws_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    """简单健康检查。"""

    return {"status": "ok"}
