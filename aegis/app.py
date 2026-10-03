import asyncio
import csv
import hashlib
import hmac
import io
import json
import os
import secrets
import sqlite3
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from urllib.parse import urljoin, urlsplit

from fastapi import Depends, FastAPI, HTTPException, Request, Response, Query
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, field_validator, model_validator
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import __version__
from .checks import CATALOG, CHECK_IDS
from .engine import Engine
from .network import in_scope, normalize_url
from .store import Store, identifier, now
from .auth import password_hash, public_user, new_user
from .maintenance import WorkspaceLease
from .migrations import SCHEMA_VERSION
from .http_limits import BodyLimitMiddleware
from .coverage import planned_slots, task_rows, latest_summary
from .graph import build_graph, GraphNotFound
from .findings import update_triage, TriageConflict


class Credentials(BaseModel):
    username: str = Field(default='admin', min_length=1, max_length=64, pattern=r'^[a-zA-Z0-9_.-]+$')
    password: str = Field(min_length=12, max_length=256)
    setup_token: str = Field(default='', max_length=256)


class AuthorizationRule(BaseModel):
    path: str = Field(max_length=1000)
    role: str = Field(min_length=1, max_length=80)
    expected_allowed: bool
    credential_env: str = Field(default='', max_length=100, pattern=r'^(|AEGIS_TEST_[A-Z0-9_]+)$')

    @field_validator('path')
    @classmethod
    def validate_path(cls, value):
        if not value.startswith('/') or value.startswith('//') or '?' in value or '#' in value:
            raise ValueError('루트 기준 경로만 허용합니다. 쿼리와 fragment는 사용할 수 없습니다.')
        return value


class AssetInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    url: str = Field(max_length=2000)
    type: Literal['web', 'api', 'service'] = 'web'
    owner: str = Field(default='', max_length=100)
    tags: list[str] = Field(default_factory=list, max_length=10)
    authorization_rules: list[AuthorizationRule] = Field(default_factory=list, max_length=20)
    authorized: bool

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, value):
        normalized = list(dict.fromkeys(tag.strip() for tag in value if tag.strip()))
        if any(len(tag) > 80 for tag in normalized):
            raise ValueError('태그는 80자 이하로 입력하세요.')
        return normalized

    @field_validator('url')
    @classmethod
    def validate_url(cls, value):
        url = normalize_url(value)
        if urlsplit(url).query:
            raise ValueError('자산 주소에 쿼리를 넣지 마세요.')
        return url

    @model_validator(mode='after')
    def validate_scope(self):
        if not self.authorized:
            raise ValueError('자산 검증 권한을 확인해야 합니다.')
        for rule in self.authorization_rules:
            if not in_scope(urljoin(self.url, rule.path), self.url):
                raise ValueError('권한 규칙이 자산 범위를 벗어났습니다.')
        return self


class TaskInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    goal: str = Field(default='등록된 자산의 보안 설정과 접근 권한을 검증합니다.', max_length=2000)
    asset_ids: list[str] = Field(min_length=1, max_length=20)
    checks: list[str] = Field(default_factory=lambda: [c['id'] for c in CATALOG], min_length=1, max_length=6)
    workers: int = Field(default=3, ge=1, le=4)
    planner: Literal['rules', 'ai'] = 'rules'

    @field_validator('checks')
    @classmethod
    def validate_checks(cls, value):
        if not set(value) <= CHECK_IDS or len(value) != len(set(value)):
            raise ValueError('등록된 검증 도구만 선택할 수 있습니다.')
        return value

    @field_validator('asset_ids')
    @classmethod
    def validate_assets(cls, value):
        if len(value) != len(set(value)):
            raise ValueError('중복 자산을 제거하세요.')
        return value


class NoteInput(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1, max_length=10000)


class MessageInput(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class FindingUpdate(BaseModel):
    expected_revision: int = Field(ge=1)
    status: Literal['open', 'accepted', 'resolved'] | None = None
    assignee_id: str | None = Field(default=None, max_length=80)
    acceptance_reason: str = Field(default='', max_length=4000)
    resolution_reason: str = Field(default='', max_length=4000)

    @field_validator('acceptance_reason', 'resolution_reason')
    @classmethod
    def trim_reason(cls, value):
        return value.strip()

    @field_validator('assignee_id')
    @classmethod
    def trim_assignee(cls, value):
        return value.strip() or None if value is not None else None

    @model_validator(mode='after')
    def require_change(self):
        if not self.model_fields_set - {'expected_revision'} or ('status' in self.model_fields_set and self.status is None):
            raise ValueError('변경할 상태·담당자·사유를 입력하세요.')
        return self


class AssetArchive(BaseModel):
    archived: bool


class ScheduleInput(TaskInput):
    interval_hours: int = Field(ge=1, le=720)


class UserInput(BaseModel):
    username: str = Field(min_length=1, max_length=64, pattern=r'^[a-zA-Z0-9_.-]+$')
    name: str = Field(min_length=1, max_length=100)
    role: Literal['admin', 'operator', 'viewer']
    password: str = Field(min_length=12, max_length=256)


class UserUpdate(BaseModel):
    expected_updated_at: float | None = Field(default=None, gt=0)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    role: Literal['admin', 'operator', 'viewer'] | None = None
    disabled: bool | None = None


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=12, max_length=256)


class PasswordReset(BaseModel):
    password: str = Field(min_length=12, max_length=256)


def create_app(data_dir=None, allow_private=None):
    folder = Path(data_dir or os.environ.get('AEGIS_DATA_DIR', 'data'))
    lease = WorkspaceLease(folder)
    try:
        store = Store(folder / 'aegis.db')
    except BaseException:
        lease.close()
        raise
    private = allow_private if allow_private is not None else os.environ.get('AEGIS_LAB_MODE') == '1'
    engine = Engine(store, private)
    scheduler_stop = threading.Event()
    shutdown_requested = threading.Event()
    auth_lock = threading.Lock()
    login_attempts = {}

    def create_task(data, retest_of=None, schedule_id=None):
        with store.lock:
            return create_task_locked(data, retest_of, schedule_id)

    def create_task_locked(data, retest_of=None, schedule_id=None):
        assets = [store.get('assets', id) for id in data.asset_ids]
        if any(a is None for a in assets):
            raise HTTPException(400, '존재하지 않는 자산입니다.')
        if any(a.get('archived_at') for a in assets):
            raise HTTPException(409, '보관된 자산은 검증할 수 없습니다. 먼저 복원하세요.')
        triage_revision = None
        if retest_of:
            finding = store.get('findings', retest_of)
            if not finding:
                raise HTTPException(404, '발견 사항이 없습니다.')
            with store.connect() as db:
                row = db.execute("SELECT data FROM records WHERE kind='tasks' AND json_extract(data,'$.retest_of')=? AND json_extract(data,'$.status') IN ('pending','queued','running','stopping') LIMIT 1", (retest_of,)).fetchone()
                if row:
                    return json.loads(row['data'])
            triage_revision = finding.get('triage_revision', 1)
        if store.count('tasks', statuses=['pending','queued','running','stopping']) >= 30:
            raise HTTPException(409, '대기·실행 작업 한도(30개)를 초과했습니다.')
        task = dict(data.model_dump(), id=identifier(), status='pending', created_at=now(),
                    started_at=None, finished_at=None, approved_at=None, done=0, errors=0,
                    scope_snapshot=assets, retest_of=retest_of, schedule_id=schedule_id,
                    retest_triage_revision=triage_revision)
        store.put_many([('tasks', task)] + [('coverage', row) for row in planned_slots(task)])
        store.event(task['id'], '작업 생성. 실행 범위와 검증 도구의 승인을 기다립니다.')
        return task

    def scheduler():
        while not scheduler_stop.wait(5) and not shutdown_requested.is_set():
            with store.lock:
                for schedule in store.all('schedules'):
                    if not schedule['enabled'] or schedule['next_at'] > now():
                        continue
                    # Scheduled tasks also require explicit approval; never silently widen authorization.
                    try:
                        create_task(TaskInput(**schedule['task']), schedule_id=schedule['id'])
                        store.patch('schedules', schedule['id'], next_at=now() + schedule['interval_hours'] * 3600, last_at=now())
                    except Exception:
                        store.patch('schedules', schedule['id'], next_at=now() + 300)
                        store.event(None, '예약 작업을 생성하지 못했습니다. 5분 후 다시 시도합니다.', 'warning')

    @asynccontextmanager
    async def lifespan(app):
        thread = threading.Thread(target=scheduler, name='aegis-scheduler', daemon=True)
        thread.start()
        try:
            yield
        finally:
            scheduler_stop.set()
            thread.join(timeout=6)
            try:
                await asyncio.to_thread(engine.shutdown)
            finally:
                lease.close()

    app = FastAPI(title='Open Aegis', version=__version__, lifespan=lifespan)
    app.state.store, app.state.engine = store, engine
    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # Pydantic's default error payload includes the invalid input. Never echo
        # passwords, credentials or whole imported records in validation responses.
        errors = [{'loc': error['loc'], 'type': error['type'], 'msg': error['msg']}
                  for error in exc.errors()]
        return JSONResponse({'detail': errors}, status_code=422)

    app.state.shutdown_requested = shutdown_requested
    hosts = os.environ.get('AEGIS_ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver').split(',')
    app.add_middleware(BodyLimitMiddleware)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts)

    @app.middleware('http')
    async def protections(request, call_next):
        if shutdown_requested.is_set():
            return JSONResponse({'detail': '서버가 종료 중입니다.'}, status_code=503)
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            source = request.headers.get('origin')
            if source and (urlsplit(source).netloc != request.headers.get('host') or urlsplit(source).scheme != request.url.scheme):
                return JSONResponse({'detail': '다른 출처의 변경 요청은 허용하지 않습니다.'}, status_code=403)
        actor = store.session_user(request.cookies.get('aegis_session', ''))
        response = await call_next(request)
        if actor and request.method not in ('GET', 'HEAD', 'OPTIONS') and request.url.path.startswith('/api/'):
            store.event(None, '사용자 변경 요청', detail={'actor_id': actor['id'], 'username': actor['username'], 'role': actor['role'], 'method': request.method, 'path': request.url.path, 'status': response.status_code})
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        return response

    def authenticated(request: Request):
        token = request.cookies.get('aegis_session', '')
        user = store.session_user(token) if token else None
        if not user:
            raise HTTPException(401, '로그인이 필요합니다.')
        return user

    def operator(user=Depends(authenticated)):
        if user['role'] not in ('admin', 'operator'):
            raise HTTPException(403, '운영자 또는 관리자 권한이 필요합니다.')
        return user

    def administrator(user=Depends(authenticated)):
        if user['role'] != 'admin':
            raise HTTPException(403, '관리자 권한이 필요합니다.')
        return user

    auth = [Depends(authenticated)]
    operations = [Depends(operator)]
    admins = [Depends(administrator)]

    @app.get('/api/health')
    def health():
        return {'status': 'ok', 'version': __version__}

    @app.get('/api/auth/status')
    def auth_status(request: Request):
        user = store.session_user(request.cookies.get('aegis_session', ''))
        return {'setup_required': not store.users(), 'authenticated': bool(user), 'user': public_user(user)}

    @app.post('/api/auth/setup')
    def setup(data: Credentials, request: Request, response: Response):
        with auth_lock:
            if store.users():
                raise HTTPException(409, '관리자 계정이 이미 설정되었습니다.')
            configured_token = os.environ.get('AEGIS_SETUP_TOKEN')
            local = request.client and request.client.host in ('127.0.0.1', '::1', 'testclient')
            if configured_token:
                if not hmac.compare_digest(data.setup_token, configured_token):
                    raise HTTPException(403, '설치 토큰을 확인하세요.')
            elif not local:
                raise HTTPException(403, '원격 설치는 AEGIS_SETUP_TOKEN 설정이 필요합니다.')
            user = store.add_user(new_user(data.username.lower(), '관리자', 'admin', data.password))
            store.event(None, '최초 관리자 설정', detail={'actor_id': user['id'], 'username': user['username']})
        return begin_session(response, user)

    def begin_session(response, user):
        token = secrets.token_urlsafe(48)
        store.session(token, now() + 8 * 3600, user['id'])
        response.set_cookie('aegis_session', token, httponly=True, samesite='strict', max_age=8 * 3600,
                            secure=os.environ.get('AEGIS_SECURE_COOKIE') == '1')
        return {'authenticated': True, 'user': public_user(user)}

    @app.post('/api/auth/login')
    def login(data: Credentials, request: Request, response: Response):
        address = request.client.host if request.client else 'unknown'
        with auth_lock:
            attempts = [t for t in login_attempts.get(address, []) if t > now() - 300]
            if len(attempts) >= 10:
                raise HTTPException(429, '로그인 시도가 많습니다. 5분 후 다시 시도하세요.')
            attempts.append(now())
            login_attempts[address] = attempts
        user = store.user(username=data.username.lower())
        # Unknown usernames still incur the same password derivation cost.
        expected = user or {'salt': '00' * 16, 'password_hash': '00' * 32}
        valid = hmac.compare_digest(password_hash(data.password, expected['salt']), expected['password_hash'])
        if not valid or not user or user['disabled']:
            raise HTTPException(401, '비밀번호를 확인하세요.')
        with auth_lock:
            login_attempts.pop(address, None)
        store.event(None, '로그인 성공', detail={'actor_id': user['id'], 'username': user['username']})
        return begin_session(response, user)

    @app.post('/api/auth/logout', dependencies=auth)
    def logout(request: Request, response: Response):
        store.logout(request.cookies.get('aegis_session', ''))
        response.delete_cookie('aegis_session')
        return {'ok': True}

    @app.post('/api/auth/password', dependencies=auth)
    def change_password(data: PasswordChange, user=Depends(authenticated)):
        with auth_lock, store.lock:
            fresh = store.user(id=user['id'])
            if not hmac.compare_digest(password_hash(data.current_password, fresh['salt']), fresh['password_hash']):
                raise HTTPException(403, '현재 비밀번호를 확인하세요.')
            replacement = new_user(user['username'], user['name'], user['role'], data.new_password)
            store.update_user(user['id'], salt=replacement['salt'], password_hash=replacement['password_hash'])
        return {'ok': True, 'login_required': True}

    @app.get('/api/users', dependencies=admins)
    def list_users():
        return [public_user(u) for u in store.users()]

    @app.post('/api/users', dependencies=admins)
    def add_user(data: UserInput):
        with auth_lock, store.lock:
            if len(store.users()) >= 100:
                raise HTTPException(409, '사용자 한도(100명)를 초과했습니다.')
            try:
                return public_user(store.add_user(new_user(data.username.lower(), data.name, data.role, data.password)))
            except sqlite3.IntegrityError as exc:
                raise HTTPException(409, '이미 등록된 사용자 이름입니다.') from exc

    @app.patch('/api/users/{user_id}', dependencies=admins)
    def update_user(user_id: str, data: UserUpdate):
        with auth_lock, store.lock:
            user = store.user(id=user_id)
            if not user:
                raise HTTPException(404, '사용자가 없습니다.')
            if data.expected_updated_at is not None and data.expected_updated_at != user['updated_at']:
                raise HTTPException(409, '다른 관리자가 사용자를 수정했습니다. 목록을 새로 불러온 뒤 다시 적용하세요.')
            changes = data.model_dump(exclude_none=True, exclude={'expected_updated_at'})
            after = {**user, **changes}
            if user['role'] == 'admin' and not user['disabled'] and (after['role'] != 'admin' or after['disabled']):
                if sum(u['role'] == 'admin' and not u['disabled'] for u in store.users()) <= 1:
                    raise HTTPException(409, '마지막 활성 관리자는 비활성화하거나 권한을 낮출 수 없습니다.')
            return public_user(store.update_user(user_id, **changes))

    @app.post('/api/users/{user_id}/password', dependencies=admins)
    def reset_password(user_id: str, data: PasswordReset):
        with auth_lock, store.lock:
            user = store.user(id=user_id)
            if not user:
                raise HTTPException(404, '사용자가 없습니다.')
            replacement = new_user(user['username'], user['name'], user['role'], data.password)
            store.update_user(user_id, salt=replacement['salt'], password_hash=replacement['password_hash'])
        return {'ok': True}

    @app.get('/api/overview', dependencies=auth)
    def overview():
        tasks, findings = store.page('tasks', limit=100)['items'], store.page('findings', limit=100)['items']
        assets = store.page('assets', archived=False, limit=100)['items']
        coverage = store.page('coverage', limit=100)['items']
        with store.connect() as db:
            summary = latest_summary(db)
            severity_counts = {f'findings_{row[0]}': row[1] for row in db.execute("SELECT json_extract(data,'$.severity'),count(*) FROM records WHERE kind='findings' AND json_extract(data,'$.status')='open' GROUP BY json_extract(data,'$.severity')")}
        return {'assets': assets, 'tasks': tasks, 'findings': findings, 'coverage': coverage,
                'coverage_summary': {k: v for k, v in summary.items() if k != 'assets'},
                'observations': store.page('observations', limit=100)['items'], 'events': store.recent_events(),
                'list_limit': 100,
                'stats': {**severity_counts, 'assets': store.count('assets', active_assets=True), 'tasks': store.count('tasks'),
                          'running': store.count('tasks', statuses=['running', 'queued', 'stopping']),
                          'pending': store.count('tasks', statuses=['pending']),
                          'findings': store.count('findings', statuses=['open']),
                          'covered_assets': summary['covered_assets'],
                          'requests': store.count('traffic')}}

    @app.get('/api/records/{kind}', dependencies=auth)
    def records(kind: Literal['assets', 'tasks', 'findings', 'traffic'],
                limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0, le=10_000_000),
                snapshot: int | None = Query(None, ge=0, le=9_223_372_036_854_775_807),
                search: str = Query('', max_length=200), status: str | None = Query(None, max_length=80),
                severity: str | None = Query(None, max_length=80), asset_id: str | None = Query(None, max_length=80),
                task_id: str | None = Query(None, max_length=80), archived: bool | None = None):
        if archived is not None and kind != 'assets':
            raise HTTPException(422, '보관 필터는 자산에만 사용할 수 있습니다.')
        return store.page(kind, limit=limit, offset=offset, snapshot=snapshot, search=search, archived=archived,
                          filters={k: v for k, v in {'status': status, 'severity': severity, 'asset_id': asset_id, 'task_id': task_id}.items() if v is not None})

    @app.get('/api/assets', dependencies=auth)
    def assets(response: Response, include_archived: bool = False):
        return legacy_page(response, 'assets', archived=None if include_archived else False)

    @app.get('/api/graph', dependencies=auth)
    def graph(asset_id: str = Query(min_length=1, max_length=80), task_id: str | None = Query(None, max_length=80),
              check: str | None = Query(None, max_length=80), severity: Literal['critical', 'high', 'medium', 'low', 'info'] | None = None,
              status: Literal['open', 'accepted', 'resolved'] | None = None,
              limit: int = Query(10, ge=1, le=25), offset: int = Query(0, ge=0, le=10_000_000),
              snapshot: int | None = Query(None, ge=0, le=9_223_372_036_854_775_807)):
        if check is not None and check not in CHECK_IDS:
            raise HTTPException(422, '등록된 검증 도구를 선택하세요.')
        try:
            return build_graph(store, asset_id, task_id, check=check, severity=severity, status=status,
                               limit=limit, offset=offset, snapshot=snapshot)
        except GraphNotFound as exc:
            raise HTTPException(404, str(exc)) from exc

    def legacy_page(response, kind, **options):
        result = store.page(kind, limit=1000, **options)
        response.headers['X-Total-Count'] = str(result['total'])
        response.headers['X-Results-Limited'] = str(result['has_more']).lower()
        return result['items']

    def save_asset(data):
        if any(a['url'] == data.url for a in store.all('assets')):
            raise HTTPException(409, '이미 등록된 자산 주소입니다.')
        asset = dict(data.model_dump(), id=identifier(), created_at=now(), revision=1, archived_at=None)
        store.put('assets', asset)
        store.event(None, '자산 등록: ' + data.name, detail={'asset_id': asset['id']})
        return asset

    @app.post('/api/assets', dependencies=operations)
    def add_asset(data: AssetInput):
        with store.lock:
            return save_asset(data)

    @app.post('/api/assets/import', dependencies=operations)
    def import_assets(data: list[AssetInput]):
        with store.lock:
            return import_assets_locked(data)

    def import_assets_locked(data):
        if len(data) > 100:
            raise HTTPException(400, '한 번에 최대 100개 자산을 가져올 수 있습니다.')
        # Validate the entire batch before writing any records.
        urls = [a.url for a in data]
        existing = {a['url'] for a in store.all('assets')}
        if len(set(urls)) != len(urls) or set(urls) & existing:
            raise HTTPException(409, '중복 자산이 있습니다. 가져오기를 적용하지 않았습니다.')
        return [save_asset(a) for a in data]

    def editable_asset(asset_id):
        asset = store.get('assets', asset_id)
        if not asset:
            raise HTTPException(404, '자산이 없습니다.')
        if any(asset_id in t['asset_ids'] and t['status'] in ('queued', 'running', 'stopping')
               for t in store.all('tasks')):
            raise HTTPException(409, '실행 중인 자산은 변경할 수 없습니다. 작업 종료 후 다시 시도하세요.')
        return asset

    @app.put('/api/assets/{asset_id}', dependencies=operations)
    def edit_asset(asset_id: str, data: AssetInput):
        with engine.lock, store.lock:
            previous = editable_asset(asset_id)
            if previous.get('archived_at'):
                raise HTTPException(409, '보관된 자산은 복원한 후 수정하세요.')
            if data.url != previous['url']:
                if any(asset_id in t['asset_ids'] for t in store.all('tasks')):
                    raise HTTPException(409, '검증 이력이 있는 주소는 변경할 수 없습니다. 새 자산으로 등록하세요.')
                if any(a['id'] != asset_id and a['url'] == data.url for a in store.all('assets')):
                    raise HTTPException(409, '이미 등록된 자산 주소입니다.')
            asset = store.patch('assets', asset_id, **data.model_dump(), revision=previous.get('revision', 1) + 1, updated_at=now())
            store.event(None, '자산 수정: ' + data.name, detail={'asset_id': asset_id, 'revision': asset['revision']})
            return asset

    @app.post('/api/assets/{asset_id}/archive', dependencies=operations)
    def archive_asset(asset_id: str, data: AssetArchive):
        with engine.lock, store.lock:
            previous = editable_asset(asset_id)
            if bool(previous.get('archived_at')) == data.archived:
                return previous
            asset = store.patch('assets', asset_id, archived_at=now() if data.archived else None,
                                revision=previous.get('revision', 1) + 1, updated_at=now())
            paused = []
            if data.archived:
                for schedule in store.all('schedules'):
                    if schedule['enabled'] and asset_id in schedule['task']['asset_ids']:
                        store.patch('schedules', schedule['id'], enabled=False)
                        paused.append(schedule['id'])
            store.event(None, ('자산 보관: ' if data.archived else '자산 복원: ') + asset['name'],
                        detail={'asset_id': asset_id, 'paused_schedules': paused})
            return asset

    @app.get('/api/tasks', dependencies=auth)
    def tasks(response: Response):
        return legacy_page(response, 'tasks')

    @app.post('/api/tasks', dependencies=operations)
    def add_task(data: TaskInput):
        return create_task(data)

    @app.get('/api/tasks/{task_id}', dependencies=auth)
    def task_detail(task_id: str):
        task = store.get('tasks', task_id)
        if not task:
            raise HTTPException(404, '작업이 없습니다.')
        return {'task': task, 'events': store.events(task_id=task_id, limit=1000),
                'coverage': task_rows(store, task),
                'findings': [f for f in store.all('findings') if task_id in f['task_ids']]}

    @app.post('/api/tasks/{task_id}/approve', dependencies=admins)
    def approve(task_id: str):
        if not store.get('tasks', task_id):
            raise HTTPException(404, '작업이 없습니다.')
        try:
            engine.start(task_id)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        return store.get('tasks', task_id)

    @app.post('/api/tasks/{task_id}/stop', dependencies=operations)
    def stop(task_id: str):
        if not store.get('tasks', task_id):
            raise HTTPException(404, '작업이 없습니다.')
        return engine.stop(task_id)

    @app.get('/api/tasks/{task_id}/messages', dependencies=auth)
    def messages(task_id: str):
        if not store.get('tasks', task_id):
            raise HTTPException(404, '작업이 없습니다.')
        return sorted([m for m in store.all('messages') if m['task_id'] == task_id], key=lambda m: m['created_at'])

    @app.post('/api/tasks/{task_id}/messages', dependencies=operations)
    def ask(task_id: str, data: MessageInput):
        task = store.get('tasks', task_id)
        if not task:
            raise HTTPException(404, '작업이 없습니다.')
        store.put('messages', {'id': identifier(), 'task_id': task_id, 'role': 'user', 'content': data.content, 'created_at': now()})
        findings = [f for f in store.all('findings') if task_id in f['task_ids']]
        coverage = [c for c in task_rows(store, task) if c['status'] == 'completed']
        findings.sort(key=lambda f: ['critical', 'high', 'medium', 'low', 'info'].index(f['severity']))
        answer = [f"작업 상태: {task['status']}. {len(task['asset_ids'])}개 자산 중 {task['done']}개 처리, {len(coverage)}개 검증 완료, {task['errors']}개 오류입니다."]
        if task['status'] == 'pending':
            answer.append('아직 대상 요청을 보내지 않았습니다. 실행 범위를 확인한 후 승인하세요.')
        if any(word in data.content for word in ('수정', '조치', '우선', '해결')):
            answer += [f"[{f['severity'].upper()}] {f['title']} ({f['asset_name']}): {f['remediation']}" for f in findings[:8]]
        else:
            answer += [f"[{f['severity'].upper()}] {f['title']} · 판정 유형: {f['confidence']} · 상태: {f['status']}" for f in findings[:8]]
        if not findings:
            answer.append('이 작업에 연결된 발견 사항이 없습니다. 미실행·검증 실패·미지원 취약점은 별도로 확인해야 합니다.')
        answer.append('이 답변은 저장된 작업·증거의 규칙 기반 요약입니다. 추가 요청이나 명령을 실행하지 않습니다.')
        return store.put('messages', {'id': identifier(), 'task_id': task_id, 'role': 'assistant', 'content': '\n\n'.join(answer),
                                     'finding_ids': [f['id'] for f in findings[:8]], 'created_at': now()})

    @app.get('/api/findings', dependencies=auth)
    def findings(response: Response):
        return legacy_page(response, 'findings')

    @app.get('/api/assignees', dependencies=auth)
    def assignees(search: str = Query('', max_length=100), limit: int = Query(25, ge=1, le=100),
                  offset: int = Query(0, ge=0, le=10_000_000)):
        with store.connect() as db:
            db.execute('BEGIN')
            where = "disabled=0 AND role IN ('admin','operator') AND instr(lower(name||' '||username),lower(?))>0"
            total = db.execute('SELECT count(*) FROM users WHERE ' + where, (search,)).fetchone()[0]
            items = [dict(row) for row in db.execute('SELECT id,name,username,role FROM users WHERE ' + where + ' ORDER BY name,id LIMIT ? OFFSET ?', (search, limit, offset))]
        return {'items': items, 'total': total, 'limit': limit, 'offset': offset, 'has_more': offset + len(items) < total}

    @app.get('/api/findings/{finding_id}/history', dependencies=auth)
    def finding_history(finding_id: str, limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0, le=10_000_000),
                        snapshot: int | None = Query(None, ge=0, le=9_223_372_036_854_775_807)):
        if not store.get('findings', finding_id):
            raise HTTPException(404, '발견 사항이 없습니다.')
        return store.page('finding_history', limit=limit, offset=offset, snapshot=snapshot, filters={'finding_id': finding_id})

    @app.get('/api/findings/{finding_id}', dependencies=auth)
    def finding_detail(finding_id: str):
        finding = store.get('findings', finding_id)
        if not finding:
            raise HTTPException(404, '발견 사항이 없습니다.')
        return {'finding': finding, 'evidence': [store.get('evidence', id) for id in finding['evidence_ids']],
                'retests': [r for r in store.all('retests') if r['finding_id'] == finding_id]}

    @app.patch('/api/findings/{finding_id}', dependencies=operations)
    def update_finding(finding_id: str, data: FindingUpdate, actor=Depends(operator)):
        try:
            result = update_triage(store, finding_id, data.model_dump(exclude_unset=True), actor)
        except KeyError:
            raise HTTPException(404, '발견 사항이 없습니다.')
        except TriageConflict as exc:
            raise HTTPException(409, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        store.event(None, '발견 사항 조치 기록 저장 요청을 처리했습니다.', detail={'finding_id': finding_id, 'status': result['status'], 'actor_id': actor['id']})
        return result

    @app.post('/api/findings/{finding_id}/retest', dependencies=operations)
    def retest(finding_id: str):
        finding = store.get('findings', finding_id)
        if not finding:
            raise HTTPException(404, '발견 사항이 없습니다.')
        return create_task(TaskInput(name='재검증 · ' + finding['title'], asset_ids=[finding['asset_id']],
                                     checks=[finding['check']], workers=1), retest_of=finding_id)

    @app.get('/api/traffic', dependencies=auth)
    def traffic(response: Response, task_id: str | None = None):
        return legacy_page(response, 'traffic', filters={'task_id': task_id} if task_id else {})

    @app.get('/api/events', dependencies=auth)
    def events(after: int = 0, task_id: str | None = None):
        return store.events(after=max(after, 0), task_id=task_id, limit=1000)

    @app.get('/api/events/stream', dependencies=auth)
    async def event_stream(request: Request, after: int = 0):
        async def stream():
            cursor = max(after, 0)
            for _ in range(60):
                if shutdown_requested.is_set() or await request.is_disconnected():
                    break
                if not store.valid_session(request.cookies.get('aegis_session', '')):
                    break
                entries = store.events(after=cursor)
                for entry in entries:
                    cursor = entry['seq']
                    yield f"id: {cursor}\ndata: {json.dumps(entry, ensure_ascii=False)}\n\n"
                if not entries:
                    yield ': heartbeat\n\n'
                await asyncio.sleep(0.5)
        return StreamingResponse(stream(), media_type='text/event-stream', headers={'X-Accel-Buffering': 'no'})

    @app.get('/api/tools', dependencies=auth)
    def tools():
        return CATALOG

    @app.get('/api/settings', dependencies=auth)
    def settings():
        return {'version': __version__, 'schema_version': SCHEMA_VERSION, 'storage': 'sqlite', 'lab_mode': private,
                'llm_configured': bool(os.environ.get('AEGIS_LLM_API_KEY') and os.environ.get('AEGIS_LLM_MODEL')),
                'llm_model': os.environ.get('AEGIS_LLM_MODEL', ''), 'request_budget': 24, 'max_workers': 4,
                'agents': [{'id': 'planner', 'name': 'Planner', 'role': '승인된 도구의 실행 순서를 계획', 'tools': ['catalog']},
                           {'id': 'worker', 'name': 'Worker', 'role': '범위 내 검증과 증거 수집', 'tools': list(CHECK_IDS)},
                           {'id': 'retester', 'name': 'Retester', 'role': '기존 발견 사항을 독립 작업으로 재검증', 'tools': list(CHECK_IDS)}]}

    @app.get('/api/notes', dependencies=auth)
    def notes():
        return store.all('notes')

    @app.post('/api/notes', dependencies=operations)
    def add_note(data: NoteInput):
        return store.put('notes', dict(data.model_dump(), id=identifier(), created_at=now()))

    @app.delete('/api/notes/{note_id}', dependencies=operations)
    def delete_note(note_id: str):
        if not store.get('notes', note_id):
            raise HTTPException(404, '노트가 없습니다.')
        with store.lock, store.connect() as db:
            db.execute('DELETE FROM records WHERE kind=? AND id=?', ('notes', note_id))
        return {'ok': True}

    @app.get('/api/schedules', dependencies=auth)
    def schedules():
        return store.all('schedules')

    @app.post('/api/schedules', dependencies=operations)
    def add_schedule(data: ScheduleInput):
        with store.lock:
            return add_schedule_locked(data)

    def add_schedule_locked(data):
        for id in data.asset_ids:
            asset = store.get('assets', id)
            if not asset:
                raise HTTPException(400, '존재하지 않는 자산입니다.')
            if asset.get('archived_at'):
                raise HTTPException(409, '보관된 자산은 예약할 수 없습니다.')
        return store.put('schedules', {'id': identifier(), 'task': data.model_dump(exclude={'interval_hours'}),
                          'interval_hours': data.interval_hours, 'enabled': True,
                          'next_at': now() + data.interval_hours * 3600, 'last_at': None, 'created_at': now()})

    @app.post('/api/schedules/{schedule_id}/toggle', dependencies=operations)
    def toggle_schedule(schedule_id: str):
        with store.lock:
            return toggle_schedule_locked(schedule_id)

    def toggle_schedule_locked(schedule_id):
        schedule = store.get('schedules', schedule_id)
        if not schedule:
            raise HTTPException(404, '예약이 없습니다.')
        if not schedule['enabled'] and any(not store.get('assets', id) or store.get('assets', id).get('archived_at') for id in schedule['task']['asset_ids']):
            raise HTTPException(409, '보관된 자산이 있어 예약을 재개할 수 없습니다.')
        return store.patch('schedules', schedule_id, enabled=not schedule['enabled'], next_at=now() + schedule['interval_hours'] * 3600)

    @app.get('/api/reports/export', dependencies=auth)
    def export(format: Literal['json', 'csv', 'markdown'] = 'markdown', task_id: str | None = None):
        selected_tasks = [t for t in store.all('tasks') if not task_id or t['id'] == task_id]
        if task_id and not selected_tasks:
            raise HTTPException(404, '작업이 없습니다.')
        selected_findings = [f for f in store.all('findings') if not task_id or task_id in f['task_ids']]
        if format == 'json':
            ids = {t['id'] for t in selected_tasks}
            finding_ids = {f['id'] for f in selected_findings}
            payload = {'version': __version__, 'generated_at': now(), 'tasks': selected_tasks, 'findings': selected_findings,
                       'evidence': [e for e in store.all('evidence') if e['task_id'] in ids],
                       'finding_history': [entry for entry in store.all('finding_history') if entry['finding_id'] in finding_ids],
                       'coverage': [row for task in selected_tasks for row in task_rows(store, task)],
                       'traffic': [t for t in store.all('traffic') if t['task_id'] in ids]}
            content, media, suffix = json.dumps(payload, ensure_ascii=False, indent=2), 'application/json', 'json'
        elif format == 'csv':
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(['severity', 'status', 'title', 'asset', 'check', 'confidence', 'remediation'])
            def cell(value):
                value = str(value)
                return "'" + value if value.lstrip().startswith(('=', '+', '-', '@')) else value
            for finding in selected_findings:
                writer.writerow([cell(finding[k]) for k in ('severity', 'status', 'title', 'asset_name', 'check', 'confidence', 'remediation')])
            content, media, suffix = '\ufeff' + buf.getvalue(), 'text/csv', 'csv'
        else:
            lines = ['# Open Aegis 검증 보고서', '', f'생성 시각: {time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())}', '',
                     '설정 관찰·권한 규칙 불일치는 확인된 침입 또는 데이터 유출과 구분됩니다.', '']
            for task in selected_tasks:
                lines += ['## 작업: ' + task['name'], '', '상태: ' + task['status'], '검증 도구: ' + ', '.join(task['checks']),
                          f"처리 자산: {task['done']}/{len(task['asset_ids'])} · 오류: {task['errors']}", '']
                rows = task_rows(store, task)
                lines += [f"검증 완료: {sum(row['status'] == 'completed' for row in rows)}/{len(rows)} (선택한 자산 × 도구)", '']
                for row in rows:
                    lines += [f"- {row['asset_id']} / {row['check']}: {row['status']} · {row.get('reason', '')}"]
                lines += ['']
            for finding in selected_findings:
                lines += ['## [' + finding['severity'].upper() + '] ' + finding['title'], '',
                          '자산: ' + finding['asset_name'], '상태: ' + finding['status'],
                          '담당자: ' + (finding.get('assignee_name') or '미지정'),
                          '위험 수용 사유: ' + finding.get('acceptance_reason', ''),
                          '해결 사유: ' + finding.get('resolution_reason', ''),
                          '판정 유형: ' + finding['confidence'], '', '```json',
                          json.dumps(finding['evidence'], ensure_ascii=False, indent=2), '```', '', finding['remediation'], '']
            content, media, suffix = '\n'.join(lines), 'text/markdown', 'md'
        return Response(content, media_type=media, headers={'Content-Disposition': f'attachment; filename="aegis-report.{suffix}"'})

    dist = Path(os.environ.get('AEGIS_WEB_DIR', str(Path(__file__).resolve().parent.parent / 'web' / 'dist')))
    if dist.exists():
        app.mount('/assets', StaticFiles(directory=dist / 'assets'), name='web-assets')
        @app.get('/')
        def index():
            return FileResponse(dist / 'index.html')
    return app
