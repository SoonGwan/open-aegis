# PostgreSQL 저장소와 전송

현재 구현은 **빈 네이티브 스키마 초기화, 오프라인 전송·되돌리기, 네이티브 Store와 선택 가능한 PostgreSQL HTTP
백엔드, 온라인 논리 백업과 새 스키마 복구**다. 기본 서버는 SQLite다. `AEGIS_POSTGRES_DSN`만 설정하면 전환되지 않으며
아래 명시적 backend/schema 설정이 필요하다. 대표 HTTP 인증·승인 실행·재검증·
보고서·가져오기·재시작과 온라인 백업→새 스키마 복구를 실제 DB에서 검수했다.
전체 운영 복구·업그레이드·오류/부하/장시간 검수는 남아 있어 전체 v1의 PostgreSQL 조건은 열린 상태다.

## 설치와 연결

`pip install 'open-aegis[postgres]'`로 선택 의존성을 설치한다. 저장소에서 재현할 때는
`requirements.lock`과 `requirements-postgres.lock`을 함께 사용한다. 현재 로컬 검수는
PostgreSQL16.15와 psycopg3.3.6이다. 서버/클라이언트 도구와 접속 계정은 별도로 준비한다.

`AEGIS_POSTGRES_DSN`에 libpq 연결 문자열 또는 URI를 설정한다. CLI 인자로 비밀번호를
전달하지 않는다. 원격 서버의 TLS/신뢰 CA/인증은 운영자가 연결 설정에 명시해야 한다.
도구는 SSL 검증 설정을 완화하지 않는다. PostgreSQL의 인증/권한을 대체하지 않는다.
연결 시간 제한5초, SQL120초, 잠금 대기5초를 적용한다. 표준 libpq 환경 설정도 영향을
줄 수 있으므로 실제 대상 DB/계정/인증 구성을 확인한다. 오류 출력에는 DSN·서버 오류
본문·비밀번호를 포함하지 않는다.

## PostgreSQL에서 처음 설치

기존 SQLite 워크스페이스 없이 시작하려면 `aegis-init-postgres`를 사용한다.
빈 DB의 별도 새 스키마에 검토된 테이블/identity/index·스키마2 저장 메타데이터·
새 감사 chain ID와 genesis를 한 트랜잭션에서 만들고 검사한다. SQLite 파일을
생성하지 않으며 사용자·세션·대상 요청·서버 시작도 만들지 않는다.

```sh
# 접속/TLS 비밀 설정은 AEGIS_POSTGRES_DSN으로 별도 제공한다.
export AEGIS_STORAGE_BACKEND=postgres
export AEGIS_POSTGRES_SCHEMA=aegis_workspace
aegis-init-postgres --schema aegis_workspace
python -m aegis
```

`--schema`를 생략하면 `AEGIS_POSTGRES_SCHEMA`를 사용한다. 선택 의존성 설치가
필요하다. 설치된 CLI는 `.env`를 자동으로 읽지 않으므로 환경변수를 직접 제공한다.
저장소의 `start.sh`는 기존처럼 `.env`를 읽는 서버 진입점을 사용한다. 저장소에서
PostgreSQL로 실행할 때는 `.venv`에 `requirements-postgres.lock`도 먼저 설치한다.
초기화 명령은 실제 운영 DB·역할·TLS 설정을 바꾸거나 자동 provisioning하지 않는다.

스키마 이름은 전송/복구와 같은 제한·식별자 인용을 적용한다. 기존 스키마는 빈
스키마여도 거절하며 삭제/수정하지 않는다. 같은 runtime key의 독점 transaction
admission을 먼저 확인해 실행 소유자/진행 중 보호 작업/다른 초기화와 겹치지 않는다.
동시 초기화는 하나만 성공한다. DDL·감사/행 검증의 커밋 전 실패는 스키마/테이블/
순번 할당기를 함께 롤백한다. 커밋 응답 유실은 불확실할 수 있으므로 먼저 실제
스키마를 확인하고 재시도한다. 잘못된 연결·권한·이름은 종료 코드2이며 DSN/서버
오류 본문을 출력하지 않는다. 초기화는 기존 저장소 업그레이드/마이그레이션 명령이 아니다.

초기화 계정에는 대상 DB의 CONNECT와 CREATE 권한이 필요하다. SUPERUSER·
CREATEDB·CREATEROLE은 필요하지 않으며 생성 스키마와 테이블은 그 계정이 소유한다.
초기화 후 DB CREATE를 회수한 같은 일반 계정으로 HTTP 최초 설정·로그인·노트·
감사 검증을 실제 DB에서 확인했다. 별도 실행 역할의 GRANT/권한 분리·서버 인증과
계정 운영은 관리자가 준비해야 한다. 명령이 역할을 생성하거나 권한을 부여하지 않는다.

서버 시작 후 기존 최초 관리자 설정 화면에서 계정을 만든다. `AEGIS_SETUP_TOKEN`을
설정하면 loopback 접속도 올바른 토큰이 필요하고, 토큰 없는 원격 최초 설정은
거절한다. 초기화 CLI는 관리자 비밀번호를 받거나 계정을 자동 생성하지 않는다.
생성 후 설정 API는409, 익명 보호 API는401이다. 정상 재시작의 로그인과 승인 대기
계획은 유지하며 계획은 자동 실행하지 않는다.

## HTTP 서버 선택

먼저 위 초기화 CLI로 빈 스키마를 만들거나 아래 전송 CLI로 기존 SQLite를 이전한다.
서버 시작은 기존 지원 형식의 스키마를
읽으며 임의 스키마 생성/SQL 마이그레이션을 수행하지 않는다. 다음 값으로 실행한다.
DSN에는 실제 접속 계정과 TLS 정책을 환경변수/운영 비밀 관리로 설정한다.

```sh
export AEGIS_STORAGE_BACKEND=postgres
export AEGIS_POSTGRES_SCHEMA=aegis_workspace
python -m aegis
```

`AEGIS_POSTGRES_DSN`과 선택 의존성도 필요하다. 잘못된 backend/schema/형식/접속
설정은 시작을 거절하며 SQLite로 대체하지 않는다. PostgreSQL 모드에서
`AEGIS_DATA_DIR`에 SQLite 파일이나 로컬 워크스페이스 임대를 만들지 않는다. DB/스키마
실행 소유권을 Engine이 획득한 다음 호출/작업 복구를 수행한다. 같은 스키마의 중복
서버는 복구 전에 거절된다. 종료는 scheduler와 Engine을 닫고 실행 소유권을 해제한다.
기존 PostgreSQL 로그인 세션은 정상 재시작 때 유지한다. 미완료 작업/호출은 결과를
추정하지 않고 중단/사용량 미확인 상태로 복구한다. 익명 API는401, 권한 위반은403,
기존 사용자명 충돌은409다. 저장소 오류/확인된 소유권 상실은 본문을 숨긴503이며
캐시를 금지한다. 대화 요약도 같은 네이티브 읽기 스냅샷을 사용한다.

설정 API의 `storage`는 실제 선택을 반환한다. 관리자 초기 설정은 초기화/전송으로
준비한 빈 스키마에서도 기존 설치 토큰/로컬 설치 정책을 따른다. HTTP startup/config 실패의
연결/스키마 오류는 원문 DSN을 출력하지 않는다. 종료 중 작업/긴 SQL/원격 접속 장애와
scheduler의 전체 운영 SLO는 아래 남은 검수에 포함한다. backup/restore CLI는 아래
명시적 backend 선택으로 네이티브 논리 백업/새 스키마 복구를 지원한다.
감사 CLI와 읽기 전용 MCP는 아래 명시적 저장소 선택을 지원한다.

## SQLite → PostgreSQL

```sh
aegis-transfer-storage sqlite-to-postgres --source data/aegis.db --schema aegis_workspace
```

서비스를 종료한 뒤 실행한다. 소스 워크스페이스 임대를 획득하며, 사용 중인 서버와
queued/running/stopping 작업이 있으면 거절한다. SQLite 스키마2만 지원하므로 이전
스키마는 기존 업그레이드·백업 절차를 먼저 적용한다. 원본은 읽기 전용으로 열고
기존 백업 무결성/참조/JSON 검증, 같은 읽기 트랜잭션의 감사 연결·엄격한 JSON 읽기를
수행한다. 다른 비협조 프로세스의 직접 DB 쓰기를 임대만으로 통제하지는 못한다.

별도의 **새 PostgreSQL 스키마**만 만든다. 기존 스키마·테이블은 덮어쓰거나 삭제하지
않는다. 이름은 소문자 영문으로 시작하는63자 이하 영문/숫자/밑줄이며 public,
information_schema, pg_* 이름은 거절한다. SQL 식별자를 인용해 예약어도 안전하게
처리한다. DDL·COPY·검증을 하나의 트랜잭션에서 수행한다. 커밋 전 실패는 새 스키마와
데이터를 함께 롤백한다. 커밋 응답 중 연결이 끊기면 완료 여부가 불확실할 수 있으므로
해당 스키마를 먼저 확인한다. 같은 이름 재시도는 기존 스키마를 거절하며 덮어쓰지 않는다.

원문 JSON·감사 detail은 TEXT로 보존하며 JSONB 재직렬화로 내용을 바꾸지 않는다.
SQLite 기록 rowid, 사용자/자격 증명 해시, 이벤트 seq/시간, 감사 연결/기준을 보존한다.
테이블별 순서가 고정된 길이 구분 행 SHA256와 감사 체크포인트가 일치해야 완료된다.
사용자 ID 정렬은 PostgreSQL C collation을 사용한다. COPY와 서버 측 커서는 클라이언트에
전체 이력을 한꺼번에 쌓지 않는다. 단일 행 크기와 장시간 최대 부하는 아직 검증 중이다.

이벤트 AUTOINCREMENT 기준도 저장한다. 삭제된 후에도 이전 seq를 재사용하지 않도록
되돌릴 때 기준을 복원한다. PostgreSQL의 신규 rowid/seq 시퀀스는 이전 최대값 이후로
설정한다. PostgreSQL TEXT가 표현할 수 없는 NUL 등은 제거/치환하지 않고 전송을
실패시킨다. 로그인 세션은 대상에 복사하지 않는다. 결과의 sessions_revoked는 대상에서
제외한 원본 세션 수다. **원본 SQLite 세션은 유지된다.**

## PostgreSQL → 새 SQLite

```sh
aegis-transfer-storage postgres-to-sqlite --schema aegis_workspace --output returned/aegis.db
```

위 전송 형식 `aegis-postgres-storage-v1`의 스키마를 일관된 REPEATABLE READ/READ ONLY
트랜잭션으로 읽는다. 예상 테이블 구성·형식·순서 기준·감사 연결을 검사한다.
뷰/외부 테이블/추가 테이블은 거절한다. 같은 DB/스키마의 exclusive runtime gate를
획득해야 하므로 실행 소유자나 보호된 작업이 있으면 반환을 거절한다.
중지한 스키마에 세션이 남아 있어도 반환할 수 있다. 세션은 반환본에 복사하지 않고
`omitted_session_count`에 제외한 행 수를 기록한다. `sessions_revoked=true`는 반환본의
세션이 비어 있음을 뜻하며 원본 세션을 삭제하는 명령이 아니다.
`source_sessions_preserved=true`: 원본 PostgreSQL 세션은 기존 만료/폐기 규칙을 유지한다.

새 SQLite 파일을 같은 출력 디렉터리의0600 임시 파일에 만들고, 행 해시·감사·SQLite
무결성 검증과 PostgreSQL 읽기 트랜잭션/연결 종료를 마친 후 공개한다. 기존 출력 파일/심볼릭 링크는 덮어쓰지 않는다.
hard-link 공개로 마지막 단계의 다른 생성자도 덮어쓰지 않는다. 해당 파일시스템의
hard-link/fsync 지원이 필요하다. 실패한 임시 파일은 제거한다. 기존 서비스 DB를
교체하는 명령이 아니며, 검증된 반환 DB의 운영 적용은 기존 복구 절차를 따른다.
반환본에서는 기존 로그인 세션이 만료되고, 저장된 계정/비밀번호로 다시 로그인한다.

## PostgreSQL 백업 검수와 남은 일

`pg_dump --format=custom --schema ...`와 `pg_restore --exit-on-error --dbname ...`로
별도의 빈 검수 DB에 복원한 뒤 위 되돌리기 명령으로 같은 행/감사 증거를 검사했다.
이는 전체 PostgreSQL 인스턴스의 역할·접속 권한·외부 객체·WAL/PITR 복구 보장이 아니다.
덤프와 반환 SQLite에는 비밀번호 해시와 관찰 데이터가 있으므로 접근을 제한한다.

실제 검수 명령:

```sh
AEGIS_TEST_POSTGRES=1 python -m pytest -q tests/test_postgres_transfer.py
python scripts/review_postgres_transfer.py --wheel-dir artifacts/postgres-transfer-wheel
```

검수는0700 임시 디렉터리의 소유한 PostgreSQL 클러스터를 UNIX socket으로만 연다.
임시 trust 인증은 그 리허설에 한정하며 운영 설치 설정이 아니다. 검수 서버의 기본 fsync 설정은 유지하며, 장애 중 디스크 유실/PITR을 검증한 것은 아니다.
종료 후 클러스터,
설치 환경, 복구 파일은 정리한다. CI에 선택 의존성/실제 클러스터 검사를 추가했으나
GitHub hosted 실행 결과는 아직 없다.

남은 v1 조건은 전체 HTTP/권한/동시성/재시작/부하 검수와 스키마 업그레이드,
라이브 백업/복구의 운영 계약이다.
현재 전송 형식은 그 기반이며, 이를 PostgreSQL 서비스 지원 완료로 표시하지 않는다.

## 읽기 전용 MCP와 감사 CLI

MCP stdio 서버는 HTTP와 같은 `AEGIS_STORAGE_BACKEND`/`AEGIS_POSTGRES_DSN`/
`AEGIS_POSTGRES_SCHEMA` 선택을 사용한다. PostgreSQL은 준비된 지원 스키마를 읽고
잘못된 설정/접속을 SQLite 파일로 대체하지 않는다. 도구7개의 이름·입력 한도·반환
계약은 [MCP.md](MCP.md)와 같다. 각 tool call은 한 read-only REPEATABLE READ
트랜잭션에서 작업·커버리지·발견·출처 확인된 증거·재검증·이벤트를 읽는다.
페이지의 삽입 watermark는 별도 호출 사이의 편집을 복원하는 기능이 아니다.
MCP는 Engine·작업 복구·스키마 수정·실행/승인을 시작하지 않는다. 오류는 고정 도구
오류 또는 원문 DB 정보를 포함하지 않는 시작 오류로 반환한다.

감사 CLI도 같은 backend 선택을 기본값으로 사용한다. 명시적으로 선택할 수도 있다.

```sh
aegis-verify-audit --backend postgres --schema aegis_workspace --output checkpoint.json
aegis-verify-audit --backend postgres --schema aegis_workspace --checkpoint checkpoint.json
```

DSN은 환경변수로만 전달한다. PostgreSQL 모드의 `--source` 파일 지정은 거절한다.
SQLite 선택은 기존 `--source` 또는 `AEGIS_DATA_DIR/aegis.db`를 읽는다. 지원하는
읽기 snapshot의 전체 감사 연결을 서버 커서로 검증하고, 검증 성공 후에만0600 새
체크포인트를 생성한다. 기존 파일은 덮어쓰지 않는다. 실패는 종료 코드2이며 비밀번호/
서버 오류 본문을 출력하지 않는다. CLI는 관리자 UI의10초 전체 제한과 별도이며
기존 연결/SQL 시간 제한을 사용한다.

SELECT 전용 DB 계정의 schema USAGE와 records/events/event_hashes/audit_state/
storage_metadata 읽기 권한으로 도구·감사 조회를 검수했다. users/sessions의 SELECT나
쓰기 권한은 필요하지 않다. 실제 테스트에서 쓰기·users 읽기가 거절됐고 읽기 전용
트랜잭션을 유지했다. 계정의 DB 접속/SSL/권한 부여는 운영자가 관리하며, MCP 설정의
DSN은 연결 클라이언트에 노출될 수 있으므로 비밀 관리 설정을 사용한다. 외부 MCP
클라이언트와 모델에는 조회한 증거가 전달될 수 있다. 원격 HTTP/SSE MCP 클라이언트나
외부 체크포인트 자동 수집을 구현한 것은 아니다.

## 네이티브 Store 계층

`aegis.postgres_store.PostgresStore(dsn, schema)`는 초기화/전송/복구한 지원 형식의 스키마를
직접 읽고 쓴다. SQLite SQL 변환이나 SQLite 복제 DB를 사용하지 않는다. 생성자는
형식/감사 기준을 읽기만 하며 세션 폐기·작업 복구·스키마 변경을 하지 않는다.
HTTP 서비스는 명시적 backend/schema 설정으로 이 Store를 선택한다.
Engine의 큐 지표/기한 조회와 발견 관찰·조치·재검증은 저장소별 쿼리와 쓰기 트랜잭션을
사용한다. 소유한 단독 검수 환경에서 네이티브 PostgreSQL Engine의 승인→로컬 요청→
증거/커버리지 저장, 재검증 해결 판정, 실행 중 중지·큐 만료·시작 복구를 검수했다.
단독 Engine 검수에 더해 HTTP 승인 실행·재검증도 검수했다. 아래 실행 소유권 계약은
Engine과 요청 경계에 연결되어 있으며, 전체 운영/장애/장시간 검수가 남아 있다.

발견 관찰·조치·재검증은 같은 쓰기 트랜잭션에서 현재 발견/담당자를 읽고 관련 증거,
변경 이력과 함께 저장한다. PostgreSQL과 SQLite의 서로 다른 Store 인스턴스에서
동시에 같은 발견을 관찰해도 증거 참조를 잃지 않고, 같은 expected revision으로
조치하면 한 변경만 성공한다. 배치 쓰기 뒤 오류를 주입해 관련 기록의 롤백도 검수했다.

각 읽기는 REPEATABLE READ/READ ONLY 트랜잭션이고 쓰기는 READ COMMITTED 트랜잭션에서
DB/스키마별 트랜잭션 advisory lock을 잡는다. 여러 Store 인스턴스의 감사 기록을 실제
서버에서 동시에 쓰고 전체 연결을 검증했다. 이 잠금은 같은 계약을 따르는 쓰기만
직렬화하며 외부 SQL 관리자의 수정을 막는 권한 장치가 아니다. 스키마 전체 쓰기가
직렬화되는 초기 구현으로, 다중 서버 처리량·긴 쓰기·장기 부하 SLO는 아직 검수하지 않았다.
연결 풀과 PostgreSQL 전용 검색 인덱스도 아직 없다.

저장/갱신·페이지/문자열 검색·관계 증거 필터·revision별 커버리지·예약/복구 목록,
계정/해시 세션·권한 변경 시 세션 폐기, 감사 이벤트/체크포인트 검증을 구현했다.
AI 결과의 기존 observed 호출 연결·결과 레코드·감사 기록은 같은 쓰기 트랜잭션에서
커밋한다. 쓰기 실패를 주입해 모두 함께 롤백되는 것을 검수했다. 제공자 호출 시작/
관찰/포기/복구의 ledger 모듈도 PostgreSQL 트랜잭션을 사용한다. 복구는 100개씩
처리하며 실패한 배치만 롤백하고 다시 호출해도 완료한 기록을 덮어쓰지 않는다.
복구 호출자는 서비스의 독점 시작 권한을 가져야 한다. PostgreSQL Engine은 아래
소유권을 획득한 뒤 독립 호출 이력과 미완료 작업을 복구한다. HTTP 서버도 같은 Engine 복구 경로를 사용한다.

사용량·비용 요약은 같은 읽기 스냅샷에서 필요한 메타데이터만 서버 커서로 200개씩
받는다. 전체 작업/메시지나 개인 질문/답변을 읽어 목록으로 만들지 않는다. 토큰 합계는
정수로, 견적은 기존 호출 시점 가격의 검증·통화별 정수 단위 합산으로 계산한다.
단일 aggregate 응답을 반환하지만 서버→클라이언트의 메타데이터 전송은 호출 수에
비례한다. 이 초기 경로의 대규모 집계 성능과 개별 메타데이터의 자원 한도는 미검수다.
실제 로컬 모형 제공자→PostgreSQL 시작 기록→응답 관찰→답변 원자 저장을 검수했다.
사용량 조회 중 별도 DB 쓰기가 일어나도 토큰·비용은 같은 스냅샷의 값으로 집계했다.

관계 그래프는 SQLite와 PostgreSQL의 명시적 질의를 사용한다. 같은 read transaction에서
자산/작업/선택 자산의 커버리지와 발견·증거·관찰 링크를 읽는다. 발견 최대25개,
발견별 증거2개, 관찰 링크10개의 기존 한도를 유지한다. 참조 배열 전체를 반환하지
않고 SQL로 유효/누락/잘못된 참조를 계산한다. 다른 자산·검사·지문의 증거를 연결하지
않고 다른 작업의 증거는 현재 작업의 증거 엣지로 표시하지 않는다. 1만 개 누락 참조와
동시 증거 소속 변경, 500개 다른 자산이 있는 계획의 선택 자산만 조회하는 것을 검수했다.
이는 정상 필드 모양의 대표 자료에 대한 검수이며 단일 증거 본문의 전체 크기나 대규모
Graph SLO를 보장하지 않는다. 그래프는 조회이며 추가 대상 요청을 보내지 않는다.

보고서의 JSON·CSV·Markdown은 같은 생성기를 쓰고 PostgreSQL에서는 명시적
네이티브 질의와 서버 측 커서(batch32)로 전체 행을 읽는다. 작업·발견·증거·조치
이력·커버리지·트래픽을 한 read-only REPEATABLE READ 스냅샷에서 읽고, 첫 전송
전에 스냅샷을 고정한다. 선택한 작업의 참조만 포함하고 고아 증거/트래픽은 제외한다.
커버리지의 추가 조회도 같은 연결을 사용한다. CSV 수식 시작 문자 보호를 유지한다.
6,000개씩의 발견·증거·이력·트래픽을 JSON으로 내보내는 로컬 검수에서 Python peak
memory2MB 미만을 확인했다. DB 서버의 실행 계획/정렬 메모리, 단일 대형 레코드의
파싱/출력 자원이나 장시간 snapshot의 vacuum 영향까지 보장하는 검수는 아니다.

기존 ExportPermit의 승인 슬롯과 총 다운로드 시간 제한을 사용한다. PostgreSQL
트랜잭션 내부에는 남은 시간으로 statement_timeout을 설정하고 취소 감시 스레드가
시간 초과/다운로드 중단 때 현재 DB 쿼리의 cancel_safe를 요청한다. 쿼리 전/행 처리
시에도 permit을 확인한다. 실제 pg_sleep 중 취소·ASGI 전송 대기 timeout·조기 close에서
커서/연결/감시 스레드/승인 슬롯 해제를 검수했다. 감시를 시작하기 전 연결 수립에는
기존5초 connect_timeout이 적용된다. libpq17 이전 cancel_safe fallback, 원격 네트워크
blackhole·프록시·HA 환경의 전체 종료 시간은 미검수다. 활성 보고서의 공유 transaction
gate는 소유 세션을 종료해도 반환/교체를 막고, 보고서를 닫은 다음 교체할 수 있다.
조회는 대상에 추가 HTTP 요청을 보내지 않는다. HTTP 앱은 이 저장소 중립 보고서
경로를 호출하며 PostgreSQL backend 선택에서도 같은 보고서를 사용한다.

관리자 감사 검증의 `AuditReview`는 저장소를 받아 SQLite 또는 네이티브 PostgreSQL의
읽기 전용 경로를 사용한다. PostgreSQL 검증은 같은 read-only REPEATABLE READ
트랜잭션에서 감사 기준·전체 해시 연결·고아 연결 여부와 선택 외부 체크포인트를
검사하고, 서버 측 커서(batch32)로 감사 행을 읽는다. 이벤트 원문이나 비밀 정보를
응답에 포함하지 않으며 기준/연결/이벤트를 복구하거나 새 검증 이벤트를 쓰지 않는다.
단일 검증 슬롯을 사용하고 초과 요청은 기존 busy 계약으로 거절한다.

남은 시간으로 statement_timeout을 설정하고 기존 DB 취소 감시를 사용한다. SQL/행
처리/결과 반환 전 시간 제한을 확인한다. 불일치는 `mismatch`, 시간 초과·읽기 오류·
실행 소유권 상실은 `inconclusive`이며 DB 오류 메시지를 응답에 노출하지 않는다.
10,000개의2KB 상세 기록을 검수한 Python peak memory는2MB 미만이었다. 실제
pg_sleep 중 취소와 다음 검증 재시도, 동시 감사 추가의 스냅샷 일관성, readonly 쓰기
거절, 소유 backend 종료 시 진행 중 검증이 교체를 막고 이후 검증이 거절되는 것을
확인했다. 모든 확인은 소유한 로컬 DB에서 수행했다. 원격 접속/취소 지연·서버 메모리·
단일 대형 이벤트·외부 체크포인트 수집 자동화의 전체 운영 검증을 뜻하지 않는다.
검증 응답 자체는 서명/승인 증명이 아니며 신뢰할 외부 체크포인트 보관은 별도다.
HTTP 앱의 관리자 감사 경로는 이 저장소 중립 검증기를 사용하나 PostgreSQL HTTP
서비스 선택은 구현했고 전체 인증/운영 조합의 검수는 아직 남아 있다. 감사 CLI도 명시적 PostgreSQL 선택을 지원한다.

ScopeSentry의 파일/설정된 원본 조회 미리보기와 선택 반영도 네이티브 PostgreSQL
트랜잭션을 사용한다. 저장소별 명시적 질의로 자산 URL 최대2개/출처/미리보기를
읽고, 전체 선택의 예상 자산/출처 digest와 상태를 확인한 뒤 생성·출처 변경 이력·
현재 출처·적용 결과·감사 연결을 한 쓰기 트랜잭션에서 저장한다. 신규 자산/미리보기/
이력은 strict INSERT이며 기존 자산을 덮어쓰지 않는다. 원본 URL 변경 시 새 범위를
만들고 기존 자산·검토 중 작업을 유지한다. 반영은 자산 등록이며 실행을 시작하지 않는다.
같은 미리보기의 같은 선택 재시도는 원래 결과를 반환하며 변경된 선택은 거절한다.

미리보기 만료 정리와50개 입장 제한도 쓰기 트랜잭션에서 직렬화한다. 서로 다른 Store
인스턴스의 동시 적용/입장과 경쟁하는 미리보기, 중간 감사 INSERT 실패의 전체
롤백, 원본 다음 페이지 포인터/미리보기의 동시 롤백을 실제 DB에서 검수했다.
HTTP/JSON parser의 기존100행·UTF-8 1MiB·사용자 소유/권한 확인은 유지한다.
설정된 원본은 원문/JWT를 저장하지 않고 검토 필드·원문 해시·불투명 연결 계약만 남긴다.
원본 POST 조회의 DNS부터 응답 처리까지 네이티브 실행 permit으로 감싼다. 소유 연결을
종료해도 이미 허용한 조회는 끝날 때까지 새 소유자 진입을 막고, 이후 조회/반영은
거절한다. 실제 loopback 원본의 읽기·페이지 재검토·캐시·실패 후 재시도를 검수했으며
원본 조회는 검증 대상 요청과 별도로 집계한다. 실제 외부 ScopeSentry 운영 인스턴스/
JWT 회전/다중 프로세스의 전체 운영 검수는 남아 있다. 미리보기 shape가 서비스가
생성하는 정상 계약이라는 전제이며 임의 손상 JSON 필드의 SQLite 질의 의미까지
일치함을 보장하지 않는다. 가져오기 HTTP 경로 자체는 공유 구현을 쓰지만 전체
PostgreSQL HTTP 저장소 선택/기본 권한/정상 재시작을 검수했으며 전체 운영 검수는 남아 있다.

레코드는 원문 TEXT로 저장하고 검색/관계 연산만 jsonb로 투영한다. 검색 문자열은
바인딩하고 `%`와 `_`도 문자 그대로 검색한다. JSON 객체의 원문 바이트 보존을 검증한
전송과, jsonb 질의의 의미는 별도 계약이다. 중복 JSON 키·PostgreSQL numeric 범위를
벗어나는 수·잘못된 필드 타입까지 SQLite 질의와 동일하게 동작함을 보장하지 않는다.
서비스가 생성하는 정상 레코드의 대표 필터/정렬/커버리지는 SQLite와 결과를 비교했다.
페이지 snapshot은 삽입 순번의 상한이며 과거 편집 내용을 복원하는 기능이 아니다.

감사 순번은 PostgreSQL identity로 할당한다. 롤백으로 번호 공백이 생겨도 해시 연결을
유지한다. SQLite 반환 시 실제 sequence의 할당 상한도 보존해 마지막 커밋 뒤의 실패한
할당 번호를 재사용하지 않는다. 순번은 MVCC 스냅샷 대상이 아니므로 동시 쓰기가 있으면
읽는 행보다 높은 상한을 반환할 수 있다. 이것은 역사적 순번 스냅샷 보장이 아니다.
쓰기 후 실제 pg_dump/pg_restore 및 SQLite 반환에서 공백 보존도 검수했다.

실제 DB 회귀 검수:

```sh
AEGIS_TEST_POSTGRES=1 python -m pytest -q tests/test_postgres_transfer.py tests/test_postgres_store.py tests/test_postgres_ledger.py tests/test_postgres_engine.py tests/test_postgres_ownership.py tests/test_postgres_graph.py tests/test_postgres_reports.py tests/test_postgres_audit_review.py tests/test_postgres_imports.py tests/test_postgres_http.py tests/test_postgres_readers.py tests/test_postgres_backups.py tests/test_postgres_bootstrap.py
```

설치본 검수 스크립트는 checkout 밖에서 잠금 의존성과 wheel을 설치한다. 설치된
PostgresStore로 읽기/쓰기·권한 변경 세션 폐기를 수행한 다음 실제 덤프/복구와
SQLite 반환의 행/감사 해시를 비교한다. 설치된 PostgreSQL HTTP 서버의 인증·질의·
보고서·대화·승인 대기 계획과 정상 종료도 검수한다. 실행 중 네이티브 백업/연결 없는
파일 검증/새 스키마 복구, 복구한 실제 HTTP 서버의 로그인·대기 계획·보고서·그래프도
검수한다. 전체 서비스의 운영 복구·장애/종료/오류/부하 응답 조합 검수는 후속 필수 작업이다.

## 실행 중 논리 백업과 새 스키마 복구

`aegis-backup`/`aegis-restore`는 `--backend` 또는 `AEGIS_STORAGE_BACKEND`를 따른다.
SQLite 기본 동작과 별도로 PostgreSQL에서는 지원 스키마2의 데이터 전용 ZIP_STORED
아카이브를 사용한다. SQL 덤프를 실행하거나 SQLite 복제 DB를 만들지 않는다.
DSN은 `AEGIS_POSTGRES_DSN` 환경변수로만 지정한다.

```sh
aegis-backup --backend postgres --schema aegis_workspace --output backups/aegis-native.zip
aegis-restore --backend postgres --source backups/aegis-native.zip --check-only
aegis-restore --backend postgres --source backups/aegis-native.zip --check-only --checkpoint trusted-checkpoint.json
aegis-restore --backend postgres --source backups/aegis-native.zip --schema aegis_recovery --checkpoint trusted-checkpoint.json
```

백업은 소스 실행 소유권을 빼앗거나 쓰기를 막지 않고 read-only REPEATABLE READ의
한 스냅샷에서 records/users/events/event_hashes/audit_state를 서버 커서(batch32)로
읽는다. 원문 JSON·계정 비밀번호 해시·감사 이력·identity 할당 상한을 보존한다.
세션은 아카이브에서 제외하고 제외 건수만 기록한다. 원본 로그인은 유지한다.
순번 할당기는 MVCC 대상이 아니므로 행 스냅샷보다 앞선 값일 수 있다. 이는 행의
일관성을 깨지 않고 복구본의 할당 번호 재사용을 피하는 상한이다.

닫힌 아카이브의 행 SHA-256·감사 체인·형식을 확인한 뒤 0600 새 파일로 공개한다.
동시 생성자·기존 파일·심볼릭 링크를 덮어쓰지 않고 임시 파일은 정리한다. 검증/읽기
트랜잭션 종료 실패는 공개 전 거절한다. 파일 공개 뒤 디렉터리 fsync가 실패하면
유효한 파일이 남을 수 있으므로 오류 후 출력 경로와 `--check-only`를 확인한다.

아카이브는 정해진6개 파일만 허용하고 압축/암호화/중복 파일명/추가 SQL은 거절한다.
메타데이터64KiB, UTF-8 NDJSON의 한 행4MiB 제한을 적용한다. 행 해시·순서·스칼라 타입·
엄격한 기록 JSON·감사 연결을 읽어 확인한다. `--check-only`는 DB 연결/복구를 하지 않는다.
DB 제약과 실제 복구된 타입의 동일성은 복구 트랜잭션에서 추가 검증한다.
이는 임의 비신뢰 ZIP의 모든 자원 공격을 방어한다는 보장이 아니다. 중앙 디렉터리
파싱과 단일 최대 행의 Python 메모리·DB 서버 정렬/장기 snapshot 영향은 별도 검수 대상이다.

복구는 기존 스키마를 삭제/교체하지 않고 **새 스키마만** 생성한다. 대상 schema의
exclusive transaction gate를 획득하므로 실행 소유자가 있으면 거절한다. 검토된 고정
DDL과 바인딩 COPY로 데이터를 넣고 DB 제약·감사 체인·각 행 해시를 다시 확인한다.
커밋 전 실패는 스키마/테이블/복사본을 함께 롤백한다. 커밋 응답이 유실되면 완료가
불확실할 수 있으므로 해당 새 스키마를 먼저 확인한다. 같은 이름의 재시도는 덮어쓰지 않는다.

새 스키마에서 별도 HTTP 서버를 시작해 기존 비밀번호 로그인·자산·증거·보고서를
확인한 뒤 운영 서버를 종료하고 `AEGIS_POSTGRES_SCHEMA`를 검증한 이름으로 변경한다.
명령은 운영 서버/설정을 자동 전환하지 않는다. 이전 스키마는 그대로 남지만 전환 후
양쪽에 생긴 쓰기는 자동 병합되지 않는다. 복구본의 기존 세션은 모두 무효이며 다시
로그인해야 한다. 미완료 작업/호출은 시작 복구에서 interrupted로 표시하고, 승인 대기
계획은 실행하지 않는다. 재점검/실행은 현재 계약과 범위를 확인하고 새로 승인한다.

백업에는 비밀번호 해시와 증거가 있으므로 별도 보호된 보관소에 복사한다. 자체 행
해시는 공격자가 전체 아카이브를 다시 만드는 것을 인증하지 못한다. 신뢰할 독립
감사 체크포인트는 감사 접두부 비교에만 사용하며 모든 자산/계정의 서명이 아니다.
DB 역할/권한/확장/함수/트리거와 전체 PostgreSQL 인스턴스는 백업하지 않는다.
WAL/PITR·HA·전체 서버 복구·실제 버전 업그레이드·원격 장애·전원 차단은 미검수다.
현재 지원 형식의 논리 데이터 복구이며 `aegis-release`의 SQLite 업데이트 계약은 별도다.

## 실행 소유권과 연결 상실

`PostgresLease`는 DB/스키마별 runtime advisory key를 독점 session lock으로
획득해야 시작할 수 있다. 같은 연결에서 shared session lock을 먼저 획득한 뒤
exclusive lock을 해제하므로 소유권에 공백이 없다. 별도 프로세스의 중복 획득은
즉시 거절된다. 스키마별 소유권은 독립적이다. 이 전용 연결은 재연결하지 않는다.
직접 libpq 세션 연결을 전제로 하며 transaction pooling 프록시 지원은 검수하지 않았다.

소유자에 연결된 Store의 모든 트랜잭션은 같은 key의 shared transaction lock을
획득하고, 전용 소유 세션의 PID·backend_start·실제 granted lock을 확인한다.
이미 허용한 작업은 연결이 끊겨도 transaction gate를 보유하므로 작업이 끝나기 전
다른 서버가 소유권을 획득하지 못한다. 다음 작업은 이전 소유 세션이 없어 거절된다.
새 소유자가 생겨도 이전 Store는 그것을 자신의 소유자로 채택하지 않는다.
정상 종료 후 Store도 종료된 객체로 남으며 새 실행에는 새 Store를 만든다.

Engine은 이 소유권을 획득한 뒤에만 복구/실행하고 종료 시 Worker를 기다린 후 해제한다.
시작 복구/실행 풀 생성 오류도 소유 연결을 닫는다. 큐 감시자가 소유권 상실을 확인하면
새 승인을 닫고 stop 신호를 설정한다. 잃은 소유자로 종료 기록을 쓰지 않으며 새 소유자의
시작 복구가 미완료 상태를 표시한다. 내장 대상 HTTP 요청과 Planner/대화의 제공자 요청은
shared transaction permit으로 보호한다. 허용한 요청이 진행 중이면 새 소유자의 시작을
막고, 다음 요청은 소유권을 다시 확인한다. 실제 소유 backend를 종료한 검수에서
진행 중 대상/제공자 요청의 교체 배제와 다음 요청/쓰기 거절을 확인했다.

소유자에 연결하지 않은 Store 쓰기는 exclusive transaction gate를 사용하므로
실행 소유자와 겹치지 않는다. 오프라인 반환도 exclusive gate를 즉시 획득해야 한다.
사용 중이면 결과 파일을 만들지 않는다. 중지된 DB의 세션은 반환본에서만 제외한다.
실행 중 서비스의 데이터 백업은 아래 읽기 스냅샷으로 가능하다. 전체 PostgreSQL
운영 복구 검수는 남아 있다. 독립 읽기 클라이언트는
읽기 스냅샷만 사용할 수 있으며 실행 permit은 소유권이 있어야 발급한다.

일반 DB 계정의 schema/table/sequence 권한으로 동작함을 검수했다. advisory 계약은
협력하는 애플리케이션 사이의 배제이며 DB 관리자나 raw SQL의 권한을 대체하지 않는다.
직접 DB 세션 종료·정상 종료·시작 실패·교체를 검수했지만 remote TCP blackhole,
프록시/HA 전환·네트워크 지연의 종료 시간 SLO·실제 전원 장애는 검수하지 않았다.
서버의 idle_session_timeout 등으로 소유 연결이 종료돼도 작업은 거절하고 재시작이 필요하다.
이 구현만으로 PostgreSQL HTTP 서비스 배포 지원 완료를 표시하지 않는다.

잠금/세션 식별의 기반은 PostgreSQL16
[advisory lock](https://www.postgresql.org/docs/16/explicit-locking.html#ADVISORY-LOCKS),
[pg_locks](https://www.postgresql.org/docs/16/view-pg-locks.html),
[pg_stat_activity](https://www.postgresql.org/docs/16/monitoring-stats.html#MONITORING-PG-STAT-ACTIVITY-VIEW)다.
위 shared gate와 소유 세션 확인은 이 프로젝트가 구현·검수한 계약이다.

구현 시 참고한 기본 계약:
[Psycopg 트랜잭션](https://www.psycopg.org/psycopg3/docs/basic/transactions.html),
[COPY](https://www.psycopg.org/psycopg3/docs/basic/copy.html),
[PostgreSQL16 pg_dump](https://www.postgresql.org/docs/16/app-pgdump.html).
네이티브 계층의 기본 계약은
[트랜잭션 격리](https://www.postgresql.org/docs/16/transaction-iso.html),
[advisory lock](https://www.postgresql.org/docs/16/explicit-locking.html#ADVISORY-LOCKS),
[JSON 함수](https://www.postgresql.org/docs/16/functions-json.html)를 참고했다.
