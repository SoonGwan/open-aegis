# API 응답·소유권 정책

자산의 ‘API 권한 규칙 설정’ JSON에 GET 경로·테스트 역할·예상 허용 여부를 정의한다.
기존 상태 코드 비교에 선택적인 `response_schema`와 `ownership`을 추가한다.
작업의 승인 범위 스냅샷에 정책을 포함하며 변경 후에는 기존 승인을 재사용할 수 없다.
자산 가져오기·수정도 같은 서버 검증을 사용한다. 요청 경로는 기존 자산 범위 안이어야
하며 쿼리·fragment와 임의 인증 헤더는 허용하지 않는다.

```json
[
  {
    "path": "/api/account",
    "role": "customer-a-test",
    "expected_allowed": true,
    "credential_env": "AEGIS_TEST_CUSTOMER_A",
    "response_schema": {
      "type": "object",
      "required": ["tenant_id", "items"],
      "properties": {
        "tenant_id": {"type": "string"},
        "items": {"type": "array", "items": {"type": "integer"}}
      }
    },
    "ownership": {"pointer": "/tenant_id", "expected": "synthetic-customer-a"}
  }
]
```

인증 값은 서버의 `AEGIS_TEST_*` 환경변수에서 실행 시 읽는다. 규칙에는 변수 이름만
저장한다. role은 운영자가 붙인 설명이며 자격증명이 실제로 그 역할인지 증명하지 않는다.
소유권 비교는 운영자가 지정한 JSON 필드와 기대 문자열의 정확한 비교다. 문자열
소유자·고객사·리소스 ID에 사용할 수 있다. 비밀번호나 토큰을 expected에 넣지 않는다.
기대 값과 스키마는 자산·작업·보고서에 포함될 수 있지만 실제 응답 값은 보존하지 않는다.

## 지원 스키마

[JSON Schema 2020-12](https://json-schema.org/understanding-json-schema/reference/object)의
아래 부분집합을 [jsonschema Draft202012Validator](https://python-jsonschema.readthedocs.io/en/stable/validate/)
로 검사한다. 전체 JSON Schema 언어 지원을 뜻하지 않는다. 모르는 키워드는 무시하지
않고 등록 시 거절한다. 규칙·소유권 객체의 오타나 추가 필드도 거절한다.

| 지원 키워드 | 제한 |
|---|---|
| type, properties, required | 중첩 스키마 최대 8단계, 각 properties 최대 64개 |
| additionalProperties | true/false만 지원 |
| items | 단일 객체 스키마만 지원 |
| enum, const | JSON 스칼라만 지원, enum 최대 32개 |
| minimum, maximum, exclusiveMinimum, exclusiveMaximum | JSON Schema의 숫자 비교 |
| minLength, maxLength, minItems, maxItems, minProperties, maxProperties | JSON Schema의 길이·개수 비교 |

스키마 전체는 UTF-8 JSON 16 KiB, 구조 검사 512노드·16단계 이하로 제한한다.
`$ref`, `$schema`, `$defs`, 정규식, 조합 스키마, format, uniqueItems 등은 지원하지
않는다. 스키마에서 원격 주소를 조회하지 않는다. 숫자는 유한해야 한다.

ownership.pointer는 JSON Pointer의 `/`·`~0`·`~1`과 배열 번호를 사용한다.
예를 들어 `/accounts/0/tenant_id`는 첫 계정의 tenant_id다. 최대 256자·16단계이며
빈 루트 포인터, 잘못된 escape, 배열의 선행 0 번호는 거절한다. expected는 1–200자의
문자열이다. 실제 값이 다른 형식이면 문자열 비교 불일치로 판정한다.

## 판정

| 응답·정책 | 결과 |
|---|---|
| 401/403, 예상 거절 | 완료, 불일치 없음. 응답 본문 계약은 검사하지 않음 |
| 401/403, 예상 허용 | 기존 권한 불일치(medium) |
| 2xx, 예상 허용, 스키마 불일치 | 응답 계약 불일치(medium), 소유권 비교는 생략 |
| 2xx, 스키마 일치, 소유권 값 불일치 | 소유권 필드 불일치(high) |
| 2xx, 예상 거절, 스키마 일치 | 기존 권한 불일치(high) |
| 2xx, 예상 거절, 스키마 불일치 | 보호 데이터 응답인지 확인하지 못했으므로 판정 불가 |
| 2xx, 본문 계약 설정, HTML/잘림/잘못된 JSON/없는 소유권 경로 | 판정 불가 |
| 429/5xx 또는 2xx·401·403 이외 | 기존 규칙대로 판정 불가 |

옵션이 없으면 기존 HTTP 상태 비교를 유지한다. 본문 계약은 완전한 UTF-8 JSON과
application/json 또는 application/*+json에만 적용한다. 본문 최대 128 KiB, JSON
최대 10,000노드·32단계이며 중복 키·NaN·Infinity·비유한 수·잘못된 UTF-8을 거절한다.
파싱과 스키마 검사 중 CPU를 강제 선점하는 별도 시간 제한은 없다. 기존 작업·요청
deadline과 크기·구조 상한을 함께 사용하며 대규모 부하 보장은 별도 검증이 필요하다.

판정 불가는 해당 검증 커버리지를 failed로 기록하며 해결/통과로 처리하지 않는다.
한 도구 내 여러 규칙 중 하나가 판정 불가이면 도구 전체가 완료되지 않는다. 현재
도구 실행은 오류 전 부분 발견을 저장하지 않는다. HTTP 요청 메타데이터·본문 해시는
남지만 원문은 남지 않는다. 스키마 증거에는 최대 첫 16개 오류의 키워드 종류만 저장하고
오류 메시지·응답 필드 경로·실제 값은 저장하지 않는다. 소유권 증거에는 일치 여부만 남긴다.

이 결과는 운영자가 정의한 응답 계약의 불일치다. 실제 고객사 권한·유출·DB 소유권을
독립적으로 증명하지 않는다. 쓰기 요청, 다른 사용자의 자격증명 수집, 자율 리소스 ID
탐색은 하지 않는다. 전용 시각 편집기는 후속 작업이다.

## 승인 정책 내보내기와 별도 재현

작업 상세의 ‘API 정책 재현’에서 ‘API 정책 JSON’을 누르거나,
로그인한 브라우저에서 `/api/tasks/<task_id>/policy-reproduction`을 열면
`aegis-api-policy.json`을 다운로드한다. 조회자도 기존 보고서처럼 읽을 수 있다.
승인 시각·실행 제한이 있고 API 권한 검증을 선택한 작업만 내보낼 수 있으며,
권한 규칙이 없는 자산은 파일에서 제외한다. 미승인 작업·규칙 없는 작업은 409다.
파일은 최대 8 MiB이며 자산 ID·revision·주소·규칙·승인 시각·실행 제한을 포함한다.
작업 이름·목표·노트·HTTP 응답·실제 인증 값은 포함하지 않는다. source_version은
내보내는 앱의 버전이며 원본 작업을 실행한 엔진 버전을 증명하지 않는다.

같은 Python 서비스 패키지를 설치한 환경에서 실행한다. 명령이 없으면 `start.sh`의
패키지 설치 단계 또는 `pip install .`로 갱신한다. 저장소에서는 아래 모듈/스크립트
진입점도 사용할 수 있다.

```sh
aegis-replay-policy --source aegis-api-policy.json
# 저장소에서 같은 파일 검사:
.venv/bin/python scripts/replay_policy.py --source aegis-api-policy.json
```

기본 동작은 파일의 형식·스키마·경로 범위·실행 제한 검사다. DNS 조회나 대상 요청은
보내지 않으며 인증 환경변수가 없어도 검사할 수 있다. 현재 대상과 테스트 계정의
검증 권한을 확인하고 필요한 AEGIS_TEST_* 환경변수를 설정한 뒤 명시적으로 실행한다.

```sh
aegis-replay-policy --source aegis-api-policy.json --run
# 자신이 운영하는 격리된 loopback/사설 실습 대상에만:
aegis-replay-policy --source aegis-api-policy.json --run --lab
```

파일은 서명되지 않는다. approved_at은 원본 작업의 메타데이터일 뿐, 파일의 진위나
현재 실행 권한을 증명하지 않는다. 파일을 수정하면 다른 정책이 되며 자산 보관·revision
변경·계정 폐기는 재현 CLI에 자동 동기화되지 않는다. 따라서 이전 서버 승인을 현재
대상에 대한 새 권한으로 간주하지 않는다. CLI는 서버 DB·커버리지·발견·감사 로그를
수정하지 않는다. 결과 JSON은 별도 실행의 결과이며 원본 작업 상태는 그대로다.

실행은 원본 엔진과 같은 기본 GET 응답 검사·API 권한 검증·본문 정책 비교를 사용한다.
나머지 다섯 도구나 AI Planner는 실행하지 않는다. 자산을 순서대로 실행하고 주소·
리다이렉트 범위를 확인하며 DNS 고정·TLS·예약 주소 차단을 사용한다. lab도 메타데이터
주소 차단은 유지한다. 원본 승인 제한과 현재 AEGIS_* 실행 환경변수 중 더 엄격한
속도·시간·예산·재시도 한도를 사용한다. 재시도 대기는 더 긴 쪽, 동시 요청은 1이다.
요청 예산은 자산별이며 전체 재현 실행은 하나의 작업 deadline을 공유한다.

종료 코드는 모두 일치하면 0, 불일치/판정 불가가 하나라도 있으면 1, 파일·전체 실행 정책 설정 오류는
2, 사용자 중지는 130이다. stdout JSON에는 자산 ID·결과·발견 코드·심각도·요청 건수·
적용 제한만 남긴다. 예외 메시지·인증 값·응답 값은 출력하지 않는다. 필드 오타,
중복 JSON 키, 지원하지 않는 파일 format과 범위 밖 규칙은 요청 전에 거절한다.
테스트 계정 환경변수가 없으면 해당 자산은 판정 불가(1)다.
타깃 상태·DNS·인증 환경·패키지 버전이 달라질 수 있으므로 원본의 동일 응답을 보장하지
않는다. 서명·장시간 부하·독립 실행 로그 보관과 전용 정책 편집기는 후속 작업이다.

화면은 미승인·API 도구 미선택·규칙 없음·이전 실행 제한 없음의 이유를 보여주고
다운로드를 비활성화한다. 최종 자격 검사는 서버에서 수행하며 서버 오류는 파일로
저장하지 않는다. 진행·중단·오류·수동 재시도는 보고서 다운로드와 같은 처리를 사용한다.
성공 안내는 브라우저 다운로드가 시작됐다는 뜻이며 디스크 저장 완료를 증명하지 않는다.
