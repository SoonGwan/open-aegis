# Changelog

## Unreleased — v1 개발

- 계획 가족의 공유 할 일 생성/편집·담당자 지정·변경 이력 화면, 미확인 생성 복원과 동시 편집 충돌 비교.

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
