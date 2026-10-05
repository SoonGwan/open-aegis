# Changelog

- Goal drafts optionally decompose natural-language requests into reviewed objectives,
  catalog checks, selected assets and Worker dependencies before a separate approval.
  Durable request replay, provider usage, rules fallback and per-objective execution
  counts distinguish tool completion from semantic goal verification.

- Explicit observed-response plans select up to10 verified Worker URLs, require new
  approval, execute bounded GET configuration checks with per-URL proof/failures,
  preserve original-URL retests and recover unknown create outcomes by request ID.

## Unreleased — v1 개발

- 선택한 관찰 URL·검사 조합의 원격 응답 배치를 연결한다. URL 응답 재사용, 출처/계획 순서 서명, 검사별 커버리지·부분 실패 후속 계획·원래 URL 재검증과 배치 전체의 원자적 저장을 지원한다.

- 원격 작업의 서명 권한 취소·영속 폐기·응답 대기 중단과 취소 확인/미확인 실행 기록을 연결한다. 기존 nonce 이력과 재사용 방지는 보존하며, 이미 전송된 요청의 부작용은 되돌리지 않는다. 신뢰한 MCP 클라이언트 대기 제한을 실제 소켓/요청 guard에도 적용한다.

- 구성된 고정 MCP GET 서버의 관리자 검토·선택·별도 실행 승인·Worker 호출·발견/증거/감사 원자적 저장을 연결한다. 전송 직전 권한/자산 변경 거절, 자산별 공유 요청 예산, 미확인 전송 비재호출과 원격 위치를 보존한 새 승인 재검증을 지원한다. 서명 권한 취소는 연결했으며 프로세스/연결 장애 후 취소 확인과 일반 플러그인 격리는 남아 있다.

- 목표 과제 근거·완료율·후속 제안·재검증 생성은 원본의 유효한 숫자 승인 시각을 요구한다. 승인 기록이 없거나 잘못된 원본과 재검증은 검증 근거로 표시하지 않으며 기존 증거는 보존한다.
- 목표 과제의 발견 검색·페이지·증거 스냅샷을 URL로 복원하며 조회 실패 재시도는 저장된 위치를 유지한다. 다른 작업으로 이동한 뒤 도착한 위치 응답은 반영하지 않는다.
- 목표 후속 회차는 원래 과제와 선택 실행 조합을 유지하며 새로 승인한다. 미실행 카탈로그 도구를 추가하지 않고 목표 밖 할 일 요청은 새 초안 검토를 요구한다.

- 목표 과제에서 별도 승인 재검증 계획을 만들고 원래 과제/발견 참조를 교체·재실행·결과에 보존한다. 같은 요청 복구와 최종 출처 재검사, 원자 저장을 지원한다.

- 목표 과제의 실제 출처 증거와 일치하는 발견을 검색·페이지 조회하고, 검증된 별도 재검증 이력과 발견/작업 상세를 연결한다. 기존 목표 완료율과 목표 달성 판정은 분리한다.

- 새 목표 계획은 과제별 자산/검사 조합만 실행하고 중복 조합은 공유한다. 기존 계획의 승인 계약은 보존하며, Worker 완료 근거·보고서·SQLite/PostgreSQL 커버리지도 실제 선택 범위를 따른다.

- Worker 관찰의 출처·완료 근거·현재 범위 확인 후 계획 당시 맥락 저장, 규칙/AI 도구 우선순위 반영과 URL 없는 제공자 입력, 포함·제외·표본 밖 수의 검토 화면.

- 종료·할 일·자산 이벤트에서 후속 제안을 자동 준비, 처리 위치와 제안 원자 저장 및 재시작/자산 페이지 재개, 준비·변경·실패 상태 표시.

- 공유 할 일의 검증 도구 요청을 다음 계획에 반영, 생성 당시 항목/버전 저장과 최종 변경 검사, 승인된 도구의 규칙/AI 순서에 고정 맥락 적용.

- 계획 가족의 공유 할 일 생성/편집·담당자 지정·변경 이력 화면, 미확인 생성 복원과 동시 편집 충돌 비교, 목록/선택/이력 탐색 URL 복원.

- 관리자·운영자·조회자 계정과 서버 역할 검사, 사용자·비밀번호 관리.
- 스키마 버전 1, 자동 백업·기존 관리자 이전·기존 세션 폐기.
- 일관된 온라인 백업 검증, 오프라인 복구·롤백 복사본·복구 세션 폐기.
- 워크스페이스 파일 잠금으로 중복 서버/실행 중 복구 차단.
- 사용자 변경 감사 기록, 오래된 사용자 수정 충돌 검출.
- 요청 본문 2 MiB·수신 30초 제한, 입력 오류 응답의 비밀정보 제거.

- Wanted Montage semantic 토큰 정리와 Neo-brutalism UI 적용.
- 자산 수정·보관·복원, 예약 중지, 과거 범위 승인 무효화.
- 대화상자 배경 inert, 숨겨진 입력의 포커스 제외, 검색 빈 결과.
- 실제 SSE 연결을 유지한 SIGTERM 종료 오류 수정 및 subprocess 회귀 검증.
- v1 출시 기준과 디자인 대비 검증 도구.

## 0.1.0 — 2026-10-03

Initial independently implemented workspace: Korean console, asset registration,
scoped validation plans, approval, parallel workers, six reviewed check types,
metadata-only HTTP evidence, findings and retests, report exports, schedules,
notes, record assistant, optional provider planning, read-only MCP, authentication,
local fixture, behavioral tests, locked dependencies, Docker configuration and
online SQLite backup tool.

Known gaps and distinctions from ARTEX are recorded in `docs/FEATURES.md`.
