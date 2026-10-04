import asyncio
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import threading
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
from .tool_contracts import contracts_for
from .engine import Engine
from .network import in_scope, normalize_url
from .store import Store, identifier, now, compact_finding, MessageRequestConflict
from .auth import password_hash, public_user, new_user
from .maintenance import WorkspaceLease, WorkspaceBusy
from .migrations import SCHEMA_VERSION
from .http_limits import BodyLimitMiddleware
from .coverage import planned_slots, task_rows, iter_task_rows
from .graph import build_graph, GraphNotFound
from .findings import update_triage, TriageConflict
from .runtime import ExecutionPolicy
from .reporting import report_stream, ReportResponse
from .export_limits import ExportPolicy, ExportPool
from .policy_models import AuthorizationRule
from .reproduction import build_manifest, MAX_MANIFEST_BYTES
from .audit_review import AuditReview, AuditReviewBusy, AuditReviewInput
from .login_limits import LoginGate, LoginLimited
from . import scopesentry
from .usage import usage_summary
from .conversation import summarize_task
from . import conversation_ai, call_ledger
from .runtime import TaskControl
from .scopesentry_remote import Sources, PageInput
from .http_queries import SQLiteHTTP,PostgresHTTP
from .worker_observations import task_page as observation_page
from . import worker_process, worker_dependencies, next_plan, planning_history
from . import todos
from .event_planner import EventPlanner
from . import observation_context
from . import observation_execution
from . import goal_planner


class Credentials(BaseModel):
    username: str = Field(default='admin', min_length=1, max_length=64, pattern=r'^[a-zA-Z0-9_.-]+$')
    password: str = Field(min_length=12, max_length=256)
    setup_token: str = Field(default='', max_length=256)


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


class NextPlanInput(BaseModel):
    fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")


class TaskInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    goal: str = Field(default='등록된 자산의 보안 설정과 접근 권한을 검증합니다.', max_length=2000)
    asset_ids: list[str] = Field(min_length=1, max_length=20)
    checks: list[str] = Field(default_factory=lambda: [c['id'] for c in CATALOG], min_length=1, max_length=6)
    workers: int = Field(default=3, ge=1, le=4)
    planner: Literal['rules', 'ai'] = 'rules'
    worker_dependencies: dict[str, list[str]] = Field(default_factory=dict)

    @model_validator(mode='after')
    def validate_dependencies(self):
        worker_dependencies.validate(self.asset_ids, self.worker_dependencies)
        return self

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
    request_id: str | None = Field(default=None, min_length=16, max_length=80, pattern=r'^[a-zA-Z0-9_-]+$')
    mode: Literal['rules','ai'] = 'rules'

    @model_validator(mode='after')
    def ai_request_key(self):
        if self.mode=='ai' and not self.request_id:
            raise ValueError('AI 대화는 재시도 전송 ID가 필요합니다.')
        return self


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
    policy = ExecutionPolicy.from_env()
    exports = ExportPool(ExportPolicy.from_env())
    backend=os.environ.get('AEGIS_STORAGE_BACKEND','sqlite')
    if backend not in ('sqlite','postgres'):
        raise ValueError('AEGIS_STORAGE_BACKEND는 sqlite 또는 postgres여야 합니다.')
    lease=None;engine=None
    private = allow_private if allow_private is not None else os.environ.get('AEGIS_LAB_MODE') == '1'
    native_errors=(WorkspaceBusy,)
    user_conflicts=(sqlite3.IntegrityError,)
    try:
        if backend=='postgres':
            from .postgres_store import PostgresStore
            from .postgres_transfer import driver
            store=PostgresStore(os.environ.get('AEGIS_POSTGRES_DSN',''),os.environ.get('AEGIS_POSTGRES_SCHEMA',''))
            native_errors=(WorkspaceBusy,driver()[0].Error)
            user_conflicts=(driver()[0].IntegrityError,)
        else:
            folder = Path(data_dir or os.environ.get('AEGIS_DATA_DIR', 'data'))
            lease = WorkspaceLease(folder)
            store = Store(folder / 'aegis.db')
            call_ledger.recover(store)
            goal_planner.recover(store)
        engine = Engine(store, private, policy=policy)
    except BaseException as exc:
        if lease:lease.close()
        if backend=='postgres' and isinstance(exc,Exception) and not isinstance(exc,WorkspaceBusy):
            raise RuntimeError('PostgreSQL 저장소를 시작하지 못했습니다. 연결·스키마·형식을 확인하세요.') from None
        raise
    queries=PostgresHTTP(store) if backend=='postgres' else SQLiteHTTP(store)
    audit_review = AuditReview(store)
    scheduler_stop = threading.Event()
    event_planner = EventPlanner(store, lambda: engine.policy.public())
    shutdown_requested = threading.Event()
    try:
        source_connections = Sources.from_env(store, shutdown_requested)
    except BaseException:
        engine.shutdown()
        if lease:lease.close()
        raise
    auth_lock = threading.Lock()
    chat_lock = threading.Lock()
    goal_lock = threading.Lock()
    login_gate = LoginGate()

    def create_task(data, retest_of=None, schedule_id=None, retry_of=None):
        with store.lock:
            return create_task_locked(data, retest_of, schedule_id, retry_of)

    def create_task_locked(data, retest_of=None, schedule_id=None, retry_of=None, *, replacing=None, followup=None, resuming=None, observation_request=None, planned_id=None, goal_draft=None):
        assets = [store.get('assets', id) for id in data.asset_ids]
        if any(a is None for a in assets):
            raise HTTPException(400, '존재하지 않는 자산입니다.')
        if any(a.get('archived_at') for a in assets):
            raise HTTPException(409, '보관된 자산은 검증할 수 없습니다. 먼저 복원하세요.')
        attempt_source = replacing or resuming
        if attempt_source:
            if replacing and replacing.get('approved_at'):
                raise HTTPException(409, '승인된 실행을 대기 계획으로 교체할 수 없습니다.')
            try:
                history = planning_history.history(store, attempt_source['id'])
                if resuming:
                    existing, kind = planning_history.continuation(store, resuming)
                    if existing:
                        if kind != 'retry':raise planning_history.PlanningConflict('이미 후속 계획을 만들었습니다. 연결된 계획을 확인하세요.')
                        return existing
                    # Adopt the active pre-upgrade retry without creating a parallel branch.
                    related = queries.active_related_task('retry_of', retry_of)
                    if related:
                        planning_history.history(store, related['id'])
                        store.put('tasks', {**resuming, 'retry_successor': related['id']})
                        return related
                if len(history) >= planning_history.MAX_HISTORY:
                    raise planning_history.PlanningConflict('계획 이력 한도(32개)에 도달했습니다.')
            except (planning_history.PlanningConflict, LookupError) as exc:
                raise HTTPException(409, str(exc)) from exc
        elif retry_of:
            related=queries.active_related_task('retry_of',retry_of)
            if related:return related
        triage_revision = None
        if retest_of:
            finding = store.get('findings', retest_of)
            if not finding:
                raise HTTPException(404, '발견 사항이 없습니다.')
            related=queries.active_related_task('retest_of',retest_of,replacing['id'] if replacing else '')
            if related:
                if replacing or resuming:raise HTTPException(409, '같은 발견의 다른 재검증 계획이 진행 중입니다.')
                return related
            triage_revision = finding.get('triage_revision', 1)
        if store.count('tasks', statuses=['pending','queued','running','stopping']) - (1 if replacing else 0) >= engine.policy.pending_limit:
            raise HTTPException(409, f'대기·실행 작업 한도({engine.policy.pending_limit}개)를 초과했습니다.')
        if attempt_source and attempt_source.get('observation_execution'):
            previous = attempt_source['observation_execution']
            try:
                current = observation_execution.preview(store, previous['source_task_id'])['context']
                selection = observation_execution.Selection(fingerprint=current['fingerprint'],
                    observation_ids=previous['observation_ids'], checks=data.checks, request_id=identifier()+identifier())
                observation_request = (previous['source_task_id'], selection)
            except (planning_history.PlanningConflict, LookupError, ValueError) as exc:
                raise HTTPException(409, str(exc)) from exc
        task = dict(data.model_dump(), id=planned_id or identifier(), status='pending', created_at=now(),
                    started_at=None, finished_at=None, approved_at=None, done=0, errors=0,
                    scope_snapshot=assets, retest_of=retest_of, schedule_id=schedule_id,
                    retest_triage_revision=triage_revision, retry_of=retry_of, execution_policy=engine.policy.public(),
                    tool_contracts=contracts_for(data.checks), replan_of=replacing['id'] if replacing else None)
        if attempt_source:
            task.update(planning_history.metadata(attempt_source))
            if attempt_source.get('goal_plan'):task['goal_plan']=attempt_source['goal_plan']
            try:task['shared_todo_context']=todos.planning_context(store,attempt_source['id'])
            except planning_history.PlanningConflict as exc:raise HTTPException(409,str(exc)) from exc
            try:task['worker_observation_context']=observation_context.snapshot(store,attempt_source['id'])
            except planning_history.PlanningConflict as exc:raise HTTPException(409,str(exc)) from exc
        if followup:
            source, proposal = followup
            task.update(followup_of=source['id'], followup_fingerprint=proposal['fingerprint'],
                        planning_round=proposal['planning_round'],shared_todo_context=proposal['shared_todo_context'])
            task['worker_observation_context']=proposal['worker_observation_context']
        if observation_request:
            source_id, selection = observation_request
            try:
                context, execution = observation_execution.prepare(store, source_id, selection)
                task.update(worker_observation_context=context, observation_execution=execution)
                if planned_id:task['observation_selection'] = selection.model_dump()
                observation_execution.require(task)
            except (planning_history.PlanningConflict, LookupError) as exc:
                raise HTTPException(409, str(exc)) from exc
        if goal_draft:
            task['goal_plan']={key:goal_draft[key] for key in ('basis_fingerprint','goal','decomposition','mode','fingerprint')}
            task['goal_plan']['draft_id']=goal_draft['id']
            if 'execution' in goal_draft:task['goal_plan']['execution']=goal_draft['execution']
        try:goal_planner.require_task(task)
        except planning_history.PlanningConflict as exc:raise HTTPException(409,str(exc)) from exc
        records = [('tasks', task)] + [('coverage', row) for row in planned_slots(task)]
        if goal_draft:records.append(('goal_plans',{**goal_draft,'accepted_task_id':task['id']}))
        if followup:
            records.append(('tasks', {**source, 'next_plan_id': task['id'],
                                      'next_plan_fingerprint': proposal['fingerprint']}))
        if resuming:
            records.append(('tasks', {**resuming, 'retry_successor': task['id']}))
        if replacing:
            records.append(('tasks', {**replacing, 'status': 'rejected', 'finished_at': now(),
                                     'replaced_by': task['id'], 'termination_reason': 'replanned'}))
            records.extend(('coverage', {**row, 'status': 'cancelled', 'updated_at': now(),
                           'reason': '새 승인 계획으로 대체되어 실행하지 않았습니다.'})
                           for row in iter_task_rows(store, replacing) if row['status'] not in
                           ('completed','skipped','failed','cancelled','interrupted','not_recorded'))
        # Source, replacement and both coverage matrices commit or roll back together.
        if followup:
            with store.write_transaction() as db:
                try:fresh=next_plan.propose(store,source['id'],engine.policy.public(),connection=db)
                except (planning_history.PlanningConflict,LookupError) as exc:raise HTTPException(409,str(exc)) from exc
                if not fresh['available'] or fresh['fingerprint']!=proposal['fingerprint'] or assets!=fresh['scope_snapshot']:
                    raise HTTPException(409,'계획 근거·공유 할 일이 변경되었습니다. 제안을 다시 확인하세요.')
                store.put_many(records,connection=db)
                store.event(task['id'], '작업 생성. 실행 범위와 검증 도구의 승인을 기다립니다.',connection=db)
        elif goal_draft:
            with store.write_transaction() as db:
                try:fresh=goal_planner.snapshot(store,goal_draft['task_id'],engine.policy.public(),connection=db)
                except (planning_history.PlanningConflict,LookupError) as exc:raise HTTPException(409,str(exc)) from exc
                persisted=store.get('goal_plans',goal_draft['id'],connection=db)
                if goal_planner.digest(fresh)!=goal_draft['basis_fingerprint'] or persisted!=goal_draft:
                    raise HTTPException(409,'목표 초안의 출처·범위·입력·상태가 변경되었습니다. 새 초안을 만드세요.')
                store.put_many(records,connection=db)
                store.event(task['id'],'검토한 목표 초안을 승인 대기 계획에 반영했습니다.',
                    detail={'draft_id':goal_draft['id'],'mode':goal_draft['mode']},connection=db)
        elif observation_request:
            with store.write_transaction() as db:
                try:
                    fresh_context, fresh_execution = observation_execution.prepare(store, source_id, selection, connection=db)
                except (planning_history.PlanningConflict, LookupError) as exc:raise HTTPException(409, str(exc)) from exc
                if (fresh_execution != execution or
                        any(store.get('assets', asset['id'], connection=db) != asset for asset in assets)):
                    raise HTTPException(409, '선택한 관찰 또는 자산 범위가 변경되었습니다.')
                store.put_many(records, connection=db)
                store.event(task['id'], '선택한 관찰 응답의 검증 계획 생성. 별도 실행 승인을 기다립니다.',
                    detail={'observation_ids': selection.observation_ids, 'source_task_id': source_id}, connection=db)
        else:
            store.put_many(records)
            store.event(task['id'], '작업 생성. 실행 범위와 검증 도구의 승인을 기다립니다.')
        if replacing:
            store.event(replacing['id'], '현재 범위와 도구의 새 승인 계획으로 대체했습니다.', detail={'replaced_by': task['id']})
        return task

    def scheduler():
        while not scheduler_stop.wait(5) and not shutdown_requested.is_set():
            try:
                with store.lock:
                    for schedule in store.due_schedules(now()):
                        # Scheduled tasks also require explicit approval; never silently widen authorization.
                        try:
                            create_task(TaskInput(**schedule['task']), schedule_id=schedule['id'])
                            store.patch('schedules', schedule['id'], next_at=now() + schedule['interval_hours'] * 3600, last_at=now())
                        except Exception:
                            store.patch('schedules', schedule['id'], next_at=now() + 300)
                            store.event(None, '예약 작업을 생성하지 못했습니다. 5분 후 다시 시도합니다.', 'warning')
            except WorkspaceBusy:
                shutdown_requested.set()
                return
            except native_errors:
                # Retry a transient read failure without exposing SQL/credentials.
                continue

    @asynccontextmanager
    async def lifespan(app):
        thread = threading.Thread(target=scheduler, name='aegis-scheduler', daemon=True)
        thread.start()
        event_planner.start()
        try:
            yield
        finally:
            scheduler_stop.set()
            thread.join(timeout=6)
            try:
                await asyncio.to_thread(event_planner.close)
                await asyncio.to_thread(engine.shutdown)
            finally:
                if lease:lease.close()

    app = FastAPI(title='Open Aegis', version=__version__, lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.state.store, app.state.engine = store, engine
    app.state.event_planner = event_planner
    app.state.exports = exports
    app.state.source_connections = source_connections
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
        try:
            if backend=='postgres' and engine.closed:
                raise WorkspaceBusy('실행 소유권이 종료되었습니다.')
            actor = await asyncio.to_thread(store.session_user,request.cookies.get('aegis_session', ''))
            response = await call_next(request)
            # Audit verification is readonly and must work on a damaged chain.
            if actor and request.method not in ('GET', 'HEAD', 'OPTIONS') and request.url.path.startswith('/api/') and request.url.path != '/api/audit/verify':
                await asyncio.to_thread(store.event,None,'사용자 변경 요청',detail={'actor_id': actor['id'], 'username': actor['username'], 'role': actor['role'], 'method': request.method, 'path': request.url.path, 'status': response.status_code})
        except native_errors:
            response=JSONResponse({'detail':'저장소 연결 또는 실행 소유권을 확인할 수 없습니다. 서버 상태를 확인하세요.'},status_code=503)
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

    @app.get('/api/openapi.json', dependencies=admins, include_in_schema=False)
    def openapi_schema():
        return JSONResponse(app.openapi(), headers={'Cache-Control': 'no-store'})

    @app.get('/api/health')
    def health(response: Response):
        healthy = engine.queue_thread.is_alive() and not engine.closed
        if not healthy:response.status_code = 503
        return {'status': 'ok' if healthy else 'degraded', 'version': __version__}

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
        try:
            with login_gate.attempt(address) as attempt:
                user = store.user(username=data.username.lower())
                # Unknown usernames still incur the same password derivation cost.
                expected = user or {'salt': '00' * 16, 'password_hash': '00' * 32}
                valid = hmac.compare_digest(password_hash(data.password, expected['salt']), expected['password_hash'])
                if not valid or not user or user['disabled']:
                    raise HTTPException(401, '비밀번호를 확인하세요.')
                attempt.succeeded()
                store.event(None, '로그인 성공', detail={'actor_id': user['id'], 'username': user['username']})
                return begin_session(response, user)
        except LoginLimited as exc:
            raise HTTPException(429, f'로그인 요청이 제한되었습니다. {exc.retry_after}초 후 다시 시도하세요.',
                                headers={'Retry-After': str(exc.retry_after)}) from exc

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
            except user_conflicts as exc:
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
        tasks, findings = store.page('tasks', limit=100)['items'], store.page('findings', limit=100, compact_findings=True)['items']
        assets = store.page('assets', archived=False, limit=100)['items']
        coverage = store.page('coverage', limit=100)['items']
        summary,severity_counts=queries.overview_summary()
        return {'assets': assets, 'tasks': tasks, 'findings': findings, 'coverage': coverage,
                'coverage_summary': {k: v for k, v in summary.items() if k != 'assets'},
                'observations': store.page('observations', limit=100)['items'], 'events': store.recent_events(),
                'list_limit': 100,
                'stats': {**severity_counts, 'assets': store.count('assets', active_assets=True), 'tasks': store.count('tasks'),
                          'running': store.count('tasks', statuses=['running', 'queued', 'stopping']),
                          'pending': store.count('tasks', statuses=['pending']),
                          'findings': store.count('findings', statuses=['open']),
                          'covered_assets': summary['covered_assets'],
                          'requests': store.count('traffic'), 'observations': store.count('observations')}}

    @app.get('/api/llm/usage', dependencies=auth)
    def llm_usage(days: Literal['7', '30'] | None = None,
                  source: Literal['planner', 'conversation', 'all'] = 'planner',
                  ledger: Literal['persisted','attempts'] = 'persisted'):
        return usage_summary(store, int(days) if days else None, source=source, ledger=ledger)

    @app.get('/api/llm/calls', dependencies=auth)
    def llm_calls(limit: int = Query(25,ge=1,le=100), offset: int = Query(0,ge=0,le=10_000_000),
                  snapshot: int | None = Query(None,ge=0,le=9_223_372_036_854_775_807),
                  search: str = Query('',max_length=200), task_id: str | None = Query(None,max_length=80),
                  source: Literal['planner','conversation'] | None = None,
                  state: Literal['started','observed','committed','uncommitted','interrupted'] | None = None):
        return store.page('llm_calls',limit=limit,offset=offset,snapshot=snapshot,search=search,
                          filters={key:value for key,value in {'task_id':task_id,'source':source,'state':state}.items() if value is not None})

    @app.get('/api/records/{kind}', dependencies=auth)
    def records(kind: Literal['assets', 'tasks', 'findings', 'traffic', 'notes', 'schedules', 'observations'],
                limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0, le=10_000_000),
                snapshot: int | None = Query(None, ge=0, le=9_223_372_036_854_775_807),
                search: str = Query('', max_length=200), status: str | None = Query(None, max_length=80),
                severity: str | None = Query(None, max_length=80), asset_id: str | None = Query(None, max_length=80),
                task_id: str | None = Query(None, max_length=80), archived: bool | None = None,
                enabled: bool | None = None):
        if archived is not None and kind != 'assets':
            raise HTTPException(422, '보관 필터는 자산에만 사용할 수 있습니다.')
        if enabled is not None and kind != 'schedules':
            raise HTTPException(422, '활성 필터는 예약에만 사용할 수 있습니다.')
        return store.page(kind, limit=limit, offset=offset, snapshot=snapshot, search=search, archived=archived,
                          filters={k: v for k, v in {'status': status, 'severity': severity, 'asset_id': asset_id, 'task_id': task_id, 'enabled': enabled}.items() if v is not None}, compact_findings=True)

    @app.get('/api/assets', dependencies=auth)
    def assets(response: Response, include_archived: bool = False):
        return legacy_page(response, 'assets', archived=None if include_archived else False)

    @app.get('/api/integrations/scopesentry/connections', dependencies=operations)
    def scopesentry_connections():
        return source_connections.public()

    @app.post('/api/integrations/scopesentry/remote/preview')
    def scopesentry_remote(data: PageInput, actor=Depends(operator)):
        return source_connections.collect(data, actor['id'])

    @app.post('/api/integrations/scopesentry/preview')
    def scopesentry_preview(data: scopesentry.PreviewInput, actor=Depends(operator)):
        return scopesentry.preview(store, data, actor['id'])

    @app.post('/api/integrations/scopesentry/{preview_id}/apply')
    def scopesentry_apply(preview_id: str, data: scopesentry.ApplyInput, actor=Depends(operator)):
        with engine.lock:
            if engine.closed:
                raise HTTPException(409, '서버가 종료 중입니다.')
            return scopesentry.apply(store, preview_id, data, actor['id'])

    @app.get('/api/assets/{asset_id}/sources', dependencies=auth)
    def asset_sources(asset_id: str, history: bool = False, limit: int = Query(25, ge=1, le=100),
                      offset: int = Query(0, ge=0, le=10_000_000), search: str = Query('', max_length=200),
                      snapshot: int | None = Query(None, ge=0, le=9_223_372_036_854_775_807)):
        if not store.get('assets', asset_id):
            raise HTTPException(404, '자산이 없습니다.')
        return store.page('asset_source_history' if history else 'asset_sources', limit=limit,
                          offset=offset, snapshot=snapshot, search=search, filters={'asset_id': asset_id})

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
        result = store.page(kind, limit=1000, compact_findings=True, **options)
        response.headers['X-Total-Count'] = str(result['total'])
        response.headers['X-Results-Limited'] = str(result['has_more']).lower()
        return result['items']

    def save_asset(data):
        if store.asset_url_exists(data.url):
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
        if len(set(urls)) != len(urls) or any(store.asset_url_exists(url) for url in urls):
            raise HTTPException(409, '중복 자산이 있습니다. 가져오기를 적용하지 않았습니다.')
        return [save_asset(a) for a in data]

    def editable_asset(asset_id):
        asset = store.get('assets', asset_id)
        if not asset:
            raise HTTPException(404, '자산이 없습니다.')
        if store.asset_has_tasks(asset_id, active_only=True):
            raise HTTPException(409, '실행 중인 자산은 변경할 수 없습니다. 작업 종료 후 다시 시도하세요.')
        return asset

    @app.put('/api/assets/{asset_id}', dependencies=operations)
    def edit_asset(asset_id: str, data: AssetInput):
        with engine.lock, store.lock:
            previous = editable_asset(asset_id)
            if previous.get('archived_at'):
                raise HTTPException(409, '보관된 자산은 복원한 후 수정하세요.')
            if data.url != previous['url']:
                if store.asset_has_tasks(asset_id):
                    raise HTTPException(409, '검증 이력이 있는 주소는 변경할 수 없습니다. 새 자산으로 등록하세요.')
                if store.asset_url_exists(data.url, exclude_id=asset_id):
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
                for schedule_id in store.enabled_schedule_ids(asset_id):
                    store.patch('schedules', schedule_id, enabled=False)
                    paused.append(schedule_id)
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
        findings = store.page('findings', filters={'task_id':task_id}, compact_findings=True)
        events = store.event_page(task_id)
        return {'task': task, 'events': events['items'],
                'coverage': task_rows(store, task),
                'findings': findings['items'],
                'findings_page': {key:value for key,value in findings.items() if key != 'items'},
                'events_page': {key:value for key,value in events.items() if key != 'items'}}

    @app.get('/api/tasks/{task_id}/policy-reproduction', dependencies=auth)
    def policy_reproduction(task_id: str):
        task = store.get('tasks', task_id)
        if not task:
            raise HTTPException(404, '작업이 없습니다.')
        try:
            payload = build_manifest(task).model_dump_json().encode()
        except (ValueError, KeyError, TypeError):
            raise HTTPException(409, '승인·API 규칙·실행 제한이 있는 작업만 내보낼 수 있습니다.') from None
        if len(payload) > MAX_MANIFEST_BYTES:
            raise HTTPException(413, '정책 파일의 크기 제한을 초과했습니다.')
        return Response(payload, media_type='application/json', headers={
            'Content-Disposition': 'attachment; filename="aegis-api-policy.json"', 'Cache-Control': 'no-store'})

    @app.get('/api/tasks/{task_id}/findings', dependencies=auth)
    @app.get('/api/tasks/{task_id}/events', dependencies=auth)
    def task_collection(task_id: str, request: Request,
                        limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0, le=10_000_000),
                        snapshot: int | None = Query(None, ge=0, le=9_223_372_036_854_775_807),
                        search: str = Query('', max_length=200)):
        if not store.get('tasks', task_id):
            raise HTTPException(404, '작업이 없습니다.')
        if request.url.path.endswith('/events'):
            return store.event_page(task_id, limit=limit, offset=offset, snapshot=snapshot, search=search)
        return store.page('findings', limit=limit, offset=offset, snapshot=snapshot, search=search,
                          filters={'task_id':task_id}, compact_findings=True)

    @app.get('/api/tasks/{task_id}/observations', dependencies=auth)
    def worker_observations(task_id: str,
                            limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0, le=10_000_000),
                            snapshot: int | None = Query(None, ge=0, le=9_223_372_036_854_775_807),
                            search: str = Query('', max_length=200)):
        try:
            return observation_page(store, task_id, limit=limit, offset=offset, snapshot=snapshot, search=search)
        except LookupError:
            raise HTTPException(404, '작업이 없습니다.')

    @app.get('/api/worker-events', dependencies=auth)
    def worker_history(limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0, le=10_000_000),
                       snapshot: int | None = Query(None, ge=0, le=9_223_372_036_854_775_807),
                       search: str = Query('', max_length=200),
                       task_id: str | None = Query(None, min_length=1, max_length=80),
                       asset_id: str | None = Query(None, min_length=1, max_length=80)):
        return worker_process.search_events(store, limit=limit, offset=offset, snapshot=snapshot,
                                            search=search, task_id=task_id, asset_id=asset_id)

    def todo_response(function, *args, **kwargs):
        try:return function(store,*args,**kwargs)
        except (todos.TodoConflict, planning_history.PlanningConflict) as exc:
            raise HTTPException(409,str(exc)) from exc
        except LookupError as exc:raise HTTPException(404,str(exc)) from exc
        except ValueError as exc:raise HTTPException(422,str(exc)) from exc

    @app.get('/api/tasks/{task_id}/todos', dependencies=auth)
    def task_todos(task_id: str, limit: int = Query(25,ge=1,le=100),
                   offset: int = Query(0,ge=0,le=10_000_000),
                   snapshot: int | None = Query(None,ge=0,le=9_223_372_036_854_775_807),
                   search: str = Query('',max_length=200)):
        return todo_response(todos.page,task_id,limit=limit,offset=offset,snapshot=snapshot,search=search)

    @app.post('/api/tasks/{task_id}/todos', dependencies=operations)
    def create_todo(task_id: str, data: todos.TodoCreate, actor=Depends(operator)):
        return todo_response(todos.create,task_id,data.model_dump(),actor)

    @app.get('/api/tasks/{task_id}/todos/{todo_id}', dependencies=auth)
    def get_todo(task_id: str, todo_id: str):
        return todo_response(todos.get,task_id,todo_id)

    @app.patch('/api/tasks/{task_id}/todos/{todo_id}', dependencies=operations)
    def update_todo(task_id: str, todo_id: str, data: todos.TodoUpdate, actor=Depends(operator)):
        return todo_response(todos.update,task_id,todo_id,data.model_dump(exclude_unset=True),actor)

    @app.get('/api/tasks/{task_id}/todos/{todo_id}/history', dependencies=auth)
    def todo_history(task_id: str, todo_id: str, limit: int = Query(25,ge=1,le=100),
                     offset: int = Query(0,ge=0,le=10_000_000),
                     snapshot: int | None = Query(None,ge=0,le=9_223_372_036_854_775_807),
                     search: str = Query('',max_length=200)):
        return todo_response(todos.page,task_id,todo_id=todo_id,limit=limit,offset=offset,snapshot=snapshot,search=search)

    @app.get('/api/tasks/{task_id}/workers', dependencies=auth)
    def workers(task_id: str):
        try:return worker_process.list_workers(store, task_id)
        except worker_process.WorkerMissing as exc:raise HTTPException(404, str(exc)) from exc

    @app.get('/api/tasks/{task_id}/workers/{asset_id}', dependencies=auth)
    def worker_detail(task_id: str, asset_id: str):
        try:return worker_process.get_process(store, task_id, asset_id)
        except worker_process.WorkerMissing as exc:raise HTTPException(404, str(exc)) from exc

    @app.get('/api/tasks/{task_id}/workers/{asset_id}/{kind}', dependencies=auth)
    def worker_collection(task_id: str, asset_id: str, kind: Literal['events','observations'],
                          limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0, le=10_000_000),
                          snapshot: int | None = Query(None, ge=0, le=9_223_372_036_854_775_807),
                          search: str = Query('', max_length=200)):
        try:return worker_process.collection(store, task_id, asset_id, kind, limit=limit, offset=offset,
                                             snapshot=snapshot, search=search)
        except worker_process.WorkerMissing as exc:raise HTTPException(404, str(exc)) from exc

    @app.post('/api/tasks/{task_id}/approve', dependencies=admins)
    def approve(task_id: str):
        if not store.get('tasks', task_id):
            raise HTTPException(404, '작업이 없습니다.')
        try:
            engine.start(task_id)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        return store.get('tasks', task_id)

    @app.post('/api/tasks/{task_id}/retry', dependencies=operations)
    def retry_task(task_id: str):
        with engine.lock, store.lock:
            if engine.closed:raise HTTPException(409, '서버가 종료 중입니다.')
            original=store.get('tasks',task_id)
            if not original:raise HTTPException(404,'작업이 없습니다.')
            if original.get('id') != task_id:raise HTTPException(409, '저장 키와 작업 ID가 일치하지 않습니다.')
            if original['status'] not in ('failed','interrupted','stopped'):
                raise HTTPException(409,'실패·중단·중지된 작업만 새 계획으로 다시 실행할 수 있습니다.')
            data=TaskInput(**{**original,'name':('재실행 · '+original['name'])[:120]})
            return create_task_locked(data,retest_of=original.get('retest_of'),schedule_id=original.get('schedule_id'),retry_of=task_id,resuming=original)

    @app.get('/api/tasks/{task_id}/next-plan', dependencies=auth)
    def get_next_plan(task_id: str):
        try:return next_plan.propose(store, task_id, engine.policy.public())
        except LookupError as exc:raise HTTPException(404, str(exc)) from exc
        except next_plan.NextPlanConflict as exc:raise HTTPException(409, str(exc)) from exc

    @app.get('/api/tasks/{task_id}/observation-plan', dependencies=auth)
    def observation_plan(task_id: str):
        try:return observation_execution.preview(store, task_id)
        except LookupError as exc:raise HTTPException(404, str(exc)) from exc
        except planning_history.PlanningConflict as exc:raise HTTPException(409, str(exc)) from exc

    @app.post('/api/tasks/{task_id}/goal-plans', dependencies=operations)
    def goal_plan_draft(task_id: str, data: goal_planner.DraftInput, actor=Depends(operator)):
        with goal_lock:
            if engine.closed:raise HTTPException(409,'서버가 종료 중입니다.')
            try:return goal_planner.generate(store,task_id,data,engine.policy.public(),actor_id=actor['id'],allow_local=private,
                                           control=TaskControl(stop=shutdown_requested))
            except LookupError as exc:raise HTTPException(404,str(exc)) from exc
            except planning_history.PlanningConflict as exc:raise HTTPException(409,str(exc)) from exc

    @app.get('/api/tasks/{task_id}/goal-plans/{draft_id}', dependencies=auth)
    def read_goal_plan(task_id: str, draft_id: str):
        draft=store.get('goal_plans',draft_id)
        if not draft or draft.get('task_id')!=task_id:raise HTTPException(404,'목표 초안이 없습니다.')
        return draft

    @app.get('/api/tasks/{task_id}/goal-progress', dependencies=auth)
    def goal_progress(task_id: str):
        try:return goal_planner.progress(store,task_id)
        except LookupError as exc:raise HTTPException(404,str(exc)) from exc
        except planning_history.PlanningConflict as exc:raise HTTPException(409,str(exc)) from exc

    @app.post('/api/tasks/{task_id}/goal-plans/{draft_id}/accept', dependencies=operations)
    def accept_goal_plan(task_id: str, draft_id: str, data: NextPlanInput):
        with engine.lock, store.lock:
            if engine.closed:raise HTTPException(409,'서버가 종료 중입니다.')
            draft=store.get('goal_plans',draft_id)
            if not draft or draft.get('task_id')!=task_id:raise HTTPException(404,'목표 초안이 없습니다.')
            if draft.get('state')!='ready' or draft.get('fingerprint')!=data.fingerprint:
                raise HTTPException(409,'검토한 목표 초안과 반영 요청이 일치하지 않습니다.')
            if draft.get('accepted_task_id'):
                existing=store.get('tasks',draft['accepted_task_id'])
                if not existing:raise HTTPException(409,'반영된 목표 계획의 저장 상태를 확인하세요.')
                return existing
            try:
                ids, checks=goal_planner.validate(draft['decomposition'],[a['id'] for a in draft['basis']['assets']])
                if goal_planner.fingerprint(draft)!=draft['fingerprint']:
                    raise planning_history.PlanningConflict('목표 초안 지문이 일치하지 않습니다.')
            except planning_history.PlanningConflict as exc:raise HTTPException(409,str(exc)) from exc
            source=store.get('tasks',task_id)
            if not source:raise HTTPException(409,'출처 작업이 없습니다.')
            planned=TaskInput(name=('목표 계획 · '+source['name'])[:120],goal=draft['goal'],asset_ids=ids,checks=checks,
                workers=source.get('workers',3),planner='rules',worker_dependencies=draft['decomposition']['worker_dependencies'])
            return create_task_locked(planned,goal_draft=draft)

    @app.post('/api/tasks/{task_id}/observation-plan', dependencies=operations)
    def select_observation_plan(task_id: str, selection: observation_execution.Selection):
        with engine.lock, store.lock:
            if engine.closed:raise HTTPException(409, '서버가 종료 중입니다.')
            planned_id = observation_execution.digest({'source':task_id, 'request':selection.request_id})[:32]
            existing = store.get('tasks', planned_id)
            if existing:
                if existing.get('observation_selection') != selection.model_dump():
                    raise HTTPException(409, '같은 요청 ID로 다른 선택을 반영할 수 없습니다.')
                return existing
            try:
                context, execution = observation_execution.prepare(store, task_id, selection)
                source = store.get('tasks', task_id)
            except LookupError as exc:raise HTTPException(404, str(exc)) from exc
            except planning_history.PlanningConflict as exc:raise HTTPException(409, str(exc)) from exc
            data = TaskInput(name=('관찰 응답 검증 · '+source['name'])[:120], goal=source.get('goal', ''),
                asset_ids=list(dict.fromkeys(row['asset_id'] for row in execution['targets'])),
                checks=selection.checks, workers=source.get('workers', 3), planner=source.get('planner', 'rules'))
            result = create_task_locked(data, observation_request=(task_id, selection), planned_id=planned_id)
            return result

    @app.get('/api/tasks/{task_id}/planner', dependencies=auth)
    def automatic_plan_review(task_id: str):
        try:return event_planner.review(task_id)
        except LookupError as exc:raise HTTPException(404,str(exc)) from exc

    @app.post('/api/tasks/{task_id}/next-plan', dependencies=operations)
    def accept_next_plan(task_id: str, data: NextPlanInput):
        with engine.lock, store.lock:
            if engine.closed:
                raise HTTPException(409, '서버가 종료 중입니다.')
            original = store.get('tasks', task_id)
            if not original:raise HTTPException(404, '작업이 없습니다.')
            if original.get('id') != task_id:
                raise HTTPException(409, '저장 키와 작업 ID가 일치하지 않습니다.')
            try:existing, kind = planning_history.continuation(store, original)
            except (planning_history.PlanningConflict, LookupError) as exc:raise HTTPException(409, str(exc)) from exc
            if existing:
                if kind != 'followup' or original.get('next_plan_fingerprint') != data.fingerprint:
                    raise HTTPException(409, '이미 연결된 계획과 제안이 일치하지 않습니다.')
                return existing
            try:proposal = next_plan.propose(store, task_id, engine.policy.public())
            except next_plan.NextPlanConflict as exc:raise HTTPException(409, str(exc)) from exc
            if not proposal['available']:
                raise HTTPException(409, '제안할 다음 계획이 없거나 회차 한도에 도달했습니다.')
            if not hmac.compare_digest(proposal['fingerprint'], data.fingerprint):
                raise HTTPException(409, '결과·자산·실행 정책이 변경되었습니다. 다음 계획을 다시 확인하세요.')
            return create_task_locked(TaskInput(**proposal['task']), followup=(original, proposal))

    @app.post('/api/tasks/{task_id}/replan', dependencies=operations)
    def replan_task(task_id: str):
        # Same lock order as approval: serialize replacement against engine.start.
        with engine.lock, store.lock:
            if engine.closed:
                raise HTTPException(409, '서버가 종료 중입니다. 다시 시작한 뒤 계획을 만드세요.')
            original = store.get('tasks', task_id)
            if not original:
                raise HTTPException(404, '작업이 없습니다.')
            if original.get('id') != task_id:
                raise HTTPException(409, '저장 키와 작업 ID가 일치하지 않습니다.')
            if original.get('replaced_by'):
                try:return planning_history.resolve(store, task_id)
                except (planning_history.PlanningConflict, LookupError) as exc:raise HTTPException(409, str(exc)) from exc
            if original['status'] != 'pending':
                raise HTTPException(409, '승인 대기 계획만 현재 범위로 다시 만들 수 있습니다.')
            data = TaskInput(**{**original, 'name': ('새 계획 · ' + original['name'])[:120]})
            return create_task_locked(data, retest_of=original.get('retest_of'),
                                      schedule_id=original.get('schedule_id'), replacing=original)

    @app.get('/api/runtime', dependencies=auth)
    def runtime():
        return {**engine.metrics(), 'exports':exports.metrics(), 'authentication':login_gate.metrics(),
                'event_planner':event_planner.metrics()}

    @app.post('/api/audit/verify', dependencies=admins)
    def verify_audit(data: AuditReviewInput):
        try:
            result = audit_review.run(data.checkpoint.model_dump() if data.checkpoint else None)
        except AuditReviewBusy:
            raise HTTPException(429, '다른 감사 검증이 진행 중입니다. 완료 후 다시 시도하세요.',
                                headers={'Retry-After': '5', 'Cache-Control': 'no-store'})
        return JSONResponse(result, headers={'Cache-Control': 'no-store'})

    @app.post('/api/tasks/{task_id}/stop', dependencies=operations)
    def stop(task_id: str):
        if not store.get('tasks', task_id):
            raise HTTPException(404, '작업이 없습니다.')
        return engine.stop(task_id)

    @app.get('/api/tasks/{task_id}/messages', dependencies=auth)
    def messages(task_id: str, response: Response):
        if not store.get('tasks', task_id):
            raise HTTPException(404, '작업이 없습니다.')
        return list(reversed(legacy_page(response, 'messages', filters={'task_id':task_id})))

    @app.get('/api/tasks/{task_id}/messages/page', dependencies=auth)
    def message_page(task_id: str, limit: int = Query(25, ge=1, le=100),
                     offset: int = Query(0, ge=0, le=10_000_000),
                     snapshot: int | None = Query(None, ge=0, le=9_223_372_036_854_775_807),
                     search: str = Query('', max_length=200)):
        if not store.get('tasks', task_id):
            raise HTTPException(404, '작업이 없습니다.')
        return store.page('messages', limit=limit, offset=offset, snapshot=snapshot, search=search,
                          filters={'task_id':task_id})

    @app.post('/api/tasks/{task_id}/messages', dependencies=operations)
    def ask(task_id: str, data: MessageInput, request: Request, actor=Depends(operator)):
        digest = hashlib.sha256(json.dumps([actor['id'], task_id, data.request_id],
                                          separators=(',', ':')).encode()).hexdigest() if data.request_id else None
        if digest:
            original=store.get('messages','question-'+digest)
            if original:
                if original['content']!=data.content or original.get('mode','rules')!=data.mode:
                    raise HTTPException(409,'같은 전송 ID에 다른 질문이나 답변 방식을 사용할 수 없습니다.')
                return store.get('messages','reply-'+digest)
        if data.mode=='ai' and not conversation_ai.configured():
            raise HTTPException(409,'AI 대화가 서버에 설정되지 않았습니다. 규칙 기반 요약을 사용하세요.')
        summary = summarize_task(store, task_id, data.content)
        if summary is None:
            raise HTTPException(404, '작업이 없습니다.')
        if data.mode=='ai':
            if not chat_lock.acquire(blocking=False):
                raise HTTPException(429,'다른 AI 대화가 진행 중입니다. 잠시 후 같은 전송 ID로 다시 시도하세요.',
                                    headers={'Retry-After':'2'})
            call_id=None
            try:
                # A completed concurrent request may now be replayed without another call.
                original=store.get('messages','question-'+digest)
                if original:
                    if original['content']!=data.content or original.get('mode','rules')!=data.mode:
                        raise HTTPException(409,'전송 ID의 질문이나 답변 방식이 다릅니다.')
                    return store.get('messages','reply-'+digest)
                try:
                    summary=conversation_ai.draft(summary,data.content,store=store,task_id=task_id,actor_id=actor['id'],allow_local=private,
                                                  control=TaskControl(stop=shutdown_requested))
                except ValueError as exc:
                    raise HTTPException(413,str(exc)) from exc
                call_id=summary['assistant_generation']['call_id']
                # Keep the admission lock until the atomic pair/audit commit below.
                with auth_lock, store.lock:
                    fresh=operator(authenticated(request))
                    if fresh['id']!=actor['id'] or shutdown_requested.is_set():
                        raise HTTPException(409,'세션 또는 서버 상태가 변경되었습니다.')
                    timestamp=now()
                    try:
                        return store.put_message_exchange(
                            {'id':'question-'+digest,'task_id':task_id,'role':'user','content':data.content,
                             'mode':data.mode,'created_at':timestamp},
                            {'id':'reply-'+digest,'task_id':task_id,'role':'assistant',**summary,'created_at':timestamp})
                    except MessageRequestConflict:
                        raise HTTPException(409,'전송 ID의 질문이나 답변 방식이 다릅니다.')
            except BaseException:
                try:
                    call_ledger.abandon(store,call_id)
                except Exception:
                    pass  # The durable observation remains visible for startup recovery.
                raise
            finally:
                chat_lock.release()
        timestamp = now()
        question = {'id':identifier(), 'task_id':task_id, 'role':'user', 'content':data.content, 'mode':data.mode, 'created_at':timestamp}
        reply = {'id':identifier(), 'task_id':task_id, 'role':'assistant', **summary, 'created_at':timestamp}
        if data.request_id:
            # Separate namespaces from legacy random IDs; the token is scoped to actor/task.
            question['id'] = 'question-' + digest
            reply['id'] = 'reply-' + digest
            try:
                return store.put_message_exchange(question, reply)
            except MessageRequestConflict:
                raise HTTPException(409, '같은 전송 ID에 다른 질문을 사용할 수 없습니다.')
        store.put_many([('messages',question),('messages',reply)])
        return reply

    @app.get('/api/findings', dependencies=auth)
    def findings(response: Response):
        return legacy_page(response, 'findings')

    @app.get('/api/assignees', dependencies=auth)
    def assignees(search: str = Query('', max_length=100), limit: int = Query(25, ge=1, le=100),
                  offset: int = Query(0, ge=0, le=10_000_000)):
        return queries.assignees(search,limit,offset)

    @app.get('/api/findings/{finding_id}/history', dependencies=auth)
    def finding_history(finding_id: str, limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0, le=10_000_000),
                        snapshot: int | None = Query(None, ge=0, le=9_223_372_036_854_775_807),
                        search: str = Query('', max_length=200)):
        if not store.get('findings', finding_id):
            raise HTTPException(404, '발견 사항이 없습니다.')
        return store.page('finding_history', limit=limit, offset=offset, snapshot=snapshot, search=search, filters={'finding_id': finding_id})

    @app.get('/api/findings/{finding_id}', dependencies=auth)
    def finding_detail(finding_id: str):
        finding = store.get('findings', finding_id, compact_findings=True)
        if not finding:
            raise HTTPException(404, '발견 사항이 없습니다.')
        evidence = store.page('evidence', filters={'finding_id': finding_id})
        retests = store.page('retests', filters={'finding_id': finding_id})
        return {'finding': finding, 'evidence': evidence['items'], 'retests': retests['items'],
                'evidence_page': {key: value for key, value in evidence.items() if key != 'items'},
                'retests_page': {key: value for key, value in retests.items() if key != 'items'}}

    @app.get('/api/findings/{finding_id}/{collection}', dependencies=auth)
    def finding_collection(finding_id: str, collection: Literal['evidence', 'retests'],
                           limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0, le=10_000_000),
                           snapshot: int | None = Query(None, ge=0, le=9_223_372_036_854_775_807),
                           search: str = Query('', max_length=200)):
        if not store.get('findings', finding_id):
            raise HTTPException(404, '발견 사항이 없습니다.')
        return store.page(collection, limit=limit, offset=offset, snapshot=snapshot, search=search,
                          filters={'finding_id': finding_id})

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
        return compact_finding(result)

    @app.post('/api/findings/{finding_id}/retest', dependencies=operations)
    def retest(finding_id: str):
        finding = store.get('findings', finding_id)
        if not finding:
            raise HTTPException(404, '발견 사항이 없습니다.')
        data = TaskInput(name='재검증 · ' + finding['title'], asset_ids=[finding['asset_id']],
                         checks=[finding['check']], workers=1)
        if finding.get('observation_id'):
            with engine.lock, store.lock:
                source_id = finding['observation_source_task_id']
                try:
                    context = observation_execution.preview(store, source_id)['context']
                    selection = observation_execution.Selection(fingerprint=context['fingerprint'],
                        observation_ids=[finding['observation_id']], checks=data.checks, request_id=identifier()+identifier())
                except (planning_history.PlanningConflict, LookupError, ValueError) as exc:
                    raise HTTPException(409, str(exc)) from exc
                return create_task_locked(data, retest_of=finding_id, observation_request=(source_id, selection))
        return create_task(data, retest_of=finding_id)

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
        return {'version': __version__, 'schema_version': SCHEMA_VERSION, 'storage': backend, 'lab_mode': private,
                'tool_contracts': contracts_for([item['id'] for item in CATALOG]),
                'llm_configured': bool(os.environ.get('AEGIS_LLM_API_KEY') and os.environ.get('AEGIS_LLM_MODEL')),
                'llm_model': os.environ.get('AEGIS_LLM_MODEL', ''), 'request_budget': engine.policy.request_budget, 'max_workers': 4,
                'llm_chat_configured':conversation_ai.configured(),
                'execution_policy': engine.policy.public(),
                'agents': [{'id': 'planner', 'name': 'Planner', 'role': '승인된 도구의 실행 순서를 계획', 'tools': ['catalog']},
                           {'id': 'worker', 'name': 'Worker', 'role': '범위 내 검증과 증거 수집', 'tools': list(CHECK_IDS)},
                           {'id': 'retester', 'name': 'Retester', 'role': '기존 발견 사항을 독립 작업으로 재검증', 'tools': list(CHECK_IDS)}]}

    @app.get('/api/notes', dependencies=auth)
    def notes(response: Response):
        return legacy_page(response, 'notes')

    @app.post('/api/notes', dependencies=operations)
    def add_note(data: NoteInput):
        return store.put('notes', dict(data.model_dump(), id=identifier(), created_at=now()))

    @app.delete('/api/notes/{note_id}', dependencies=operations)
    def delete_note(note_id: str):
        if not store.get('notes', note_id):
            raise HTTPException(404, '노트가 없습니다.')
        queries.delete_note(note_id)
        return {'ok': True}

    @app.get('/api/schedules', dependencies=auth)
    def schedules(response: Response):
        return legacy_page(response, 'schedules')

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
        if task_id and not store.get('tasks', task_id):
            raise HTTPException(404, '작업이 없습니다.')
        media, suffix = {'json':('application/json','json'), 'csv':('text/csv','csv'),
                         'markdown':('text/markdown','md')}[format]
        permit = exports.acquire()
        if permit is None:
            raise HTTPException(429, '보고서 다운로드가 모두 사용 중입니다. 잠시 후 다시 시도하세요.',
                                headers={'Retry-After':'5'})
        try:
            return ReportResponse(report_stream(store,format,task_id,permit), permit=permit, media_type=media,
                                  headers={'Content-Disposition':f'attachment; filename="aegis-report.{suffix}"',
                                           'Cache-Control':'no-store'})
        except BaseException:
            permit.finish('failed')
            raise

    dist = Path(os.environ.get('AEGIS_WEB_DIR', str(Path(__file__).resolve().parent.parent / 'web' / 'dist')))
    if dist.exists():
        app.mount('/assets', StaticFiles(directory=dist / 'assets'), name='web-assets')
        @app.get('/')
        def index():
            return FileResponse(dist / 'index.html')
    return app
