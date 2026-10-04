# 서명된 릴리스와 오프라인 업데이트 사전 점검

`aegis-release`는 wheel·빌드된 UI·runtime 잠금 파일의 SHA-256 목록을 Ed25519로
서명하고 검증한다. 별도로 신뢰한 공개 키를 명시해야 하며 릴리스 안의 키를 자동으로
신뢰하지 않는다. 서명은 해당 키의 소유자가 파일 목록에 서명했다는 증거다.
코드의 안전성·실제 CI 통과·최신 버전·공식 배포자 신원을 독립적으로 증명하지 않는다.

Linux/macOS의 OpenSSL 3.x와 Python 3.11 이상이 필요하다. 이 구현은 OpenSSL의
[`pkeyutl -sign/-verify -rawin` 계약](https://docs.openssl.org/3.6/man1/openssl-pkeyutl/)
및 [Ed25519 키 생성 명령](https://docs.openssl.org/3.6/man1/openssl-genpkey/)을 사용한다.
기존 서버 실행에는 OpenSSL CLI가 필요하지 않으며 서명/검증 명령에서만 사용한다.
서명 키의 배포·보관·회전과 공식 공개 키 전달 채널은 운영자가 별도로 준비해야 한다.

## 제작과 검증

아래는 로컬 리허설용 키 생성이다. 공개 배포용 키는 리허설 키와 구분하고,
암호화/오프라인 보관 정책을 정한다. 현재 CLI는 로컬 비대화형 PEM 키만 지원한다.

```sh
umask 077
openssl genpkey -algorithm ED25519 -out rehearsal-private.pem
openssl pkey -in rehearsal-private.pem -pubout -out rehearsal-public.pem

aegis-release create --wheel dist/open_aegis-0.1.0-py3-none-any.whl \
  --web web/dist --lock requirements.lock --output release-0.1.0 \
  --private-key rehearsal-private.pem --revision FULL_SOURCE_COMMIT_SHA

aegis-release verify --bundle release-0.1.0 --public-key rehearsal-public.pem
```

wheel은 `open-aegis`, 현재 제작 도구와 같은 버전, Python >=3.11 메타데이터가 필요하다.
`--revision`은 검증한 소스의 전체 40자리 Git SHA를 입력한다. 도구가 그 SHA의 코드와
wheel의 동일성을 자동 증명하지 않으므로 빌드·소스 대조·설치 리허설을 먼저 수행한다.
출력 경로는 새 디렉터리여야 하며 UI 입력 디렉터리 밖이어야 한다.

출력은 `release.json`, 64바이트 `release.sig`, `runtime/` wheel, `web/` UI,
`requirements.lock`이다. manifest는 정규 JSON 바이트로 서명하며 서명 확인 후
전체 payload의 크기/해시를 검사한다. 경로 탈출·중복 키·심볼릭 링크·특수 파일,
변조·누락·서명에 없는 추가 파일을 거절한다. manifest는 256 KiB,
payload는 파일당 2 GiB·최대 10,000개 제한이다. 신뢰한 키의 지문도 확인한다.

검증 직후에도 제삼자가 수정할 수 있는 디렉터리를 설치 대상으로 사용하지 않는다.
검증 도구는 릴리스를 설치하거나 wheel 안의 코드를 실행하지 않는다. 의존성 잠금은
파일의 서명/해시를 확인하는 것이며 외부 패키지 전체의 공급망 안전성 검사가 아니다.

## 업데이트 전 중지·백업

현재 서버의 설치 환경·UI·설정·검증된 이전 릴리스를 따로 보존한다. 실행 작업을
정상 중지하고 서버를 종료한 뒤 수행한다. 실제 컨테이너/서비스 관리 명령은 배포
환경의 절차를 따르며 아래 도구가 자동 중지하지 않는다.

```sh
aegis-release prepare --backend sqlite --bundle release-0.1.0 --public-key rehearsal-public.pem \
  --database data/aegis.db --output before-update
```

서명·파일 검증 후 워크스페이스의 독점 임대를 획득한다. 사용 중인 서버, SQLite/
JSON/참조/감사 무결성 오류, 릴리스가 읽지 못하는 스키마, queued/running/stopping
작업이 있으면 거절한다. 새 출력 디렉터리에 `before-update.db`와 `preflight.json`을
저장하며 원본 DB를 업데이트하지 않는다. 백업은 실제 스키마·건수·감사 연결을 검증한다.
백업과 점검 기록은 0600, 출력 디렉터리는 0700이다. 백업에는 인증 해시와 세션이
있으므로 접근 권한과 보관 기간을 관리한다.

receipt의 `installed=false`는 사전 점검만 완료됐다는 뜻이다. 서명된 manifest 해시,
신뢰한 공개 키 지문, DB 경로, 백업 해시/크기·메타데이터·목표 쓰기 스키마를 기록한다.
서명된 receipt가 아니므로 신뢰한 로컬 위치에 보관하고 외부 변조를 독립 보장하지 않는다.
현재 제작 도구의 SQLite 계약은 읽기 0–2/쓰기 2이다. 두 backend의 사전 점검은
현재 스키마보다 낮은 쓰기 스키마를 선언한 릴리스도 거절한다. 읽기 범위에 포함돼
있다는 이유로 스키마 downgrade를 승인하지 않는다. PostgreSQL은 아래 format2 선언·
중지된 워크스페이스 사전 점검을 지원한다.
미래 스키마 마이그레이션과 실제 버전/설정 전환은 별도 구현/리허설이 필요하다.

## PostgreSQL 릴리스 선언과 업데이트 사전 점검

PostgreSQL용 번들은 선택 의존성 잠금 파일도 서명에 포함한다. `--postgres-lock`을
명시하면 manifest format2로 만들며, 현재 저장 형식 `aegis-postgres-storage-v1`의
읽기 스키마 범위2–2/쓰기2와 고정 잠금 경로 `requirements-postgres.lock`을 선언한다.
생략하면 기존 format1 SQLite 계약을 그대로 만든다. 새 검증기는 두 형식을 읽지만,
이전 format1 검증기는 새 format2를 지원하지 않는다. 기존 도구로 이 번들을 검증할
수 있다고 가정하지 않는다. 호환성 선언은 제작자의 주장으로 실제 runtime/소스 대조와
설치본 검수를 대신하지 않는다.

```sh
aegis-release create --wheel dist/open_aegis-0.1.0-py3-none-any.whl \
  --web web/dist --lock requirements.lock --postgres-lock requirements-postgres.lock \
  --output release-postgres --private-key rehearsal-private.pem --revision FULL_SOURCE_COMMIT_SHA

aegis-release verify --bundle release-postgres --public-key rehearsal-public.pem
# 실행 작업을 정리하고 PostgreSQL HTTP 서버를 종료한 뒤:
aegis-release prepare --backend postgres --schema aegis_workspace \
  --bundle release-postgres --public-key rehearsal-public.pem --output before-postgres-update
```

`AEGIS_POSTGRES_DSN` 환경변수와 선택 의존성이 필요하다. `prepare`의 backend는
`AEGIS_STORAGE_BACKEND`, schema는 `AEGIS_POSTGRES_SCHEMA`도 따른다. DSN을 CLI
인자로 전달하거나 receipt에 저장하지 않는다. PostgreSQL에서 SQLite `--database`
지정은 거절한다. SQLite는 명시적 `--database` 또는 `AEGIS_DATA_DIR/aegis.db`를 쓴다.
CLI는 `.env`를 자동으로 읽지 않는다. PostgreSQL 실패는 종료 코드2와 고정 메시지이며
DB/연결/비밀번호 원문을 출력하지 않는다.

서명·전체 payload 해시·format2의 명시적 PostgreSQL 호환성을 먼저 확인한다. 대상
워크스페이스의 exclusive transaction gate를 획득해 실행 소유자·허용된 진행 작업·
협력하는 쓰기를 배제하고, read-only 연결에서 저장 형식·테이블·감사·스키마 읽기
범위·현재보다 낮은 쓰기 스키마 거절과 queued/running/stopping 작업을 확인한다. 백업 자체는 별도 read-only
REPEATABLE READ snapshot에서 수행한다. gate를 유지한 채 백업까지 검증하며,
백업에 담긴 실제 작업 상태도 다시 확인한다. 관리자/raw SQL은 advisory 계약 밖이다.

0700 임시 공간에 `before-update.zip`과 `preflight.json`을 준비하고, DB 트랜잭션이
정상 종료된 뒤 새0700 출력 디렉터리에 두0600 파일을 공개한다. 출력이 이미 있거나
동시에 다른 생성자가 만든 경우 덮어쓰지 않는다. 공개 중 처리 가능한 실패는 해당
명령이 생성한 출력만 정리한다. 파일·디렉터리·부모 디렉터리를 fsync한다. 프로세스
강제 종료/전원 차단 중에는 부분 출력이 남을 수 있으므로 성공 종료와 두 파일의
검증을 확인한다. 기존 일반 digest 계약에 따라 사전 백업은2GiB 이하만 지원한다.

receipt에는 backend/schema, 릴리스 버전/revision/서명 키 지문/manifest digest,
백업 digest/메타데이터와 목표 쓰기 스키마, `installed=false`를 기록한다. 임시 경로와
DSN은 포함하지 않는다. 원본 데이터·원본 로그인은 유지한다. receipt는 서명된 결과가
아니므로 보호된 경로에 보관한다. 이 명령은 설치·스키마 마이그레이션·서버/설정 전환을
수행하지 않는다. 다른 schema/버전/설정의 업그레이드 호환성 검수는 아직 남아 있다.

실패 복구 리허설은 새 스키마에 사전 백업을 복구하고 이전 runtime/UI/설정으로
HTTP 로그인·기록·감사 연결을 검증한다. 복구본의 기존 세션은 무효화되며 원본
스키마는 그대로 남는다. 운영 전환은 검증한 schema 이름을 명시하고 별도로 수행한다.
전환 후의 쓰기는 자동 병합하지 않는다.

```sh
aegis-restore --backend postgres --source before-postgres-update/before-update.zip --check-only
aegis-restore --backend postgres --source before-postgres-update/before-update.zip --schema aegis_rollback
```

## 설치와 실패 복구

준비 후 새 격리된 설치 환경에서 잠긴 runtime 의존성/wheel·별도 UI를 설치한다.
서비스 시작 전에 이전 설치 환경을 보존하고, 인증·데이터·스키마·감사·UI·종료를
검수한다. 현재 도구는 프로세스 전환이나 자동 업데이트를 수행하지 않는다.

실패하면 새 서버를 먼저 종료한다. 원본 백업의 무결성을 확인한 뒤 기존 복구 CLI로
DB를 복원한다. 복구 시 세션이 무효화되고 복구 직전 DB도 별도 보존된다.

```sh
aegis-restore --backend sqlite --source before-update/before-update.db --destination data/aegis.db
```

그 후 검증된 이전 runtime·UI·설정을 사용해 서버를 시작한다. DB 백업만으로
프로그램/화면/환경변수가 복구되는 것은 아니다. 새 버전에서 저장한 데이터는 이전
백업 시점 이후의 변경이므로 복구 시 사라질 수 있다. 운영 업데이트는 사전 공지·
중지 구간과 데이터 보존 요구에 맞춰 계획해야 한다.

## 설치본 전환·시작 실패 리허설

`scripts/review_release_transition.py`는 다른 두 wheel을 체크아웃 밖의 독립된
가상환경에 설치한다. 각 wheel과 UI·잠금 파일을 임시 키로 서명/검증하고, 이전
서버에서 만든 합성 자산·승인 대기 작업·노트를 새 서버가 읽는지 실제 HTTP로
확인한다. 대상 URL에는 요청하지 않는다.

```sh
.venv/bin/python scripts/review_release_transition.py \
  --old-wheel artifacts/conversation-ai-wheel/open_aegis-0.1.0-py3-none-any.whl \
  --new-wheel artifacts/release-wheel/open_aegis-0.1.0-py3-none-any.whl \
  --web-dir web/dist --runtime-lock requirements.lock \
  --old-revision 4a0717e58eb250d07588454de9607f59b0835034 \
  --new-revision 809a88cf95ead0f4307a2bcb9bbee7544ff453a9
```

새 서버의 정상 시작/기록 후 종료도 확인한다. 그 다음 앱의 원래 startup과 DB
기록 후, 준비 완료 전에 합성 예외를 주입한다. 실패 프로세스의 종료·HTTP 미제공·
워크스페이스 잠금 해제를 확인하고 이전 설치본의 복구 CLI로 사전 백업을 복원한다.
보존된 이전 UI/설정과 프로세스로 재시작하여 이전 쿠키 거절, 비밀번호 재로그인,
백업 시점 기록 보존, 이후 정상 기록과 실패 시작 기록 제거, 감사 연결과 종료를 검사한다.
모든 설치·데이터·서명 키는 임시 공간에 있으며 기존 워크스페이스를 변경하지 않는다.

현재 확인한 두 wheel은 서로 다른 코드지만 **모두 버전 0.1.0·스키마 2**이며
같은 UI 입력·의존성 잠금·공통 설정을 사용한다. 이것은 실제 설치본/프로세스 전환과
시작 실패의 복구 근거다. 다른 버전/스키마의 마이그레이션, 설정 변경의 호환성,
UI 기능 변경의 호환성, 자동 서비스 관리자 전환을 검증한 것은 아니다.
revision 입력과 wheel 소스의 동일성도 이 스크립트가 자동 증명하지 않는다.
컨테이너/볼륨, 공식 키의 서명 릴리스·공개 배포와 이 나머지 검증은 v1 조건으로 남아 있다.
