# PostgreSQL 저장소와 전송

현재 구현은 **오프라인 전송·되돌리기와 네이티브 Store 계층**이다. HTTP 서비스의 PostgreSQL 실행
백엔드는 아직 연결하지 않았다. `AEGIS_POSTGRES_DSN`만 설정해도 서비스가 PostgreSQL로
전환되는 것은 아니다. 전체 v1의 PostgreSQL 조건은 열린 상태다.

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
트랜잭션으로 읽는다. 예상 테이블 구성·형식·순서 기준·빈 세션·감사 연결을 검사한다.
뷰/외부 테이블/추가 테이블은 거절한다. 현재 형식에는 실행 중 PostgreSQL 서비스를 위한
운영 세션이나 쓰기 배제 계약이 없으므로 세션이 들어 있는 스키마도 거절한다.

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

남은 v1 조건은 HTTP/작업 실행의 PostgreSQL Store 연결·보고서/감사 읽기,
서버 선택 설정·업그레이드·백업/복구의 운영 계약과 HTTP/권한/동시성/재시작 전체 검수다.
현재 전송 형식은 그 기반이며, 이를 PostgreSQL 서비스 지원 완료로 표시하지 않는다.

## 네이티브 Store 계층

`aegis.postgres_store.PostgresStore(dsn, schema)`는 전송으로 생성한 형식의 스키마를
직접 읽고 쓴다. SQLite SQL 변환이나 SQLite 복제 DB를 사용하지 않는다. 생성자는
형식/감사 기준을 읽기만 하며 세션 폐기·작업 복구·스키마 변경을 하지 않는다.
현재 서비스의 Store 선택 설정에는 연결하지 않았으며 공개 HTTP PostgreSQL 지원을 뜻하지 않는다.
Engine의 큐 지표/기한 조회와 발견 관찰·조치·재검증은 저장소별 쿼리와 쓰기 트랜잭션을
사용한다. 소유한 단독 검수 환경에서 네이티브 PostgreSQL Engine의 승인→로컬 요청→
증거/커버리지 저장, 재검증 해결 판정, 실행 중 중지·큐 만료·시작 복구를 검수했다.
이것은 HTTP 서비스의 PostgreSQL 실행이나 다중 서버 운영 소유권 검수가 아니다.
서비스 시작 잠금/연결 상실 처리와 보고서/그래프/가져오기 경로가 남아 있다.

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
복구 호출자는 서비스의 독점 시작 권한을 가져야 한다. PostgreSQL 서비스 소유권/
시작 잠금과 HTTP 실행 경로의 연결은 아직 남아 있다.

사용량·비용 요약은 같은 읽기 스냅샷에서 필요한 메타데이터만 서버 커서로 200개씩
받는다. 전체 작업/메시지나 개인 질문/답변을 읽어 목록으로 만들지 않는다. 토큰 합계는
정수로, 견적은 기존 호출 시점 가격의 검증·통화별 정수 단위 합산으로 계산한다.
단일 aggregate 응답을 반환하지만 서버→클라이언트의 메타데이터 전송은 호출 수에
비례한다. 이 초기 경로의 대규모 집계 성능과 개별 메타데이터의 자원 한도는 미검수다.
실제 로컬 모형 제공자→PostgreSQL 시작 기록→응답 관찰→답변 원자 저장을 검수했다.
사용량 조회 중 별도 DB 쓰기가 일어나도 토큰·비용은 같은 스냅샷의 값으로 집계했다.

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
AEGIS_TEST_POSTGRES=1 python -m pytest -q tests/test_postgres_transfer.py tests/test_postgres_store.py tests/test_postgres_ledger.py tests/test_postgres_engine.py
```

설치본 검수 스크립트는 checkout 밖에서 잠금 의존성과 wheel을 설치한다. 설치된
PostgresStore로 읽기/쓰기·권한 변경 세션 폐기를 수행한 다음 실제 덤프/복구와
SQLite 반환의 행/감사 해시를 비교한다. HTTP PostgreSQL 실행, 운영 서버 재시작,
운영 백업/복구, 다중 서비스 인스턴스 배제 계약은 후속 필수 작업이다.

구현 시 참고한 기본 계약:
[Psycopg 트랜잭션](https://www.psycopg.org/psycopg3/docs/basic/transactions.html),
[COPY](https://www.psycopg.org/psycopg3/docs/basic/copy.html),
[PostgreSQL16 pg_dump](https://www.postgresql.org/docs/16/app-pgdump.html).
네이티브 계층의 기본 계약은
[트랜잭션 격리](https://www.postgresql.org/docs/16/transaction-iso.html),
[advisory lock](https://www.postgresql.org/docs/16/explicit-locking.html#ADVISORY-LOCKS),
[JSON 함수](https://www.postgresql.org/docs/16/functions-json.html)를 참고했다.
