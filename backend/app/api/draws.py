"""开奖数据路由。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..config import get_settings
from ..db import fetch_draw_by_period, fetch_draws

router = APIRouter(prefix="/api/v1/draws", tags=["draws"])


@router.get("/")
def list_draws(limit: int = Query(50, ge=1, le=500)) -> dict:
    """返回最近开奖数据列表。"""

    settings = get_settings()
    limit = min(limit, settings.max_draws)
    items = fetch_draws(limit)
    return {"items": items, "count": len(items)}


@router.get("/{period}")
def get_draw(period: str) -> dict:
    """按期号查询单条开奖数据。"""

    draw = fetch_draw_by_period(period)
    if not draw:
        raise HTTPException(status_code=404, detail="period not found")
    return draw
