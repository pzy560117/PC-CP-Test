'''分析结果与特征查询 API。'''
from __future__ import annotations

import csv
import io
import json
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..config import get_settings
from ..db import (
    fetch_analysis_jobs,
    fetch_analysis_results,
    fetch_features_batch,
    fetch_features_by_period,
)

analysis_router = APIRouter(prefix='/api/v1/analysis', tags=['analysis'])
features_router = APIRouter(prefix='/api/v1/features', tags=['features'])


class FeatureBatchRequest(BaseModel):
    '''批量特征查询请求体。'''

    periods: list[str]


class FeatureExportRequest(BaseModel):
    '''特征导出请求体。'''

    periods: list[str]
    export_format: str = 'json'


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


@analysis_router.get('/results/export')
def export_analysis_results_endpoint(
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    analysis_type: str | None = Query(None),
    export_format: str = Query('json', pattern='^(json|csv)$'),
):
    '''导出分析结果，支持 JSON/CSV。'''

    settings = get_settings()
    limit = min(limit, settings.max_results)
    items = fetch_analysis_results(limit=limit, offset=offset, analysis_type=analysis_type)

    if export_format == 'json':
        return {'items': items, 'count': len(items), 'format': 'json'}

    csv_rows = _serialize_analysis_rows(items)
    filename = f'analysis-results-{datetime.utcnow().strftime("%Y%m%d%H%M%S")}.csv'
    headers = {'Content-Disposition': f'attachment; filename="{filename}"'}
    fieldnames = list(csv_rows[0].keys()) if csv_rows else ['id', 'analysis_type', 'result_summary', 'result_data', 'metadata', 'created_at']
    return StreamingResponse(
        _iter_csv(csv_rows, fieldnames=fieldnames),
        media_type='text/csv',
        headers=headers,
    )


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


@features_router.post('/batch')
def batch_features(request: FeatureBatchRequest) -> dict:
    '''批量查询多期特征，便于前端导出或比对。'''

    if not request.periods:
        raise HTTPException(status_code=400, detail='periods required')
    items_map = fetch_features_batch(request.periods)
    ordered_items = [items_map[period] for period in request.periods if period in items_map]
    return {'items': ordered_items, 'count': len(ordered_items)}


@features_router.post('/export')
def export_features(request: FeatureExportRequest):
    '''导出特征结果，支持 JSON/CSV。'''

    if not request.periods:
        raise HTTPException(status_code=400, detail='periods required')
    items_map = fetch_features_batch(request.periods)
    ordered_items = [items_map[period] for period in request.periods if period in items_map]
    if request.export_format == 'json':
        return {'items': ordered_items, 'count': len(ordered_items), 'format': 'json'}
    if request.export_format != 'csv':
        raise HTTPException(status_code=400, detail='unsupported format')
    rows = _serialize_feature_rows(ordered_items)
    filename = f'features-{datetime.utcnow().strftime("%Y%m%d%H%M%S")}.csv'
    fieldnames = list(rows[0].keys()) if rows else ['period', 'feature_type', 'schema_version', 'value', 'updated_at']
    headers = {'Content-Disposition': f'attachment; filename="{filename}"'}
    return StreamingResponse(_iter_csv(rows, fieldnames=fieldnames), media_type='text/csv', headers=headers)


def _serialize_analysis_rows(items: list[dict]) -> list[dict[str, str]]:
    '''将分析结果转为 CSV 结构。'''

    rows: list[dict[str, str]] = []
    for item in items:
        rows.append(
            {
                'id': str(item['id']),
                'analysis_type': item['analysis_type'],
                'schema_version': str(item['schema_version']),
                'result_summary': item.get('result_summary') or '',
                'result_data': json.dumps(item.get('result_data'), ensure_ascii=False),
                'metadata': json.dumps(item.get('metadata'), ensure_ascii=False),
                'created_at': str(item.get('created_at')),
            }
        )
    return rows


def _serialize_feature_rows(items: list[dict]) -> list[dict[str, str]]:
    '''将特征结构展平成 CSV 行。'''

    rows: list[dict[str, str]] = []
    for item in items:
        period = item['period']
        features = item.get('features', {})
        for feature_type, payload in features.items():
            rows.append(
                {
                    'period': period,
                    'feature_type': feature_type,
                    'schema_version': str(payload.get('schema_version')),
                    'value': json.dumps(payload.get('value'), ensure_ascii=False),
                    'updated_at': str(payload.get('updated_at')),
                }
            )
    return rows


def _iter_csv(rows: list[dict[str, str]], fieldnames: list[str]):
    '''生成 CSV 流。'''

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
        buffer.seek(0)
        data = buffer.read()
        yield data
        buffer.truncate(0)
        buffer.seek(0)
    if not rows:
        buffer.seek(0)
        data = buffer.read()
        if data:
            yield data
