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
탐색은 하지 않는다. 규칙의 재현 테스트 내보내기와 전용 시각 편집기는 후속 작업이다.
