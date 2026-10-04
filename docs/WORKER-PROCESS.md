# Worker 실행 과정 조회

Worker는 한 작업의 승인 범위에 포함된 자산 하나를 검증하는 실행 단위다. 식별자는
`task_id:asset_id`다. HTTP 경로와 MCP 입력은 두 ID를 각각 받는다. 현재 자산의
주소·이름을 대입하지 않고 작업에 저장된 승인 범위와 revision을 사용한다.

## 조회 경로

인증된 admin/operator/viewer가 다음 GET을 사용할 수 있다.

- `/api/tasks/{task_id}/workers`: 승인 범위의 Worker 목록, 최대 20개.
- `/api/tasks/{task_id}/workers/{asset_id}`: 해당 Worker의 범위, 작업 상태·승인 시각,
  도구별 커버리지 최대 6개, 최신 이벤트·관찰 각각 25개와 페이지 정보.
- `/api/tasks/{task_id}/workers/{asset_id}/events`: 해당 Worker 이벤트 검색·페이지.
- `/api/tasks/{task_id}/workers/{asset_id}/observations`: 해당 Worker 관찰 검색·페이지.

페이지의 limit 기본값은 25, 최대 100이며 search 최대 200자, offset 최대
10,000,000이다. 이벤트 snapshot은 seq, 관찰 snapshot은 records 삽입 상한이다.
두 값을 교환하지 않는다. 삽입 상한은 다음 페이지에 새 기록이 끼어드는 것을
제한하며 이후 수정까지 고정하는 과거 스냅샷은 아니다.

MCP `get_worker`, `list_worker_events`, `list_worker_observations`는 `id`(작업),
`asset_id`로 같은 조회를 제공한다. 목록 도구는 기존 페이지 인수를 지원한다.
모든 도구는 읽기 전용이며 기존 512 KiB 반환 제한을 적용한다. DB SELECT 권한을
가진 클라이언트가 사용할 수 있고 HTTP 인증 역할을 대신하는 서비스는 아니다.

## 완료 근거와 경계

각 호출은 범위·커버리지·이벤트·관찰을 같은 읽기 DB 스냅샷에서 조회한다.
전체 이력을 Python 배열로 읽지 않고 커버리지는 예상 ID로, 이벤트·관찰은
작업/자산 조건과 SQL limit으로 읽는다. 다른 Worker·작업·자산 없는 Planner
이벤트는 Worker 이벤트 페이지에 포함하지 않는다.

커버리지 누락·알 수 없는 상태·ID 불일치·revision 불일치는 완료로 표시하지 않는다.
이전 기록의 없는 셀은 진행 중 작업에서 not_started, 종료 작업에서 not_recorded다.
현재 자산이 수정되어도 당시 승인 revision의 과정은 보존한다.

새 실행의 Worker 이벤트는 task_id, asset_id, worker_id를 함께 저장한다.
`worker_provenance.status=matched`는 그 저장 메타데이터의 일치이며 암호학적으로
인증된 Worker 신원이나 실행 성공 증명이 아니다. Worker ID가 없는 이전 이벤트는
자산 조건으로 조회하되 unconfirmed로 표시한다. 관찰은 기존
[출처 계약](WORKER-OBSERVATIONS.md)을 따른다. 링크는 아직 방문한 주소나 검증 성공
근거가 아니다. 내용은 신뢰할 수 없는 데이터이고 `execution_authorized=false`다.

저장 키와 작업 payload ID가 다르거나 작업 범위가 없거나 중복/잘못된 도구 목록이면
Worker 조회는 거절한다. 개별
레코드 payload 크기를 강제 제한하는 기능이나 전체 실행 이력 보존 정책은 아니다.
작업별 Worker 조회는 구현했지만 전체 워크스페이스 과정 검색 UI, 반복 Planner가
이 과정을 자동 소비하는 단계, 공유 할 일은 아직 남아 있다. 승인된 의존 실행과 완료 근거/관찰 참조 전달은
[WORKER-DEPENDENCIES.md](WORKER-DEPENDENCIES.md)에 구현 범위를 정리했다.
