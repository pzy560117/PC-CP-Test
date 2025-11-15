'''分析结果与特征查询 API。'''
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..config import get_settings
from ..db import fetch_analysis_jobs, fetch_analysis_results, fetch_features_by_period

analysis_router = APIRouter(prefix='/api/v1/analysis', tags=['analysis'])
features_router = APIRouter(prefix='/api/v1/features', tags=['features'])


@analysis_router.get('/results')
def list_analysis_results(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    analysis_type: str | None = Query(None),
) -> dict:
    '''返回分析结果列表，支持分页与类型过滤。'''

    settings = get_settings()
    limit = min(limit, settings.max_results)
    items = fetch_analysis_results(limit=limit, offset=offset, analysis_type=analysis_type)
    return {'items': items, 'count': len(items), 'offset': offset}


@analysis_router.get('/jobs')
def list_analysis_jobs(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None),
    job_type: str | None = Query(None),
) -> dict:
    '''返回分析任务状态，可按状态/类型过滤。'''

    settings = get_settings()
    limit = min(limit, settings.max_jobs)
    items = fetch_analysis_jobs(limit=limit, offset=offset, status=status, job_type=job_type)
    return {'items': items, 'count': len(items), 'offset': offset}


@features_router.get('/{period}')
def get_features(period: str) -> dict:
    '''按期号查询特征详情。'''

    record = fetch_features_by_period(period)
    if not record:
        raise HTTPException(status_code=404, detail='features not found')
    return record
