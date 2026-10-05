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

aegis-release create --wheel dist/open_aegis-0.2.0a1-py3-none-any.whl \
  --web web/dist --lock requirements.lock --output release-0.2.0a1 \
  --private-key rehearsal-private.pem --revision FULL_SOURCE_COMMIT_SHA

aegis-release verify --bundle release-0.2.0a1 --public-key rehearsal-public.pem
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
aegis-release prepare --backend sqlite --bundle release-0.2.0a1 --public-key rehearsal-public.pem \
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
aegis-release create --wheel dist/open_aegis-0.2.0a1-py3-none-any.whl \
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

## 서로 다른 버전·UI·설정 전환과 시작 실패 리허설

현재 로컬 후보는0.2.0a1이며 v1 완료/공식 배포를 뜻하지 않는다.
`scripts/review_release_transition.py`는 서로 다른 wheel을 checkout 밖의 두 독립
가상환경에 설치하고, 각 설치본의 자체 제작 CLI로 해당 버전의 번들을 서명한다.
새 검증기로 두 번들의 payload를 확인한 뒤 실제 HTTP/MCP가 설치 버전을 보고하는지
검사한다. 임시 키는 서명 후 제거하며 공식 신원/키 배포를 검증하지 않는다.

이전 UI는 빌드 교체 전에 별도 디렉터리에 보존한다. `--old-web-dir`를 생략하면
같은 UI 입력을 사용하므로 UI 변경 검수라고 부르지 않는다. 현재 리허설은 다른 JS
payload를 가진 이전/후보 UI를 각각 서명하고 HTTP index/JS/CSS의 실제 내용을 비교했다.
후보의 변경은 버전 미조회 시 잘못된0.1.0 표시를 제거하고 실제 서버 버전을 표시하는
작은 수정이며, 임의 UI/API 변경의 일반적 호환성이나 전체 브라우저 여정을 보장하지 않는다.

```sh
.venv/bin/python scripts/review_release_transition.py --backend postgres \
  --old-wheel artifacts/postgres-release-downgrade-wheel/open_aegis-0.1.0-py3-none-any.whl \
  --new-wheel artifacts/version-candidate-wheel/open_aegis-0.2.0a1-py3-none-any.whl \
  --old-web-dir artifacts/version-transition-old-web --web-dir web/dist \
  --runtime-lock requirements.lock --postgres-lock requirements-postgres.lock \
  --old-revision 10ded2b5e78b338aaad5def57a196693dd691783 \
  --new-revision 8bc19f2dde54f409de272264507f0e1aa65ac324
```

PostgreSQL 모드는 소유한0700 임시 Unix socket/신뢰 인증 클러스터를 시작하고 종료한다.
운영 DB에는 연결하지 않는다. SQLite는 `--backend sqlite`로 같은 절차를 사용하며
`--postgres-lock`/DB 서버 도구가 필요하지 않다. 두 모드 모두 이전 서버에서 만든
자산·승인 대기 작업·노트를 후보가 읽고 정상 기록하는지 확인한다. 계획은 실행하지 않는다.

이전 설정의 요청 예산24→후보12로 전환하고 기존 도구 계약의 승인 거절을 확인한다.
후보에서 만든 새 대기 계획은 같은 후보를 예산6으로 재시작한 후 정책 변경 사유로
승인을 거절한다. 복구할 때 이전 버전/UI/예산24를 선택한다. 이런 승인 차단은 변경
후 자동 실행을 허용하는 기능이 아니다. 현재 계약/범위/정책으로 새 계획을 검토한다.

실패는 원래 앱 startup에 진입하고 실제 notes 쓰기를 커밋한 뒤 준비 완료 전에
주입한다. 실패 프로세스가 비정상 종료하고 HTTP를 제공하지 않으며 SQLite 임대 또는
PG 실행 소유권을 해제한 것을 검사한다. 실제 실패 기록이 원본에 남아 있음을 확인한
뒤 이전 설치본의 restore CLI로 사전 백업을 복구한다. PG는 새 스키마로 복구하고,
원본 스키마의 이후 기록/원본 쿠키는 유지한다. SQLite는 복구 직전 DB를 별도 보존한다.

이전 프로세스/UI/설정으로 재시작해 이전 쿠키401, 원래 비밀번호 재로그인,
백업 시점 자산/계획/노트 유지와 후보 계획/노트·실패 기록 제거, 감사 연결과 정상
종료를 검증했다. 두 결과 모두 same_version=false, shared_ui_input=false,
target_requests=0이다. 현재 스키마는 양쪽 모두2이며 실제 다른 DB 스키마 이전을
검수한 것은 아니다. runtime/선택 PG 의존성 잠금은 공유한다. 깨지는 설정 변경,
자동 서비스 관리자 전환, 컨테이너/전원/원격 장애, 공식 키와 공개 배포, 전체 UI/부하
검수는 여전히 v1 조건으로 남아 있다. 입력 revision은 스크립트가 자동 증명하지 않으며,
이번 old/candidate wheel의57개 Python 파일은 해당 Git revision/실제 source와 별도로 대조했다.

## 작업 템플릿 후보의 버전 전환 검토

템플릿 후보(88개 서비스 파일)는 기존 저장 형식2에 새 record kind를 추가한다.
SQL 스키마 변경이나 새 환경변수는 없다. 후보와 이전87파일 alpha 모두 패키지
버전은0.2.0a1이므로 **버전 문자열만으로 아티팩트를 구별하지 않는다**. 검증한
소스 revision과 wheel/UI 해시를 함께 보존하고 기존 중지·백업·전환 순서를 따른다.

설치한 실제 wheel의 SQLite writer/reader 순서 `새 후보 작성 → 이전 wheel →
새 후보 재개`를 임시 워크스페이스에서 확인했다. 이전 wheel은 템플릿·버전 이력과
기존 작업의 원래 버전 참조를 보존하며 새 후보에서 현재 버전 적용을 재개할 수 있다.
그러나 **이전87파일 writer로 재계획하면 새 작업에 템플릿 출처가 빠진다**. 원래
작업과 `replan_of` 연결·템플릿 이력은 남지만, 새 후보 재개가 그 누락 필드를
자동 보충하지 않는다. 새 후보의 출처 유지 계약을 이전 writer까지 확장하지 않는다.

출처를 유지해야 하는 운영에서는 이전 코드로 확인하는 동안 작업 변경을 중지하고,
새 후보 writer를 재개한 후 재계획·재시도·후속 계획을 만든다. 이전 서버에 템플릿
API가 없으므로 후보 UI의 템플릿 흐름도 이전 서버와 함께 사용하지 않는다.
가장 마지막으로 출처가 온전히 유지되는 상태는 이전 writer가 파생 계획을 쓰기
전이다. 이는 조건부 코드 전환 검토이며 데이터 복구 증명이 아니다. PostgreSQL의
두 버전 전환과 운영 백업/복원은 이 SQLite 검토에서 실행하지 않았다.

### Task-category old/new writer pairing

The category candidate uses the existing records schema. Installed SQLite pairing
(89-file category writer → previous 88-file template writer → category writer)
preserves original category records, versions, membership history, operation receipts
and original task references; audit integrity stays valid and no target request occurs.

The old writer lacks the category API and omits classification on a newly derived
replan. Returning to the current writer does not rewrite that existing child: repeated
replan still returns the same pending child through the existing duplicate guard.
An explicit current-version classification of that child works, and a subsequent new
replan inherits the newly reviewed category with a fresh membership revision and origin.
Rollback is therefore conditional on avoiding old-version derived-plan writes when
complete classification provenance is required. This pairing covers SQLite only; it
is not a native PostgreSQL version-pair or backup/restore receipt.
