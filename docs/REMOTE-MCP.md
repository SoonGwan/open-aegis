# 원격 MCP 클라이언트 기반

`aegis.remote_mcp.Client`는 동기식 Streamable HTTP 클라이언트 라이브러리다.
앱의 관리자 API·UI에는 목록 검토와 메타데이터 등록만 연결했다. Planner·Worker에
외부 실행 경로를 추가하지 않는다. 신뢰된 호출자가
연결 설정과 도구 정의·정확한 입력을 검토하는 기반이며, 서비스의 사용자 승인이나
역할 권한을 대신하지 않는다. **원격 MCP v1 출시 조건은 미완료다.**

## 연결과 호출 계약

`Connection`은 고정 MCP endpoint, 연결 ID, 선택적 Bearer token 환경변수 이름을
받는다. HTTPS와 기본 CA/호스트 검증을 사용한다. 주소의 인증정보·query·fragment·제어
문자를 거절한다. 매 요청마다 DNS의 모든 주소를 검증하고 선택한 IP에 연결하며,
리다이렉트를 따르지 않는다. 사설망은 명시적 `allow_private` 설정이 필요하다.
HTTP는 `allow_private=true`, `lab_http=true`인 숫자 loopback 실습만 허용한다.
환경변수 인증정보는 호출할 때 다시 읽으며 원문을 예외에 넣지 않는다.

`initialize()`는 지원 버전 2025-11-25, 2025-06-18, 2025-03-26 중 서버가 선택한
버전을 검사하고 초기화 알림을 보낸다. 이후 요청은 협상 버전과 발급된 session ID를
전달한다. `list_tools()`는 cursor를 따라 최대 10페이지·100개 도구를 조회하고
중복 이름·반복 cursor·잘못된 입력 스키마를 거절한다. 반환 정의는 복사본이다.

신뢰된 호출자는 목록을 검토한 후 `approve_call(name, arguments)`로 일회용 grant를
발급한다. `call_tool(name, arguments, grant)`는 정확한 입력을 복사하고 도구 목록을
다시 조회해 승인 당시 연결·인증 지문·세션·프로토콜·서버 정보·전체 도구 정의·입력을
비교한다. 변경되면 도구 호출 전에 거절한다. 서버의 `readOnlyHint`는 실행 승인이
아니다. 각 grant는 호출 전 소비하며, 오류 응답·연결 실패 후 자동 재시도하지 않는다.
목록 변경 알림은 기존 grant를 폐기한다. 인증 회전·세션 상실은 재초기화와 새 검토가
필요하다. `close()`는 발급된 세션의 DELETE를 시도하고 로컬 상태를 폐기한다.

JSON 응답과 POST SSE를 처리한다. SSE의 UTF-8 BOM, LF/CRLF/CR, 주석·빈 priming
event·여러 data 줄을 처리하고 해당 요청 ID의 응답만 받는다. 서버가 보내는 내용은
명령으로 실행하지 않는다. 서버 발신 요청은 거절하며 roots·sampling·elicitation
권한을 광고하지 않는다. JSON-RPC 오류는 고정 오류 코드만 노출한다. 도구 결과의
`isError=true`는 그대로 반환하므로 호출자가 성공으로 처리하면 안 된다.

## 자원과 스키마 한도

작업 admission 대기와 DNS·헤더·본문 전송을 합쳐 기본 12초 deadline을 사용하며,
외부 `TaskControl`의 더 짧은 deadline과 중지를 따른다. 한 POST 응답/SSE 전체와
합친 도구 메타데이터는 각각 512 KiB, 입력은 64 KiB다. JSON은 깊이 16·노드 4096,
동시에 보관할 grant는 최대 16개다. 압축 응답·중복 JSON 키·비유한 수를 거절한다.

입력 스키마는 object 및 JSON Schema 2020-12로 검사한다. 외부 참조·`$id`·동적 참조는
거절하며 로컬 JSON pointer 참조만 허용한다. 참조를 펼친 깊이/노드 예산과 순환을
검사한다. 모든 JSON Schema 기능과 모든 MCP 서버에 대한 호환을 보장하지 않는다.
네트워크 deadline이 Python JSON/스키마 처리의 CPU 시간이나 OS 메모리 하드 제한을
보장하지는 않는다. 반환 content의 기본 구조를 검사하지만 외부 도구별 outputSchema·
출처·증거·스코프 검증은 제품 통합 단계에서 추가해야 한다.

## 남은 출시 조건

별도 [서명된 GET 실행 서버](MCP-EXECUTION.md)는 신뢰한 승인 스냅샷의 범위와
요청 제한을 서버에서 검사하고 일회용 권한을 영속 소비한다. 기존 내장 검사 6개의
전체 결과를 검증하는 초기 어댑터다. 메인 작업 승인·Worker·저장 및 일반 플러그인
실행/격리와 실제 운영 호환은 아직 미완료다.

관리자 메타데이터 검토·등록·비활성화와 해당 감사 저장은 구현했다. 도구별 실행
입력/결과 계약·실행 역할 권한·작업 승인/감사·실행 프로세스 격리와 허용된 네트워크
범위 강제가 남아 있다. 메타데이터 지문은 호환성 검사이며 원격 서버의
구현이나 실제 부작용을 증명하지 않는다. 승인한 `url` 입력도 서버의 outbound 동작을
제한하지 않는다. 도구 결과에 민감한 데이터가 올 수 있으며 이 라이브러리는 이를
자동 저장하거나 사용자에게 공개하지 않는다.

OAuth 흐름, legacy HTTP+SSE, GET 구독·끊긴 SSE 재개, 서버 요청 처리, 서버 취소
알림은 아직 지원하지 않는다. 네트워크 중지/시간 초과는 **원격 실행 중단의 증거가
아니다**. 실행 여부가 불명확한 실패를 재승인할 때는 서버 측 상태를 먼저 확인해야 한다.
실제 제3자 서버 호환·운영 권한·격리 검수가 끝나기 전 제품 실행 경로에 연결하지 않는다.

계약 기준은 공식 [전송 규격](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports),
[수명 주기](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle),
[도구 규격](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)이다.
테스트는 직접 띄운 loopback HTTP/HTTPS 서버만 사용한다.

## 관리자 검토·등록 서비스

서버 운영자가 `AEGIS_MCP_CONNECTIONS`에 최대 10개의 고정 연결을 설정하고 서버를
재시작한다. 토큰 원문은 JSON 설정에 넣지 않고 선택한 환경변수에 둔다. 예:

```sh
AEGIS_MCP_CONNECTIONS='[{"id":"team-mcp","url":"https://mcp.example/mcp","token_env":"TEAM_MCP_TOKEN"}]'
TEAM_MCP_TOKEN='…'
```

관리자 **시스템 설정 → 원격 MCP 도구 등록**에서 연결을 명시적으로 선택하고
도구 정의를 펼쳐 검토한다. 도구 선택을 바꾸면 검토 확인은 해제된다. 선택한 도구
등록은 실제 검증 실행 승인이 아니다. 현재 `execution_available=false`인 도구만
등록되며 내장 도구 목록·작업·커버리지에는 합쳐지지 않는다.

| 관리자 API | 계약 |
|---|---|
| `GET /api/integrations/mcp/connections` | 설정된 연결 주소·인증 설정 유무; 토큰과 환경변수 이름은 반환하지 않음 |
| `POST /api/integrations/mcp/previews` | `connection_id`의 목록을 실제 조회하고 15분 검토 기록 생성 |
| `POST /api/integrations/mcp/previews/{id}/register` | `selected` 도구 이름과 `reviewed=true`; 만든 관리자만 반영 |
| `GET /api/integrations/mcp/tools` | 정의를 SQL에서 제외한 요약 페이지; limit 기본 25/최대 100, offset 최대 10,000,000 |
| `GET /api/integrations/mcp/tools/{id}` | 등록된 도구의 저장 정의·프로토콜·서버 정보 |
| `POST /api/integrations/mcp/tools/{id}/disable` | 현재 정수 `revision` 대조 후 비활성화 |

비로그인·운영자·조회자는 이 경로를 사용할 수 없다. 등록 직전에 새 프로세스로 목록을
조회하고 전체 카탈로그 지문과 연결/인증 지문을 대조한다. 검토 시점의 도구 등록
revision도 비교하므로 중간 등록·비활성화를 오래된 검토로 덮어쓰지 않는다.
등록된 선택과 검토 반영 결과·해당 감사 이벤트는 동일한 SQLite/PostgreSQL 트랜잭션으로
저장한다. 감사 실패 시 모두 롤백한다. 같은 검토/선택의 반영 재시도는 원래 영수증을
반환하며 추가 원격 요청이나 도구 재활성화를 하지 않는다. 선택을 바꾸면 새 검토가 필요하다.
이미 반영한 영수증과 도구의 현재 상태는 구분하며, 현재 상태는 목록/상세로 확인한다.

열린 검토 기록은 최대 20개, 등록 도구는 연결별 누적 최대 100개다. 새 검토 생성 시
만료 기록을 삭제한다. 도구가 서버 목록에서 사라져도 자동 삭제·비활성화하지 않는다.
앱 재시작은 저장된 등록을 읽으며 목록 조회나 도구 실행을 자동으로 시작하지 않는다.
정의는 서버가 제공한 신뢰할 수 없는 텍스트이며 링크·명령을 실행하지 않는다.
원격 설명/스키마에 포함된 미확인 민감정보까지 자동 식별한다는 보장은 없다.

### 조회 프로세스의 경계

서비스의 목록 조회는 고정 클라이언트 코드를 POSIX 자식 프로세스로 실행한다.
앱의 전체 환경변수를 상속하지 않고 선택한 인증 변수와 최소 OS/CA 환경만 전달한다.
임시 작업 디렉터리·입력/출력 파일을 사용하고 종료·실패·중지 후 프로세스를 회수한다.
부모의 15초 실행 제한, 자식 CPU 5초·출력 파일 512 KiB·FD 64 제한을 설정한다.
Linux에는 가상 주소 공간 512 MiB 제한도 설정한다. macOS의 RSS 하드 제한은 없다.
한 워크스페이스의 목록 조회/등록 검토는 동시에 하나만 허용한다.

도구 `_meta`는 비신뢰 정의와 함께 검토용으로 보존한다. 실행 서버의 계약 정보를
확인할 수 있지만 이 필드만으로 실행 권한을 부여하지 않는다.
세션 ID·인증 원문·서버 instructions·미지원 메타데이터 필드는 저장하지 않는다.
선택한 인증 원문이 설명/스키마에 반사되면 전체 조회를 거절한다. stdout에는 검토할
카탈로그만 반환하며 오류 stderr를 API에 노출하지 않는다. 조회는 initialize,
initialized, tools/list, 세션 DELETE만 사용하고 tools/call은 보내지 않는다.

이 자식 프로세스는 고정 클라이언트의 조회/파싱 자원 경계이며 임의 플러그인의
파일시스템·네트워크 sandbox가 아니다. DNS/TLS/고정 endpoint 제한은 기존 전송
코드가 검사한다. 원격 서버의 outbound 활동까지 OS에서 격리하는 기능은 미완료다.
현재 검증은 실제 macOS 자식 프로세스와 소유한 HTTP/HTTPS 서버, SQLite 및 실제
임시 PostgreSQL에 한정한다. Linux 제한의 실제 운영 검수·전체 모바일/스크린리더
여정·사용자 실행 승인 통합은 남아 있다.
