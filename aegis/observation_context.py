"""Frozen, bounded provenance-checked Worker observations for planning relevance."""
import hashlib
import json
import re
from urllib.parse import urlsplit, unquote
from contextlib import nullcontext

from .checks import CATALOG
from .network import in_scope, normalize_url
from .planning_history import history, PlanningConflict
from .worker_observations import provenance, observation_id

FORMAT = 'aegis-observation-context-v1'
MAX_ITEMS = 100
MAX_BYTES = 64 * 1024
PRIORITIES = {
    'api_path': ['api_authorization', 'cors_policy'],
    'session_path': ['cookie_policy', 'transport_security'],
    'management_path': ['api_authorization'],
    'other': [],
}


def category(url):
    parts = {part.casefold() for part in unquote(urlsplit(url).path).split('/') if part}
    if parts & {'login', 'logout', 'signin', 'signout', 'session', 'auth', 'oauth'}:return 'session_path'
    if parts & {'admin', 'manage', 'management', 'settings'}:return 'management_path'
    if parts & {'api', 'graphql', 'rest'}:return 'api_path'
    return 'other'


def encode(context):
    return json.dumps(context, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def snapshot(store, task_id, *, connection=None):
    with (nullcontext(connection) if connection is not None else store.read_transaction()) as db:
        family = history(store, task_id, connection=db)
        assets = {id: store.get('assets', id, connection=db) for id in family[0]['asset_ids']}
        items, seen = [], set()
        total = inspected = excluded = 0
        for source in family:
            if not source.get('approved_at'):continue
            remaining = MAX_ITEMS - inspected
            try:
                page = store.page('observations', filters={'task_id': source['id']},
                                  limit=max(1, remaining), connection=db)
            except (TypeError, ValueError, KeyError):
                raise PlanningConflict('Worker 관찰 목록의 저장 형식을 확인하세요.') from None
            total += page['total']
            for row in page['items'][:remaining]:
                inspected += 1
                current = assets.get(row.get('asset_id')) if type(row.get('asset_id')) is str else None
                coverage = store.get('coverage', f"{source['id']}:{row.get('asset_id')}:endpoint_inventory", connection=db)
                try:
                    url = row['url']; parsed = urlsplit(url)
                    if type(row.get('id')) is not str:raise ValueError('invalid observation identity')
                    stored=store.get('observations',row['id'],connection=db)
                    identity_matches=(stored is not None and
                        {k:v for k,v in stored.items() if k not in ('asset_name','task_name')} ==
                        {k:v for k,v in row.items() if k not in ('asset_name','task_name')})
                    valid = (provenance(row, source)['status'] == 'matched'
                             and identity_matches
                             and current and current.get('authorized') is True and not current.get('archived_at')
                             and type(current.get('revision',1)) is int
                             and current.get('revision', 1) == row['scope_revision'] and current.get('url') == row['scope_url']
                             and coverage and coverage.get('status') == 'completed'
                             and coverage.get('id') == f"{source['id']}:{row['asset_id']}:endpoint_inventory"
                             and coverage.get('task_id') == source['id'] and coverage.get('asset_id') == row['asset_id']
                             and coverage.get('check') == 'endpoint_inventory' and type(coverage.get('asset_revision')) is int
                             and coverage.get('asset_revision') == row['scope_revision']
                             and not parsed.query and not parsed.fragment and not parsed.username and not parsed.password
                             and normalize_url(url) == url and row['id'] not in seen)
                except (KeyError, TypeError, ValueError):valid = False
                if not valid:
                    excluded += 1
                    continue
                seen.add(row['id'])
                items.append({key: row[key] for key in ('id', 'task_id', 'asset_id', 'url', 'scope_url', 'scope_revision', 'package_sha256')}
                             | {'category': category(url)})
        context = {'format': FORMAT, 'source_task_id': task_id,
                   'counts': {'total': total, 'inspected': inspected, 'included': len(items),
                              'excluded': excluded, 'omitted': total - inspected}, 'items': items}
        body = encode(context)
        if len(body) > MAX_BYTES:raise PlanningConflict('Worker 관찰 계획 맥락의64KiB 한도를 초과했습니다.')
        context['fingerprint'] = hashlib.sha256(body).hexdigest()
        return context


def require(context):
    try:
        if (type(context) is not dict or set(context) != {'format', 'source_task_id', 'counts', 'items', 'fingerprint'}
                or context['format'] != FORMAT or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', context['source_task_id'])
                or type(context['items']) is not list or len(context['items']) > MAX_ITEMS):raise ValueError()
        counts = context['counts']
        if (type(counts) is not dict or set(counts) != {'total', 'inspected', 'included', 'excluded', 'omitted'}
                or any(type(n) is not int or n < 0 for n in counts.values())
                or counts['included'] != len(context['items']) or counts['inspected'] > MAX_ITEMS
                or counts['included'] + counts['excluded'] != counts['inspected']
                or counts['inspected'] + counts['omitted'] != counts['total']):raise ValueError()
        seen = set()
        for row in context['items']:
            if (type(row) is not dict or set(row) != {'id', 'task_id', 'asset_id', 'url', 'scope_url', 'scope_revision', 'package_sha256', 'category'}
                    or any(type(row[k]) is not str for k in row if k != 'scope_revision')
                    or type(row['scope_revision']) is not int or row['scope_revision'] < 1
                    or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', row['task_id'])
                    or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', row['asset_id'])
                    or not re.fullmatch(r'[a-f0-9]{64}', row['package_sha256'])
                    or len(row['url']) > 2000 or len(row['scope_url']) > 2000
                    or normalize_url(row['url']) != row['url'] or not in_scope(row['url'], row['scope_url'])
                    or urlsplit(row['url']).query or urlsplit(row['url']).fragment
                    or row['id'] in seen or row['id'] != observation_id(row['task_id'], row['asset_id'], 'endpoint_inventory', row['url'])
                    or row['category'] != category(row['url'])):raise ValueError()
            seen.add(row['id'])
        body = encode({key: value for key, value in context.items() if key != 'fingerprint'})
        if len(body) > MAX_BYTES or hashlib.sha256(body).hexdigest() != context['fingerprint']:raise ValueError()
    except (KeyError, TypeError, ValueError):
        raise PlanningConflict('저장된 Worker 관찰 계획 맥락의 출처·유형·지문을 확인하세요.') from None
    return context


def priorities(context):
    require(context)
    requested = {check for row in context['items'] for check in PRIORITIES[row['category']]}
    return [check['id'] for check in CATALOG if check['id'] in requested]


def provider_items(context):
    require(context)
    return [{key: row[key] for key in ('id', 'task_id', 'asset_id', 'scope_revision', 'category')} for row in context['items']]
