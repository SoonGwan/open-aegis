"""Independent adapter for reviewed ScopeSentry asset NDJSON exports.

No source connection or target requests. Preview records contain only reviewed fields.
"""
import hashlib
import json
import re
from urllib.parse import urlsplit

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

from .audit import append_event
from .network import normalize_url
from .store_util import identifier, now

MAX_BYTES = 1024 * 1024
MAX_ROWS = 100
PREVIEW_TTL = 900
FORMAT = 'scopesentry-asset-ndjson-v1'


class PreviewInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    source_key: str = Field(min_length=1, max_length=64, pattern=r'^[A-Za-z0-9_.-]+$')
    export: str = Field(min_length=1, max_length=MAX_BYTES)


class ApplyInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    selected: list[str] = Field(min_length=1, max_length=MAX_ROWS)
    authorized: bool


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def source_id(source_key, external_id):
    return hashlib.sha256((source_key + '\0' + external_id).encode()).hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def invalid_constant(_value):
    raise ValueError('non-JSON constant')


def parse_export(text):
    try:
        if len(text.encode('utf-8')) > MAX_BYTES:
            raise HTTPException(413, 'ScopeSentry 파일은 UTF-8 기준 1 MiB 이하로 나누어 보내세요.')
    except UnicodeEncodeError:
        raise HTTPException(422, '올바른 UTF-8 텍스트를 보내세요.') from None
    lines = [line for line in text.removeprefix('\ufeff').split('\n') if line.strip()]
    if not 1 <= len(lines) <= MAX_ROWS:
        raise HTTPException(422, '한 파일에는 비어 있지 않은 줄 1–100개를 넣으세요.')
    result, seen = [], set()
    for number, line in enumerate(lines, 1):
        try:
            row = json.loads(line, object_pairs_hook=unique_object, parse_constant=invalid_constant)
        except (ValueError, RecursionError):
            raise HTTPException(422, f'{number}번째 레코드의 JSON 형식을 확인하세요.') from None
        if not isinstance(row, dict):
            raise HTTPException(422, f'{number}번째 레코드는 JSON 객체여야 합니다. 배열 대신 한 줄에 하나씩 보내세요.')
        item = {'line': number, 'external_id': None, 'url': None, 'status': 'invalid', 'reason': ''}
        external_id = row.get('_id')
        if not isinstance(external_id, str) or not re.fullmatch(r'[a-fA-F0-9]{24}', external_id):
            item['reason'] = '원본 _id가 24자리 ObjectID 문자열이 아닙니다.'
        else:
            external_id = external_id.lower()
            if external_id in seen:
                raise HTTPException(422, '같은 원본 ID가 반복됩니다. 파일을 확인하세요.')
            seen.add(external_id)
            item['external_id'] = external_id
            if row.get('type') != 'http':
                item.update(status='unsupported', reason='HTTP 자산만 가져올 수 있습니다.')
            elif not isinstance(row.get('url'), str) or len(row['url']) > 2000:
                item['reason'] = '2000자 이하의 HTTP/HTTPS url이 필요합니다.'
            else:
                try:
                    url = normalize_url(row['url'])
                    url.encode('utf-8')
                    if urlsplit(url).query or any(ord(c) < 32 or ord(c) == 127 for c in url):
                        raise ValueError('query/control')
                    item.update(url=url, status='ready')
                except (ValueError, UnicodeError):
                    item['reason'] = '쿼리·인증정보·fragment·제어 문자가 없는 HTTP/HTTPS 주소를 보내세요.'
        result.append(item)
    return result


def read(db, kind, record_id):
    row = db.execute('SELECT data FROM records WHERE kind=? AND id=?', (kind, record_id)).fetchone()
    return json.loads(row['data']) if row else None


def target_asset(db, url):
    rows = db.execute("SELECT data FROM records WHERE kind='assets' AND json_extract(data,'$.url')=? LIMIT 2", (url,)).fetchall()
    if len(rows) > 1:
        raise HTTPException(409, '같은 주소의 기존 자산이 여러 개입니다. 중복을 정리한 후 다시 미리보세요.')
    return json.loads(rows[0]['data']) if rows else None


def inspect(db, item, source_key):
    link = read(db, 'asset_sources', source_id(source_key, item['external_id']))
    previous_asset = read(db, 'assets', link['asset_id']) if link else None
    asset = target_asset(db, item['url'])
    blocked = bool((asset and asset.get('archived_at')) or (link and previous_asset is None))
    action = 'blocked' if blocked else 'create' if asset is None else 'link'
    changed = bool(link and link['source_url'] != item['url'])
    if link and not changed and asset:
        action = 'seen' if not blocked else action
    return {
        **item, 'status': 'blocked' if blocked else 'ready', 'action': action,
        'source_changed': changed, 'previous_url': link['source_url'] if changed else None,
        'asset_id': asset['id'] if asset else None,
        'expected_source': digest(link), 'expected_asset': digest(asset),
        'reason': '보관된 자산을 복원하거나 누락된 출처 연결을 확인한 후 다시 미리보세요.' if blocked else '',
    }


def public_preview(record):
    return {key: record[key] for key in ('id', 'format', 'source_key', 'export_sha256', 'created_at', 'expires_at')} | {
        'rows': [{k: v for k, v in item.items() if not k.startswith('expected_')} for item in record['rows']]}


def preview(store, data, actor_id):
    rows = parse_export(data.export)
    timestamp = now()
    with store.lock, store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute("DELETE FROM records WHERE kind='import_previews' AND json_extract(data,'$.expires_at')<=?", (timestamp,))
        count = db.execute("SELECT count(*) FROM records WHERE kind='import_previews'").fetchone()[0]
        if count >= 50:
            raise HTTPException(429, '열린 가져오기 미리보기가 50개입니다. 만료 후 다시 시도하세요.')
        rows = [inspect(db, row, data.source_key) if row['status'] == 'ready' else row for row in rows]
        record = {'id': identifier(), 'format': FORMAT, 'source_key': data.source_key, 'actor_id': actor_id,
                  'export_sha256': hashlib.sha256(data.export.encode()).hexdigest(), 'created_at': timestamp,
                  'expires_at': timestamp + PREVIEW_TTL, 'rows': rows, 'applied_at': None}
        db.execute("INSERT INTO records VALUES ('import_previews',?,?)", (record['id'], json.dumps(record, ensure_ascii=False)))
    return public_preview(record)


def apply(store, preview_id, data, actor_id):
    if data.authorized is not True:
        raise HTTPException(422, '선택한 주소의 검증 권한을 확인하세요. 작업 실행에는 별도 승인이 필요합니다.')
    if len(set(data.selected)) != len(data.selected):
        raise HTTPException(422, '선택한 원본 ID가 반복됩니다.')
    timestamp = now()
    with store.lock, store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        record = read(db, 'import_previews', preview_id)
        if not record:
            raise HTTPException(404, '가져오기 미리보기가 없습니다. 다시 미리보세요.')
        if record['actor_id'] != actor_id:
            raise HTTPException(403, '이 미리보기를 만든 사용자만 반영할 수 있습니다.')
        if record['expires_at'] <= timestamp:
            raise HTTPException(410, '미리보기가 만료됐습니다. 현재 파일과 자산으로 다시 미리보세요.')
        selected = sorted(data.selected)
        if record.get('applied_at'):
            if selected != record['selected']:
                raise HTTPException(409, '이미 반영한 미리보기의 선택을 바꿀 수 없습니다. 다시 미리보세요.')
            return record['result']
        candidates = {row['external_id']: row for row in record['rows'] if row['status'] == 'ready'}
        if not set(selected) <= candidates.keys():
            raise HTTPException(422, '가져올 수 있는 미리보기 항목만 선택하세요.')
        # Verify the complete selection before any write, against the reviewed snapshot.
        for external_id in selected:
            row = candidates[external_id]
            current = inspect(db, row, record['source_key'])
            if any(current[key] != row[key] for key in ('expected_source', 'expected_asset', 'status')):
                raise HTTPException(409, '미리보기 이후 자산 또는 출처가 바뀌었습니다. 다시 미리보세요.')
        result = {'preview_id': preview_id, 'created': 0, 'linked': 0, 'seen': 0, 'source_changed': 0, 'items': []}
        for external_id in selected:
            row = candidates[external_id]
            asset = target_asset(db, row['url'])
            if asset is None:
                asset = {'id': identifier(), 'name': urlsplit(row['url']).netloc[:100], 'url': row['url'], 'type': 'web',
                         'owner': '', 'tags': [], 'authorization_rules': [], 'authorized': True,
                         'created_at': timestamp, 'revision': 1, 'archived_at': None}
                db.execute("INSERT INTO records VALUES ('assets',?,?)", (asset['id'], json.dumps(asset, ensure_ascii=False)))
                result['created'] += 1
            link_id = source_id(record['source_key'], external_id)
            previous = read(db, 'asset_sources', link_id)
            if previous:
                result['seen' if previous['source_url'] == row['url'] else 'source_changed'] += 1
            else:
                result['linked'] += 1
            link = {'id': link_id, 'asset_id': asset['id'], 'source_key': record['source_key'], 'external_id': external_id,
                    'source_url': row['url'], 'format': FORMAT, 'first_seen': previous['first_seen'] if previous else timestamp,
                    'last_seen': timestamp, 'preview_id': preview_id, 'export_sha256': record['export_sha256']}
            if previous and previous['asset_id'] != asset['id']:
                history = {**previous, 'id': identifier(), 'replaced_at': timestamp}
                db.execute("INSERT INTO records VALUES ('asset_source_history',?,?)", (history['id'], json.dumps(history, ensure_ascii=False)))
            db.execute("INSERT INTO records VALUES ('asset_sources',?,?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data", (link_id, json.dumps(link, ensure_ascii=False)))
            result['items'].append({'external_id': external_id, 'asset_id': asset['id'], 'url': asset['url']})
        record.update(applied_at=timestamp, selected=selected, result=result)
        db.execute("UPDATE records SET data=? WHERE kind='import_previews' AND id=?", (json.dumps(record, ensure_ascii=False), preview_id))
        append_event(db, (timestamp, None, 'info', 'ScopeSentry 자산 가져오기를 반영했습니다.',
                         json.dumps({'actor_id': actor_id, 'preview_id': preview_id, 'source_key': record['source_key'],
                                     'export_sha256': record['export_sha256'], 'selected': len(selected),
                                     **{key: result[key] for key in ('created', 'linked', 'seen', 'source_changed')}}, ensure_ascii=False)))
    return result
