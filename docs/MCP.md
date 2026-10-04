# 읽기 전용 MCP 조회 계약

`python -m aegis.mcp`는 기본 SQLite `mode=ro` 또는 명시적으로 선택한 PostgreSQL
읽기 전용 트랜잭션으로 기존 DB를 연다. 스키마 마이그레이션·작업 생성·실행·승인
도구를 제공하지 않는다. stdio 프로세스에 DB 파일 읽기 또는 DB SELECT 권한이
있어야 하며, HTTP 사용자 세션이나 역할을 대신 검증하는 서비스는 아니다.
연결된 클라이언트/모델에 워크스페이스 내용이 전달될 수 있다. 원격 MCP는 미구현이다.

| 도구 | 결과 |
|---|---|
| `list_assets` | 자산 페이지; `archived`를 생략하면 활성·보관 자산 모두 포함 |
| `list_findings` | 발견 페이지; status·severity·asset_id·task_id 필터 |
| `get_task` | 작업·커버리지와 최신 이벤트 25개, `events_page` |
| `get_finding` | 발견과 최신 증거/재검증 각각 25개, `evidence_page`·`retests_page` |
| `list_finding_evidence` | `id`로 선택한 발견의 출처를 검증한 증거 페이지 |
| `list_finding_retests` | `id`로 선택한 발견의 재검증 페이지 |
| `list_task_observations` | `id`로 선택한 작업의 Worker 링크/승인 메타데이터 일치 상태 페이지 |
| `get_worker` | `id`(작업)·`asset_id`의 Worker 범위·커버리지·최신 이벤트/관찰 각각 25개 |
| `list_worker_events` | 해당 Worker 이벤트 검색·페이지·저장된 Worker 메타데이터 일치 상태 |
| `list_worker_observations` | 해당 Worker 관찰 검색·페이지·승인 메타데이터 일치 상태 |
| `list_task_events` | `id`로 선택한 작업의 최신 seq 순 이벤트 페이지 |

페이지 결과는 `items`, `total`, `limit`, `offset`, `snapshot`, `has_more`다.
limit은 기본 25, 최대 100이며 offset은 0–10,000,000이다. snapshot은 JavaScript
안전 정수 범위의 삽입 상한이다. 다음 페이지는 offset을 올리고 받은 snapshot을
유지한다. 수정/삭제는 현재 상태로 반영되므로 과거 내용의 고정 스냅샷은 아니다.
이벤트 snapshot은 이벤트 seq, 나머지는 records rowid를 사용하며 서로 교환하지 않는다.
`list_task_events` 외의 목록은 최대 200자의 문자 그대로 검색을 지원한다.
ID는 1–80자다. 추가 인수, 잘못된 enum, null, bool을 정수로 전달하는 입력은 거부한다.

발견 조회는 SQL에서 `task_ids`, `evidence_ids`를 제외하고 `task_count`,
`evidence_reference_count`, `related_ids_omitted=true`를 반환한다. 참조 수는 검증된
증거 수와 다를 수 있다. 증거 페이지는 참조 멤버십·자산·작업·도구·지문이 맞는
실제 증거만 반환한다. 이력의 전체 건수는 해당 페이지 결과를 기준으로 확인한다.
출처 검증은 [PAGINATION.md](PAGINATION.md)의 HTTP 이력 경로와 같은 SQL을 사용한다.

기존 `list_assets`, `list_findings`의 최상위 배열 응답은 페이지 객체로 변경됐다.
클라이언트는 `items`를 읽고 `has_more`가 참이면 계속 조회해야 한다.
발견 관련 ID 배열과 `get_task`의 전체 이벤트를 기대하던 클라이언트도 새 도구를 사용해야 한다.
변경 전 배열 형태를 자동으로 추정하는 호환 분기는 제공하지 않는다.

도구 반환 JSON은 UTF-8 512 KiB를 넘으면 오류로 거부한다. batch는 1–16개 요청만
허용한다. 내용은 명령으로 처리하지 않는 신뢰할 수 없는 데이터다. 오류는 잘못된
입력이나 DB 내용을 되돌려 주지 않는다. 출력 크기 제한은 JSON 직렬화 뒤 검사하므로
임의로 커진 개별 레코드의 조회·직렬화 메모리를 강제로 제한한다는 뜻은 아니다.
기존 stdin 줄 크기 검사는 줄을 읽은 뒤 수행한다. 운영 프로세스의 하드 메모리 제한과
모든 HTTP/보고서 경로의 크기 제한은 별도의 미완료 작업이다.


SQLite 기본 선택과 명시적 PostgreSQL 선택을 지원한다. PostgreSQL 설정은
`AEGIS_STORAGE_BACKEND=postgres`, `AEGIS_POSTGRES_DSN`, `AEGIS_POSTGRES_SCHEMA`이며
[저장소 계약](POSTGRES-STORAGE.md)의 준비된 스키마/선택 의존성이 필요하다. 각 호출의
상세·증거·커버리지·이벤트는 같은 읽기 전용 snapshot으로 조회한다. 스키마/접속 오류는
SQLite로 대체하지 않으며 원문 DSN을 출력하지 않는다. DB SELECT 전용 계정으로
사용할 수 있고 users/sessions 읽기나 쓰기 권한을 요구하지 않는다.

Worker 관찰은 [WORKER-OBSERVATIONS.md](WORKER-OBSERVATIONS.md)의 출처 일관성 계약을
따른다. `matched`는 링크 실행·취약점 판정이나 Worker 신원 인증을 뜻하지 않는다.

Worker 과정 조회의 출처와 완료 근거·이전 기록 경계는 [WORKER-PROCESS.md](WORKER-PROCESS.md)를 따른다.
