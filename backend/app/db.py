'''数据库连接工具，复用 analysis 模块的 Engine。'''
from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Any, Iterator

from sqlalchemy import text
from sqlalchemy.engine import Connection

from analysis.src.database import get_engine

from .cache import cache_store


_engine = None


def get_connection() -> Connection:
    '''获取 SQLAlchemy Connection。'''

    engine = get_engine()
    return engine.connect()


@contextmanager
def connection_scope() -> Iterator[Connection]:
    '''提供上下文便于 API 查询。'''

    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def fetch_draws(limit: int) -> list[dict]:
    '''查询最近开奖记录。'''

    with connection_scope() as conn:
        rows = conn.execute(
            text(
                '''
                SELECT period, draw_time, timestamp, numbers, sum, span, odd_even, big_small
                FROM lottery_draws
                ORDER BY draw_time DESC
                LIMIT :limit
                '''
            ),
            {'limit': limit},
        ).mappings().all()
        return [dict(row) for row in rows]


def fetch_draw_by_period(period: str) -> dict | None:
    '''按期号查询单条记录（含缓存）。'''

    cache_key = f'draw:{period}'
    cached = cache_store.get_json(cache_key)
    if cached:
        return cached

    with connection_scope() as conn:
        row = conn.execute(
            text(
                '''
                SELECT period, draw_time, timestamp, numbers, sum, span, odd_even, big_small
                FROM lottery_draws
                WHERE period=:period
                '''
            ),
            {'period': period},
        ).mappings().first()
        if not row:
            return None
        payload = dict(row)
        cache_store.set_json(cache_key, payload, ttl=60)
        return payload


def fetch_analysis_results(limit: int, offset: int = 0, analysis_type: str | None = None) -> list[dict]:
    '''查询最新分析结果并解析 JSON 字段，支持过滤与缓存。'''

    cache_key = f'analysis_results:{analysis_type or "all"}:{limit}:{offset}'
    cached = cache_store.get_json(cache_key)
    if cached:
        return cached

    clauses: list[str] = []
    params: dict[str, Any] = {'limit': limit, 'offset': offset}
    if analysis_type:
        clauses.append('analysis_type = :analysis_type')
        params['analysis_type'] = analysis_type
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ''

    sql = f'''
        SELECT id, analysis_type, schema_version, result_summary, result_data, metadata, created_at
        FROM analysis_results
        {where_sql}
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
    '''

    with connection_scope() as conn:
        rows = conn.execute(text(sql), params).mappings().all()

    results: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item['result_data'] = _parse_json(item['result_data'])
        item['metadata'] = _parse_json(item.get('metadata'))
        results.append(item)

    cache_store.set_json(cache_key, results, ttl=30)
    return results


def fetch_analysis_jobs(limit: int, offset: int = 0, status: str | None = None, job_type: str | None = None) -> list[dict]:
    '''查询 analysis_jobs 状态，便于展示任务进度。'''

    cache_key = f'analysis_jobs:{status or "all"}:{job_type or "all"}:{limit}:{offset}'
    cached = cache_store.get_json(cache_key)
    if cached:
        return cached

    clauses: list[str] = []
    params: dict[str, Any] = {'limit': limit, 'offset': offset}
    if status:
        clauses.append('status = :status')
        params['status'] = status
    if job_type:
        clauses.append('job_type = :job_type')
        params['job_type'] = job_type
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ''

    sql = f'''
        SELECT id, job_type, payload, status, started_at, finished_at, result_id, created_at, updated_at, priority
        FROM analysis_jobs
        {where_sql}
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
    '''

    with connection_scope() as conn:
        rows = conn.execute(text(sql), params).mappings().all()

    jobs: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item['payload'] = _parse_json(item['payload'])
        jobs.append(item)

    cache_store.set_json(cache_key, jobs, ttl=15)
    return jobs


def fetch_features_by_period(period: str) -> dict[str, Any] | None:
    '''按期号聚合特征列表，返回特征类型到值的映射。'''

    cache_key = f'features:{period}'
    cached = cache_store.get_json(cache_key)
    if cached:
        return cached

    with connection_scope() as conn:
        rows = conn.execute(
            text(
                '''
                SELECT feature_type, feature_value, schema_version, meta, updated_at
                FROM lottery_features
                WHERE period=:period
                ORDER BY updated_at DESC
                '''
            ),
            {'period': period},
        ).mappings().all()

    if not rows:
        return None

    features: dict[str, Any] = {}
    for row in rows:
        features[row['feature_type']] = {
            'schema_version': row['schema_version'],
            'meta': _parse_json(row.get('meta')),
            'value': _parse_json(row['feature_value']),
            'updated_at': row['updated_at'],
        }
    payload = {'period': period, 'features': features}
    cache_store.set_json(cache_key, payload, ttl=60)
    return payload


def _parse_json(value: Any) -> Any:
    '''尽量解析 JSON 字段，失败时保持原值。'''

    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value
