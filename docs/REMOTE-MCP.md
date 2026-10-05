# 원격 MCP 클라이언트 기반

`aegis.remote_mcp.Client`는 동기식 Streamable HTTP 클라이언트 라이브러리다.
앱 API·UI·Planner·Worker에 외부 실행 경로를 추가하지 않는다. 신뢰된 호출자가
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

관리자 검토 등록·도구별 입력/결과 계약·역할 권한·승인/감사 저장·실행 프로세스 격리와
허용된 네트워크 범위 강제가 남아 있다. 메타데이터 지문은 호환성 검사이며 원격 서버의
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
