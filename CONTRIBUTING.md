# Contributing

Python 3.11+ and Node.js 22 are used for development.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.lock
.venv/bin/pip install --no-deps -e .
.venv/bin/python -m pytest -q
cd web
npm ci
npm test
npm run build
```

For hot reload, run `.venv/bin/python -m aegis` in the repository root and
`npm run dev` in `web/`. The Vite proxy defaults to backend port 8787.
The production UI is served by the Python backend after a frontend build.

API schema is available at `/api/openapi.json` with an authenticated administrator
session. Default `/docs`, `/redoc`, `/openapi.json` and the Swagger OAuth redirect
route are disabled for all roles. The authenticated endpoint returns the static
OpenAPI contract with no-store; it does not include workspace records or provide an
interactive Swagger UI. Custom session/role dependencies still enforce each operation;
the schema is not a grant of permission or a complete machine-readable role policy.

## CI and installed package review

The Verify workflow uses Python 3.11 and Node.js 22, locked runtime/dev dependencies,
frontend tests/build, backend tests and selected design contrast/token checks. It also
builds a wheel and rehearses it outside the checkout in a fresh virtual environment.
Run the package stage locally from the repository root after building the frontend:

```sh
.venv/bin/python scripts/check_design.py
.venv/bin/python -m pip wheel --no-deps . --wheel-dir artifacts/ci-wheel
.venv/bin/python scripts/review_runtime_package.py --wheel-dir artifacts/ci-wheel --web-dir web/dist --runtime-lock requirements.lock
.venv/bin/python scripts/review_goal_recovery.py --wheel artifacts/ci-wheel/*.whl --backend sqlite
.venv/bin/python scripts/review_goal_recovery.py --wheel artifacts/ci-wheel/*.whl --backend sqlite --crash
```

Use a wheel directory containing exactly one Open Aegis wheel. The runtime review installs
locked runtime dependencies (network access to the package index is required), checks
dependency consistency and CLI entry points, starts the installed server on an inherited
loopback socket, and exercises authentication, synthetic asset/pending-plan persistence,
separately built UI assets, runtime metrics and audit verification. It never approves a
scan or requests a target. It removes inherited AEGIS settings and Python path overrides.
Shutdown must finish the app lifespan and release the workspace lease. The existing
installed backup/restore/audit rehearsal runs afterwards. Temporary installations and
synthetic databases are removed on exit. This POSIX review supports Linux/macOS; Windows
uses WSL or a container, consistent with the workspace-lock implementation.

`review_goal_recovery.py` separately creates an owned loopback target and exercises
actual approved goal execution, pending follow-up/retest replacement, installed CLI
backup/restore and checkpoint comparison, session revocation and request replay.
Restored plans stay pending until each explicit approval; three target GETs per backend
cover the source, recovered retest and recovered goal round. The API authorization
check is skipped without policies and is not reported as successful. Completed origin
and results must survive another server restart. Use `--backend postgres` or `both`
with PostgreSQL binaries on PATH for an isolated native cluster; no external target or
AI provider is contacted. Locked package installation still requires package-index
access. Temporary servers, databases and installations are cleaned up on exit.

`--crash` additionally SIGKILLs only the owned server processes: once with pending
goal plans, once during the retest GET and once during the follow-up GET. Pending
plans and request identities must survive restart. In-flight tasks must recover as
interrupted, keep their origins and create exactly one pending retry; a new explicit
approval completes each retry. This mode makes five owned target GETs per backend
and verifies the resulting audit chain. It tests process death while the database
remains available, not a machine power loss or database-server crash. CI uses this
mode in both storage jobs.

For the native job, add `--database-crash` to `--backend postgres --crash`
(or `--backend both --crash`). This immediately stops only the temporary owned
PostgreSQL cluster after pending plans are committed, then requires startup-log
evidence of WAL recovery, an unchanged audit checkpoint, retained plans and request
identities, and no automatic target requests. The host and storage remain alive;
this does not simulate hardware power loss, storage failure or PITR.

Add `--database-crash-in-flight` with `--database-crash` to also stop the owned
database during held, explicitly approved retest and follow-up retry GETs. The
service loses its runtime ownership and must refuse reads, approvals and health
with 503 rather than reacquire automatically. After an owned service restart each
task must recover as interrupted, create exactly one pending retry and complete
only after a fresh approval. This mode makes seven owned GETs and five service
SIGKILLs on PostgreSQL (three database immediate shutdowns including the pending
phase); SQLite still makes five GETs and three service SIGKILLs. Audit checkpoints
are verified throughout. Native CI requests this mode. This exercises a held HTTP
request across database loss; a crash during a database write transaction is
separate validation.

`--database-crash-write` with `--database-crash` adds a separate owned schema and
real HTTP follow-up write rehearsal. A temporary trigger confirms that the new
child and six coverage cells are staged, then exposes a nontransactional sequence
signal and holds the parent-link insert. Immediate database shutdown must roll back
the task/coverage/goal-plan records to the exact prior snapshot and retain the
audit checkpoint. The stale service returns 503. After restart the same fingerprint
creates one unapproved pending plan; explicit approval completes it. This adds two
owned target GETs, one database shutdown and one service SIGKILL. Native CI requests
it. The fixture trigger/function/sequence are removed before recovery. This covers
one precommit point in a follow-up transaction; commit-acknowledgement ambiguity,
other write boundaries and hardware/storage failures need separate validation.

`--database-crash-audit` requires `--database-crash-write` and adds a second owned
schema with the same HTTP flow. Its audit-state trigger confirms the staged child,
six coverage cells, parent link, audit event and linked hash before signalling the
crash gate. It stops the database before the audit-state update/commit and requires
exact rollback of plan records, audit rows/state and the storage event watermark.
Before/after snapshot digests and audit sequence numbers are included in the report.
Recovery again requires one pending plan and a fresh approval. This adds two more
owned GETs, one DB shutdown and one service SIGKILL. Native CI requests this mode;
an acknowledged/ambiguous commit or hardware/storage failure is still separate.

The wheel contains the Python backend/CLI, not the frontend bundle. Its UI is supplied
explicitly via AEGIS_WEB_DIR for this review; Docker packages the separately built UI.
Build dependencies, runner images and Python/Node patch versions are not fully pinned,
so this is behavior verification rather than a byte-reproducible or signed release.
Action references use full official commit SHAs, checkout credentials are not retained,
the token is read-only; Python/native jobs have a 15-minute limit and container/Compose
jobs have a 25-minute limit. The hosted workflow still needs
an actual run on the published repository; local review does not prove a GitHub job ran.
Docker execution, whole UI accessibility/mobile coverage and release signing remain
separate gates in [V1-READINESS.md](docs/V1-READINESS.md).

With Docker Compose2.24.4+, run `python3 scripts/review_compose.py` and
`python3 scripts/review_compose.py --postgres` to rehearse the actual `compose.yml`
using temporary overrides, synthetic settings and unique projects/volumes. They
verify actual HTTP storage, retained data/cookies after container recreation,
backup/checkpoint restore and old-session rejection without approving target
execution. Native mode starts a PostgreSQL16 container and restores a new schema,
preserving the original. Both remove their owned resources; image caches may remain.
CI has both modes; local arm64 evidence does not prove hosted/amd64 execution.
Details and network/trust limits are in [OPERATIONS.md](docs/OPERATIONS.md).

## Goal UI review

`scripts/review_goal_ui.py --selective-round` seeds explicitly synthetic completed/
failed goal cells for follow-up review. Check the one-cell selection, pending
acceptance/detail and progress1/2 without approving execution. These seed records
are not real target evidence; actual sparse execution is exercised by SQLite/native
PostgreSQL tests. The goal recovery harness compares the result's declared selected
asset/check pairs, while its write/audit crash fixture requests all goal tools to
retain the existing six-cell staging gate.

After building `web/dist`, run `.venv/bin/python scripts/review_goal_ui.py` in a
terminal. The disposable loopback app prints its synthetic login and task URL.
Its local provider returns one synthetic objective; a goal containing `대기`
holds the response until you type `release` in that terminal. Use this to verify
focus preservation after moving to another control or closing the task detail.
`--unconfigured` exercises the real missing-provider error. Review draft creation,
same-request recovery, Tab to acceptance, reset to goal input and error recovery.
Stop with Ctrl+C; the fixture reports provider calls, pending task states and target
traffic, then removes its workspace. It validates UI behavior; do not treat its
synthetic plan as model-quality or executed-security evidence.

## New checks

Register a named check in `aegis/checks.py`, implement it in `run_check`, and
add behavioral tests against a loopback synthetic fixture. Use `Transport`
for every target request. Do not open a second unguarded network transport.
Preserve explicit scope, request limits, cancellation, and metadata redaction.
Report configuration observations separately from confirmed policy failures.

Include a finding that is observed before a fixture change and absent after
the change. Verify that connection errors do not falsely resolve it.
Never add real customer data, production tokens, arbitrary shell execution,
or live third-party scans to tests.

## Pull requests

Describe the user-visible behavior, reproduction, and validation. Screenshots
help for UI changes. Keep generated databases, local artifacts, credentials,
and virtual environments out of Git.

`review_goal_ui.py --objective-observations` seeds a synthetic approved goal and
completed endpoint inventory with one observation for objective-specific picker
review. Build the console first; create only a pending plan in this fixture. Do
not approve the seeded `.invalid` target. The fixture logs target traffic and
provider calls at shutdown and removes its disposable workspace.

Finish frontend builds before starting the Python regression suite: `create_app`
mounts `web/dist/assets`, and Vite temporarily removes that directory during a
rebuild. Freeze `aegis/**/*.py` during the run as package fingerprints are captured
at import; a mid-run backend edit invalidates approval/provenance checks.

`review_goal_ui.py --observation-rounds` seeds explicitly synthetic failed observed
URL results for reviewing selected follow-up cells and creating a pending child.
Never approve that fixture's `.invalid` target. `--web-dir` can point at a separate
built UI directory so visual iteration does not remove `web/dist/assets` while
Python tests are running. Shutdown records target traffic/provider calls and
removes the disposable workspace.

관찰 미완료 자동 할 일의 생성·사람 결정 보존·롤백·이전 처리 위치 재개 검증은
`tests/test_observation_todos.py`와 `tests/test_postgres_observation_todos.py`에 있습니다.
후자는 `AEGIS_TEST_POSTGRES=1`과 로컬 PostgreSQL 실행 도구가 필요하며 소유한 임시 클러스터를 사용합니다.

실제 승인 검사·재검증과 조회 부하·실행/대기 중 프로세스 장애를 함께 검수하는
명령은 [실행 부하 리허설](docs/EXECUTION-LOAD.md)을 따릅니다. 이벤트 묶음의 작업별
마지막 변경·원자 롤백·자산 페이지 경계·처리 한도는 `tests/test_event_planner_batches.py`와
`tests/test_postgres_event_planner_batches.py`에서 확인합니다.

자동 계획의 저장 위치·실제 대기 행 수·정책 재처리·손상 위치·자산 페이지 지표는
`tests/test_event_planner_metrics.py`와 `tests/test_postgres_event_planner_metrics.py`에서
검증합니다. `scripts/review_event_progress_ui.py --state current|replay|invalid`는
처리기를 멈춘 합성 UI 검수 환경이며 대상 작업을 만들거나 실행하지 않습니다.

실행 부하 리허설의30초 progress 파일은 중간 관측이며 통과 증거가 아닙니다.
완료/정리된 결과만 `scripts/summarize_execution_load.py`로 시간 구간별 요약할 수
있습니다. `--progress-log`에는 같은 실행의 stdout 파일을 지정합니다. 운영 SLO나
원인 판정은 별도 검증이며, 실행 중에는 서비스 소스를 변경하지 않습니다.
