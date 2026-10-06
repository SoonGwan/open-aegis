# ARTEX 전체 기능 추적 목록

2026-10-06에 확인한 원본 커밋은
[`b55ceb1fdd84a813d77de09a06af83d323a81f85`](https://github.com/Autumn-27/ARTEX/tree/b55ceb1fdd84a813d77de09a06af83d323a81f85)이다.
이전 README 중심 비교에서 빠진 기능을 공개 HTTP 등록, 화면 진입점, 선택한
하위 시스템의 소스 읽기로 보충한다. 원본을 설치·실행하거나 전체 보안 감사를
완료한 기록은 아니다. 이후 원본의 변경은 이 고정 목록에 자동 반영되지 않는다.

[기계 판독 목록](artex-source-inventory.json)은 **HTTP 등록 261개**와
**화면 진입점 27개**를 담는다. 메인 서버의 직접 문자열 등록 243개에 발견 트래픽
7개와 별도 질문 11개를 수동 검토해 확장했다. HTTP 등록 수는 기능 수가 아니며,
이 목록에는 SDK 내부 도구나 모든 Go 함수가 열거돼 있지 않다.
agent/server 소스에서 문자열 이름을 직접 선언한 도구 생성 호출 **49곳**도
파일·행·이름으로 기록한다. 실제 런타임 목록을 실행해서 센 값이 아니며
동적/MCP/skill/SDK 도구는 이 수치에 포함하지 않는다.
[메인 등록](https://github.com/Autumn-27/ARTEX/blob/b55ceb1fdd84a813d77de09a06af83d323a81f85/server/server.go),
[트래픽 등록](https://github.com/Autumn-27/ARTEX/blob/b55ceb1fdd84a813d77de09a06af83d323a81f85/server/finding_traffic.go),
[별도 질문 등록](https://github.com/Autumn-27/ARTEX/blob/b55ceb1fdd84a813d77de09a06af83d323a81f85/server/side_questions.go)을 기준으로 한다.

아래 ‘연결됨’은 OpenAegis의 현재 구현 경계를 뜻한다. 원본과 동등하거나 완성됐다는
판정이 아니다. 세부 실행 근거는 [검증 기록](VALIDATION.md), 출시 조건은
[v1 기준](V1-READINESS.md), 기존 구현 위치는 [기능 비교](FEATURES.md)를 따른다.
새로 발견한 항목은 이 목록에서 미완료 상태로 추적하며 구현된 것으로 계산하지 않는다.

## 작업·계획·실행

| 기능군 | 원본에서 확인한 구성 | OpenAegis 상태·다음 조건 |
|---|---|---|
| 작업 생성·상세·메타데이터 | 목표·작업 목록·상세·수정 | 범위 스냅샷과 승인 계획 연결됨; 종료 이력의 자유 수정은 제공하지 않음 |
| 작업 분류·일괄 변경 | 분류 CRUD, 여러 작업 분류 변경 | 일부 구현: 버전·이력·보관/복원·CRUD 화면, 분류별 SQL 검색/페이지, 최대25개 원자적 변경·요청 재시도·출처 상속([계약](TASK-CATEGORIES.md)); 전체 모바일·모달 복원·교차 버전 검수는 남아 있음 |
| 작업 템플릿 | 이름·설명·목표·분류·승인 규칙 저장 | 일부 구현: 버전·이력·보관/복원·CRUD·화면·분류 라벨·새 승인 대기 계획; 관리자 승인 정책 고정, 별도 분류 관리·모달 복원·전체 모바일 검수는 남아 있음([계약](TASK-TEMPLATES.md)) |
| 작업 큐·동시성·시간 제한 | admission, engine, scheduler, timeout | 실행 예산·공유 origin 제한·대기열·중지 연결됨 |
| 일시정지·재개·일괄 통제 | task/intent control, batch control | 중지·새 승인 재실행 연결됨; 동일 승인으로 상태 복원·일괄 통제 미구현 |
| 개별 Worker 개입 | 의도 중지, 메시지로 재개, 개별·blocked 재실행 | 의존 실행/근거 공유 연결됨; 실행 중 자연어 지시 재개 미구현 |
| 목표 분해·목표 편집 | goals agent, 목표 CRUD | 자연어 초안·검토·새 승인 실행 연결됨; 진행 작업 목표 편집 미구현 |
| 운영 제약 관리 | constraints CRUD 및 agent 맥락 | 고정 범위·실행 예산 연결됨; 자연어 운영 제약 편집 미구현 |
| 반복 계획·할 일 | planner, 공유 blackboard, 이벤트 병합 | 이벤트 후속 제안·할 일·새 승인·회차 이력 연결됨 |
| Worker 과정 공유 | 실행 과정 조회·다른 Worker 기록 활용 | 작업/자산별 과정 조회·검색·승인 의존 단계 참조 연결됨 |
| 과제 완료 판정 | 증명 도구·목표/의도 상태 | 검사 진행률/실제 증거 참조 연결됨; 실제 자연어 목표 달성 판정 미구현 |
| 다른 작업 관리·참조 | 작업/모델 목록, 작업 생성·일시정지·다른 작업 그래프/발견/기록 참조 | 새 승인 후속 작업·회차 연결/기록 조회 연결됨; 범용 agent의 다른 작업 생성·통제 미구현 |
| 그래프 기억 압축 | cold graph, digest, 원본 펼침·관련 작업 읽기 | 기록/페이지 조회 연결됨; 자동 기억 압축·장기 기억 미구현 |
| 작업 아카이브·복원 | 대기 처리·일괄 보관/복원/삭제·압축 파일 패키지 | 일부 구현; 종료 작업 최대25개 원자적 보관/복원·이력·요청 복구·고정 선택 버전·SQL/URL·충돌 후 재선택([계약](TASK-ARCHIVES.md)); 삭제·자동 보관·압축 패키지·설치본/전체 모바일 검수는 남아 있음 |

핵심 읽기 위치:
[작업 통제](https://github.com/Autumn-27/ARTEX/blob/b55ceb1fdd84a813d77de09a06af83d323a81f85/server/task_control.go),
[템플릿](https://github.com/Autumn-27/ARTEX/blob/b55ceb1fdd84a813d77de09a06af83d323a81f85/server/task_templates.go),
[Worker 개입](https://github.com/Autumn-27/ARTEX/blob/b55ceb1fdd84a813d77de09a06af83d323a81f85/server/intent_intervention.go),
[기억 펼침](https://github.com/Autumn-27/ARTEX/blob/b55ceb1fdd84a813d77de09a06af83d323a81f85/agent/tools_digest.go),
[아카이브](https://github.com/Autumn-27/ARTEX/blob/b55ceb1fdd84a813d77de09a06af83d323a81f85/server/task_archive_package.go).

## 자산·발견·증거

| 기능군 | 원본에서 확인한 구성 | OpenAegis 상태·다음 조건 |
|---|---|---|
| 자산 계층·귀속 | 도메인/IP/서비스/앱/엔드포인트, 회사·회사 범위·재귀속 | 승인 URL 자산·담당자·태그·revision 연결됨; 회사 계층·범용 네트워크 지도 미구현 |
| 작업 자산·범위 연결 | task asset refs, scope CRUD, intent-assets | 승인 당시 범위·관찰 출처 연결됨; 실행 중 범위 확대는 새 승인 계획 필요 |
| 이중 그래프·앵커 | asset graph + exploration graph | 실제 자산/작업/증거/관찰 관계 연결됨; 원본의 의도·사실 그래프와 동등하지 않음 |
| 커버리지 그래프 | 자산별 실행 상태·coverage graph | 실패·건너뜀·중지·이전 revision 포함 분모 연결됨 |
| 비동기 자산 보강 | DNS와 HTTP 보강 큐·중복 억제·관계 기록 | 범위 내 HTML 링크 관찰 연결됨; 자동 DNS/서비스 보강 미구현 |
| 발견 조회·그룹·자산 트리 | 목록·그룹·자산 트리·통계·lineage | 발견 검색/페이지·관계 그래프·원본 이동 연결됨; 전용 그룹/자산 트리 UI 미구현 |
| 발견 조치·보고 내용 변경 | workflow、보고 수정·발견 삭제 | 담당자·사유·버전 충돌·조치 이력 연결됨; 증거 원본 임의 변경은 제공하지 않음 |
| 추가 조사·독립 재검증 | deepen, retester, 진행 세션·증거 보존 | 별도 승인 재검증·재현/해결/판정 불가·사람 결정 보존 연결됨 |
| 발견 트래픽 증거 | 요청 연결·순서·메모·버전·본문 조회 | 자체 GET 메타데이터/해시와 발견 증거 연결됨; 원문 트래픽 증거 연결/편집 미구현 |
| 트래픽 수집·검색·삭제 | recording proxy, host 목록, request/response blob | 자체 검증 요청 기록 연결됨; 범용 MITM/CA 프록시 미구현 |
| 보고서·내보내기 | 보고서 및 발견 export | 동일 스냅샷 Markdown/CSV/JSON 스트리밍 연결됨; 원문 트래픽 패키지는 미구현 |
| ScopeSentry 자산 동기화 | 데이터 소스·프로젝트·작업 선택·실행 | 출처·미리보기·선택·충돌·중복 방지·원격 페이지 복구 연결됨; 원본 운영 호환 검수 남음 |

읽기 위치:
[자산 보강](https://github.com/Autumn-27/ARTEX/blob/b55ceb1fdd84a813d77de09a06af83d323a81f85/enrich/enrich.go),
[발견 재검증](https://github.com/Autumn-27/ARTEX/blob/b55ceb1fdd84a813d77de09a06af83d323a81f85/server/finding_retests.go),
[트래픽 증거](https://github.com/Autumn-27/ARTEX/blob/b55ceb1fdd84a813d77de09a06af83d323a81f85/server/finding_traffic.go),
[자산 동기화](https://github.com/Autumn-27/ARTEX/blob/b55ceb1fdd84a813d77de09a06af83d323a81f85/server/sync_scopesentry.go).

## 사람·에이전트·확장·모델

| 기능군 | 원본에서 확인한 구성 | OpenAegis 상태·다음 조건 |
|---|---|---|
| 대화·세션 관리 | 작업 대화·독립 대화·이름/프로필·일괄 삭제·중지 | 작업 기록 질문·출처 인용·중복 없는 재시도·선택적 AI 연결됨; 독립 범용 대화 미구현 |
| 파일 첨부·참조 검색 | upload, chat mentions | 검증 기록 인용 연결됨; 파일 업로드·자유 참조 검색 미구현 |
| 실행 옆 별도 질문 | main/worker/conversation 질문, 이벤트·취소 | 기록 기반 질문 연결됨; 진행 모델 세션의 별도 질문 미구현 |
| 에이전트 편집 | 생성·구성·도구/모델 바인딩 | 고정 역할·작업별 Worker/Planner 설정 연결됨; 사용자 정의 실행 agent 미구현 |
| 프롬프트 관리 | prompt/wrapup/timeout-wrapup, 버전·변수·미리보기·초기화 | 일부 구현; 계획/기록 대화의 관리자 추가 지침·불변 버전·제한 변수·로컬 미리보기·기본값 복원·호출 당시 스냅샷([계약](PROMPT-VERSIONS.md)); 사용자 agent/종료/시간 제한 프롬프트는 남아 있음 |
| 사용자 정의 트리거 | 주기·발견·목표·시간 제한·도구 호출·작업 생성 | 이벤트 기반 계획 제안/예약 연결됨; 사용자 agent 트리거 미구현 |
| 내장 도구 카탈로그 | 설명·기본값·agent 바인딩·초기화 | 내장 6개 도구의 계약/지문/승인 연결됨; 사용자 카탈로그 편집 미구현 |
| 사용자 도구 | command/script/http 생성·수정·테스트 | 일반 플러그인 계약·OS/egress 격리 미구현; 고정 GET 어댑터만 실행 |
| MCP 연결·목록 갱신 | HTTP/SSE 구성·도구 조회·새로고침 | 제한된 HTTP 클라이언트·관리자 목록 검토/등록·고정 서버 승인 실행·서명 취소/장애 복구·선택 관찰 응답 배치/재검증 연결됨; 범용 SSE/플러그인 실행 미구현 |
| skills 관리 | 생성·ZIP 업로드·파일 편집·메타데이터·사용/미존재 조회 | 외부 실행 skills 등록 미구현 |
| 플랫폼 자동 관리 도구 | agent가 skill/도구/MCP 생성·수정 | 미구현; 실행 권한을 자동 등록하지 않음 |
| agent/도구/MCP/skill 가시성 | 리소스별 표시·바인딩 | 서버 RBAC 연결됨; 리소스별 가시성 편집 미구현 |
| 모델 구성·프로필 | 여러 profile·활성 설정·task/agent 고정·모델 조회·연결 테스트 | 고정 수신처 관리자 프로필/용도별 선택/호출 스냅샷 일부 구현·검수; 명시적 모델 목록 조회는 계약 범위의 패키지/전환/브라우저/GitHub 검수 완료; task/agent 고정·대화 연결 시험 미구현 |
| 모델 장애 전환 | retry policy·profile pool·health circuit·reset | 제한된 호출 시간/실패 기록 연결됨; 여러 모델의 장애 전환 미구현 |
| 사용량·모델 호출 기록 | 일별/대화별/모델별 집계·원문 호출 기록 | 호출 시도/실제 usage·누락 구분·가격 당시 추정 연결됨; 제공자 원문·실제 청구 관리 미구현 |
| 도구 호출 기록 | commands 목록·도구별 집계 | Worker 실행 과정·감사 연결됨; 범용 셸 명령 기록 미구현 |
| 작업 파일 워크스페이스 | 목록·읽기/쓰기·디렉터리·업로드/다운로드·삭제 | 지속 노트 연결됨; 서버 파일 관리자 미구현 |

읽기 위치:
[도구 카탈로그](https://github.com/Autumn-27/ARTEX/blob/b55ceb1fdd84a813d77de09a06af83d323a81f85/agent/toolcatalog.go),
[사용자 도구](https://github.com/Autumn-27/ARTEX/blob/b55ceb1fdd84a813d77de09a06af83d323a81f85/server/customtool.go),
[플랫폼 도구](https://github.com/Autumn-27/ARTEX/blob/b55ceb1fdd84a813d77de09a06af83d323a81f85/server/platform_tools.go),
[모델 풀](https://github.com/Autumn-27/ARTEX/blob/b55ceb1fdd84a813d77de09a06af83d323a81f85/server/llmpool.go),
[별도 질문](https://github.com/Autumn-27/ARTEX/blob/b55ceb1fdd84a813d77de09a06af83d323a81f85/server/side_questions.go).

## 승인·알림·운영

| 기능군 | 원본에서 확인한 구성 | OpenAegis 상태·다음 조건 |
|---|---|---|
| 승인 규칙·기록·실행 상세 | global/task intercept rules, pending decide, history/execution | 범위/도구/버전의 작업 승인·감사 연결됨; 도구 호출별 사용자 규칙 미구현 |
| 자산 차단 규칙 | 도메인·IP·URL·CIDR 관리 | 각 요청의 URL 범위/DNS/IP·redirect 검사 연결됨; 전역 사용자 차단 규칙 UI 미구현 |
| 모델 승인 판단 | judge 구성·usage·검토 맥락 | 미구현; 현재 승인자는 관리자 |
| 알림 채널·필터 | 여러 채널 인스턴스·종류·설정 마스킹·필터·속도 | 일부 구현; 고정 webhook 수신처·관리자 승인·버전/상태 필터·DB 간격·비활성 테스트·마스킹·SQL/URL·충돌 검토([계약](NOTIFICATIONS.md)); 이메일/전용 어댑터·임의 이벤트 필터는 남아 있음 |
| 알림 배달·수동 재전송 | deliveries, attempts/state, retry | 일부 구현; 원자적 이벤트/커서/전송 이력·시도 영수증·미확인 복구·최대3회 수동 재전송·응답 손실 중복 방지·SQL/URL; 설치본93→89→93·두 저장소 백업 복구 검수; 장시간 운영 검수는 남아 있음 |
| 인증·관리 설정 | setup/login/password, JWT, settings | 초기 관리자·서버 세션·admin/operator/viewer·세션 폐기 연결됨 |
| 로그·활동·감사·정리 | 현재/과거/stream 로그·활동 SSE·audit·gc | DB 활동·SSE 재연결·감사 연결 검증·체크포인트·제한된 보존 CLI 연결됨; 외부 감사 보관 자동화 남음 |
| 웹 검색·프록시 설정 | 설정/연결 테스트·전역 프록시 | 미구현; 범위 외 검색을 검증 요청으로 취급하지 않음 |
| 설치·데이터 저장 | PostgreSQL·Docker/Compose·내장 웹 바이너리 | SQLite/네이티브 PG·wheel·외부 웹 빌드·실제 Linux 이미지/Compose 검증 연결됨; 전체 운영/플랫폼 검수 남음 |
| 갱신·복구 | 업데이트 확인/적용/stream·checksum·smoke·rollback | Ed25519 릴리스 검증·백업/복구·호환 점검·설치 전환 리허설 연결됨; 자동 UI 업데이트 미구현 |

읽기 위치:
[승인 시스템](https://github.com/Autumn-27/ARTEX/blob/b55ceb1fdd84a813d77de09a06af83d323a81f85/server/intercept.go),
[알림 API](https://github.com/Autumn-27/ARTEX/blob/b55ceb1fdd84a813d77de09a06af83d323a81f85/server/notify_api.go),
[갱신](https://github.com/Autumn-27/ARTEX/blob/b55ceb1fdd84a813d77de09a06af83d323a81f85/server/update.go).

## 구현 순서와 완료 판정

먼저 기존 기능의 공백인 확장 도구의
입력/결과 계약과 실제 격리를 닫는다. 이어 작업 템플릿·분류·알림 배달 이력처럼
현재 업무 흐름을 개선하는 기능을 연결한다. 모델 프로필·장애 전환·프롬프트 버전은
호출 당시 구성과 비용의 추적성을 보존해야 한다. 아카이브·트래픽·자동 자산 보강은
증거 참조 보존, 승인 범위, 자원·개인정보 보존 정책까지 함께 검증한다.

모든 기능군을 추적하되 승인된 방어 검증이라는 제품 범위를 유지한다. 현재 범위에서
제외한 임의 셸/자율 악용 체인은 [기능 비교](FEATURES.md)의 명시적 항목이다.
원본의 코드·프롬프트·skills를 MIT 프로젝트에 복사하지 않는다. 이 목록은 기능과
공개 인터페이스를 기록한 독립 분석이며 원본 코드의 라이선스를 변경하지 않는다.
