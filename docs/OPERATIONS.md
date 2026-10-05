# 계정·백업·복구 운영

## 지원 구성

현재 Linux/macOS의 단일 서버 프로세스, 단일 공유 워크스페이스를 사용한다.
기본 저장소는 SQLite WAL이며 이 문서의 파일 백업/복구·스키마 업데이트·잠금 절차는
SQLite용이다. 명시적 PostgreSQL HTTP 선택은 [별도 저장소 계약](POSTGRES-STORAGE.md)을
따른다. PostgreSQL의 온라인 논리 백업/새 스키마 복구는 해당 문서의 명시적
`--backend postgres` 절차를 사용한다. 전체 운영 복구·업그레이드 검수는 진행 중이다.
CLI는 `AEGIS_STORAGE_BACKEND`도 따르므로 아래 SQLite 파일 절차에는 필요 시
`--backend sqlite`를 명시한다. Windows는 WSL/컨테이너를
사용한다. 다중 인스턴스·테넌트 분리 지원은 남아 있다.

## 사용자 권한

| 역할 | 조회·보고서 | 자산·계획·조치·중지 | 실행 승인 | 사용자 관리 |
|---|---|---|---|---|
| 조회자 | 가능 | 불가 | 불가 | 불가 |
| 운영자 | 가능 | 가능 | 불가 | 불가 |
| 관리자 | 가능 | 가능 | 가능 | 가능 |

최초 설치 시 사용자 이름(기본 admin)과 비밀번호를 지정한다. 사용자 관리는
관리자에게만 표시되며 API에서도 관리자 역할을 검사한다. 계정은 삭제 대신
비활성화하며 마지막 활성 관리자는 비활성화하거나 권한을 낮출 수 없다.
권한·상태·비밀번호 변경은 해당 사용자의 모든 세션을 폐기한다. 표시 이름만
바꾸거나 동일한 역할/상태를 저장하면 세션을 폐기하지 않는다.
사용자 수정 화면은 조회한 updated_at으로 동시 변경을 검사한다. 다른 관리자가
먼저 저장하면 409를 반환한다. API에서는 expected_updated_at을 보내 같은 검사를
사용할 수 있다.
모든 사용자는 자신의 비밀번호를 바꿀 수 있다. 변경 후 다시 로그인해야 한다.
브라우저의 API/보고서 요청은 시작 당시 세션 전환 번호를 기억한다. 로그인·초기
설정·로그아웃·비밀번호 변경 성공 또는 현재 401 만료 처리 후에는 이전 요청의
늦은 401로 새 세션을 만료시키지 않는다. 이전 요청 자체의 실패는 그대로 반환한다.
이 번호는 문서 안의 응답 순서 보호이며 서버 인증·쿠키·다른 탭의 세션 동기화를
대체하지 않는다. 세션 전환 뒤 도착한 GET 성공은 JSON 해석 전/후에 취소로 거절하며
요약/인증 상태 갱신은 이전 세션의 성공·오류를 반영하지 않는다. 비인증 화면으로
전환할 때 요약·설정·상세·편집 선택·오류/안내 상태를 정리한다. 보고서도 이전
세션의 성공·오류로 파일 저장이나 화면 오류를 만들지 않는다. POST/PATCH 등
이미 반영된 일반 변경의 완료 응답은 API에서 유지한다. 공용 작업 액션·등록 폼은
세션이 바뀐 이전 완료의 갱신·알림·모달 닫기·이동을 반영하지 않는다. 비인증
전환은 저장 잠금을 해제하고, 이전 요청의 종료 처리가 새 요청의 잠금을 풀지
않도록 요청별 소유권을 검사한다. 로그아웃은 인증 완료 후 비인증 화면으로
전환하며 로그아웃된 쿠키로 목록 갱신을 실행하지 않는다. 인증 변경은 예외로, 이전 세션의
성공 헤더가 늦게 도착해도 새 세션 번호를 바꾸지 않고 취소로 거절한다. 현재 인증
변경도 본문 해석 도중 다른 로그인으로 전환되면 이전 완료를 거절한다. 계정 관리
화면은 닫힌 화면의 저장 콜백/오류를 반영하지 않으며, 자기 계정의 역할·상태·암호
재설정 성공은 현재 세션을 즉시 만료 처리한다. 전체 컴포넌트의 변경 후 콜백·다른 탭
동기화와 실제 계정 전환 경합은 별도 검수 대상이다.
권한은 각 요청을 승인할 때 결정한다. 이미 승인된 진행 중 요청을 소급 취소하지 않는다.

## 스키마 마이그레이션

`PRAGMA user_version=2`를 사용한다. 버전 0·1 DB를 열기 전에 일관된 SQLite
backup으로 `.pre-schema2-<id>.db`를 만들고 트랜잭션으로 이전한다. 버전 0의
비밀번호 해시는 `admin` 계정으로 옮기고 이전 세션을 폐기한다. 버전 1의 계정·세션은
유지하며 기존 이벤트를 감사 해시 연결의 초기 기준으로 봉인한다. 버전 1 서버는
버전 2 DB를 열 수 없다. 이전 서버로 롤백하려면 변경 전 백업을 별도 경로에 복구해야
하며 업그레이드 후 기록은 그 백업에 없다. 현재 스키마는 다시 봉인하지 않는다.
자산·작업·발견·증거·기록은 유지한다. 더 최신 버전 DB는 변경 없이 거절한다.
마이그레이션이 실패하면 트랜잭션이 롤백되고 변경 전 백업을 보존한다.

자동 마이그레이션 백업은 원본과 같은 디렉터리에 있다. 이는 장비 장애 대비용
외부 백업을 대신하지 않는다. 데이터 파일/백업은 0600으로 생성되지만 부모
디렉터리와 디스크 암호화, 보관 위치는 운영 환경에서 관리한다.

## 일관된 온라인 백업

서버 실행 중 SQLite backup API로 복사한 뒤 무결성·스키마·JSON·참조를 확인한다.
버전 2 백업은 감사 로그 해시 연결도 검증하며 실패한 파일을 복구에 사용하지 않는다.
버전 0·1 백업도 지원하지만 감사 봉인은 서버에서 업그레이드한 뒤 제공한다.
백업에는 사용자 비밀번호 해시와 세션 해시가 포함된다. 같은 출력 파일을
덮어쓰지 않으며 백업본은 독립적인 DELETE journal 형식이다.

```sh
.venv/bin/python scripts/backup.py --source data/aegis.db --output backups/aegis-2026-10-03.db
.venv/bin/python scripts/restore.py --source backups/aegis-2026-10-03.db --check-only
```

`--check-only`는 원본·대상 파일을 수정하지 않는다. 백업의 생성 시각이나 완전성은
무결성 확인만으로 보장되지 않는다. 작업 수·기록 수와 기대한 시점을 확인한다.

## 설치 패키지·컨테이너의 유지보수 명령

패키지 설치 후에는 저장소 위치와 관계없이 `aegis-backup`, `aegis-restore`,
`aegis-verify-audit` 명령을 사용할 수 있다. `start.sh`로 설치한 로컬 환경에서는
`.venv/bin/` 아래에 있다. 기존 `python scripts/*.py` 진입점도 같은 구현을 호출한다.

Dockerfile은 패키지 설치 과정에서 유지보수 CLI들을 포함한다. 이미지 변경 후 재빌드해야
한다. 다음 절차는 명령의 사용 계약이며 Docker 볼륨에서의 실제 실행은 아직
검증하지 않았다. 설치 wheel의 명령은 별도 가상환경에서 검증했다.

온라인 백업은 쓰기 가능한 데이터 볼륨 안에 생성하고 호스트의 별도 위치로 복사한다.
아래 파일명은 예시이며 이미 존재하면 덮어쓰지 않는다.

```sh
docker compose exec -T aegis aegis-backup --source /app/data/aegis.db --output /app/data/backups/before-update.db
docker compose exec -T aegis aegis-restore --source /app/data/backups/before-update.db --check-only
mkdir -p backups
docker compose cp aegis:/app/data/backups/before-update.db backups/before-update.db
```

복구 전 서버를 중지하고 같은 볼륨을 사용하는 일회성 컨테이너에서 복구한다.
같은 데이터 디렉터리를 사용하는 다른 서버가 있으면 잠금으로 거절한다.
Compose에 필요한 `.env` 설정은 유지한다.

```sh
docker compose stop aegis
docker compose run --rm --no-deps aegis aegis-restore --source /app/data/backups/before-update.db --destination /app/data/aegis.db
docker compose run --rm --no-deps aegis aegis-verify-audit --source /app/data/aegis.db
docker compose up -d aegis
```

호스트 복사본과 볼륨 내부 복사본은 자동으로 동기화되지 않는다. 다른 장비/볼륨으로
복구할 때에는 백업을 먼저 해당 볼륨으로 전달해야 한다. 독립 저장소의 백업·감사
체크포인트 보관은 별도로 관리한다.

## 로컬 오프라인 복구

1. 서버를 정상 종료한다.
2. 백업을 `--check-only`로 확인한다.
3. 별도 데이터 디렉터리에서 먼저 복구하고 로그인·자산·기록을 확인한다.
4. 운영 경로로 복구하고 서버를 다시 시작한다.

```sh
.venv/bin/python scripts/restore.py --source backups/aegis-2026-10-03.db --destination recovery-test/aegis.db
AEGIS_DATA_DIR=recovery-test AEGIS_PORT=8791 .venv/bin/python -m aegis
# 위 서버에서 복구 상태를 확인하고 종료한 뒤:
.venv/bin/python scripts/restore.py --source backups/aegis-2026-10-03.db --destination data/aegis.db
```

실행 중인 서버가 있으면 `.server.lock`의 OS 잠금 때문에 복구를 거절한다.
파일이 남아 있어도 실행 중이라는 뜻은 아니다. 프로세스 종료 시 OS가 잠금을 해제한다.
이 잠금은 Open Aegis 프로세스 사이의 조정이다. 임의 SQLite 도구로 같은 DB에 쓰지 않는다.

대상 DB가 있으면 `.pre-restore-<id>.db`로 이전 상태를 보존한다. 복구본은 먼저
임시 DB에서 검증하고 세션을 지운다. journal을 DELETE로 확정하고 연결을 닫은 뒤
파일을 교체하고 디렉터리를 fsync한다. 모든 사용자는 새로 로그인해야 한다.
상태 검증 실패·미지원 스키마·실행 중 잠금은 대상 파일 교체 전에 거절한다.
기존 WAL 상태를 checkpoint하지 못하는 경우에도 복구를 거절한다.

로그인 문제나 기록 누락이 있으면 서버를 종료하고 `.pre-restore-<id>.db`로 같은
복구 명령을 실행해 이전 상태로 돌아간다. 이때도 기존 세션은 무효화된다.
버전 0 백업을 복구하면 다음 서버 시작에서 스키마 마이그레이션을 진행한다.

## 검증된 범위

설치 아티팩트의 유지보수 명령을 재현하려면 wheel을 빌드하고 아래 리허설을 실행한다.
별도 임시 가상환경에 wheel만 설치하며 합성 DB만 생성한다. 저장소 밖에서 유지보수 명령을
실행하고 백업·복구·감사 비교·사용 중 거절·롤백 보존·변조 거절을 확인한 뒤 임시
설치와 데이터를 제거한다. Linux/macOS용이며 출력 JSON에 wheel SHA-256을 포함한다.

```sh
.venv/bin/python -m pip wheel --no-deps --wheel-dir artifacts/package-review .
.venv/bin/python scripts/review_installed_commands.py --wheel artifacts/package-review/open_aegis-0.1.0-py3-none-any.whl
```

이 wheel은 Python 서비스·유지보수 코드만 포함한다. 프런트엔드 dist는 Docker의
별도 빌드 단계 또는 로컬 `start.sh`가 생성한다. 명령 리허설은 전체 서버 설치나
컨테이너·TLS·공개 릴리스 검증을 대신하지 않는다.

자동 테스트는 실행 중 복구 거절, 원본 덮어쓰기 거절, 변경 전 복사본 보존,
손상/최신 스키마 거절, 한글·공백·물음표 경로, 복구 후 이전 세션 폐기,
기존 비밀번호 로그인과 기록 복원, 마이그레이션 롤백을 검증한다.
실습 DB를 백업해 별도 디렉터리로 복구하는 명령도 실행했다.
PostgreSQL의 대표 HTTP 시작/종료·덤프 복구 후 SQLite 반환, 실행 중 논리 백업→
새 스키마 복구→이전 세션 거절/기존 비밀번호 로그인도 실제 DB와 설치본에서 검수했다. 전체 PostgreSQL
운영 복구·컨테이너 볼륨·원격 스토리지·전원 차단 리허설은 아직 검증하지 않았다.

## 요청 제한

HTTP 요청 본문은 2 MiB, 전체 본문 수신은 30초로 제한한다. Content-Length가
없어도 누적 바이트를 확인한다. 대용량 자산 가져오기는 여러 요청으로 나눈다.
검증 오류 응답에는 입력 값과 예외 context를 넣지 않아 비밀번호나 가져온 기록을
반사하지 않는다. 이 제한은 전체 서비스 부하 검증을 대신하지 않는다.

## 실행 속도·시간·대기열

[실행 정책 운영](RUNTIME.md)에 환경변수 범위, origin 공유 제한, DNS/HTTP/작업
시간 초과, 재시도·새 승인 계획, 지표의 재시작 범위와 정상 종료 절차를 정리했다.


## 감사 로그 연결과 외부 체크포인트

[AUDIT.md](AUDIT.md)의 읽기 전용 검증 명령으로 이벤트 연결을 검사하고 체크포인트를
내보낸다. 독립적으로 신뢰하는 위치에 이전 체크포인트를 보관한 뒤 비교해야 데이터
전체의 재작성이나 오래된 백업으로의 교체를 탐지할 수 있다. 같은 DB 디렉터리에만
보관한 파일은 독립 신뢰 근거가 아니다. 현재 자동 외부 전송이나 서명은 제공하지 않는다.

감사 기준의 주기적인 append-only 보관은 `aegis-checkpoint`와
[AUDIT.md](AUDIT.md)의 독립 경로·스케줄러 계약을 따른다. 실제 운영 예약은
운영자가 설정하며 원격 보관 신뢰/실행 실패 감시는 별도 검증이 필요하다.

## 컨테이너 설정과 재현 검수

기본 이미지는 SQLite를 사용한다. `.env`에서 `AEGIS_INSTALL_POSTGRES=1`로
설정하고 재빌드하면 `requirements-postgres.lock`의 드라이버를 추가 설치한다.
`AEGIS_STORAGE_BACKEND=postgres`, `AEGIS_POSTGRES_DSN`, `AEGIS_POSTGRES_SCHEMA`는
Compose가 서버에 전달한다. 기존 이미지에 환경 변수만 추가해도 드라이버가
설치되는 것은 아니다. DB/스키마를 먼저 준비하는 [네이티브 설치 계약](POSTGRES-STORAGE.md)은
유지하며 Compose가 외부 DB를 생성하거나 자동 초기화하지 않는다. 컨테이너의
127.0.0.1은 호스트 DB를 가리키지 않으므로 접근 가능한 DB 주소를 명시한다.

AI 대화 사용·가격 JSON·ScopeSentry 연결 JSON과 보고서 동시성/시간 설정도
Compose에 전달한다. ScopeSentry의 `token_env`로 지정한 별도 인증 변수는
운영자가 Compose override의 환경 설정 등으로 전달해야 한다. 연결 JSON에
인증 값을 직접 넣지 않는다. `docker compose config` 출력에는 DSN/API 키 등
환경 값이 포함될 수 있으므로 공개 검증 자료에 복사하지 않는다.

상태 검사는 `python -m aegis.healthcheck`를 실행한다. 환경의 `AEGIS_PORT`
(기본8787)에 직접 loopback으로 연결하며 proxy와 redirect를 사용하지 않는다.
HTTP200, 4KiB 이하 JSON, `status:ok`와 현재 프로그램 버전이 일치해야 성공한다.
소켓 timeout은3초이며 이미지의 health timeout은5초다. 허용 Host를 원격 이름으로
제한하면 `AEGIS_HEALTH_HOST`도 그 이름으로 설정한다. 이 값은 Host 헤더만 바꾸며
실제 연결 주소는127.0.0.1이다. Compose의 기본 내부 포트는8787로 유지한다.

Docker가 있는 독립 검수 환경에서는 다음 명령을 사용한다.

```sh
python3 scripts/review_container.py
python3 scripts/review_container.py --postgres-extra
```

각 실행은 고유한 이미지·bridge 네트워크·볼륨과 서버 컨테이너를 만들고 임의의
호스트 loopback 포트만 공개한다. 비관리자/read-only 실행, 실제 health, UI 파일,
최초 설정/인증, 승인 대기 계획, 볼륨/쿠키의 재시작 유지, 체크포인트 보관/반복,
중지한 볼륨의 복구, 이전 세션 거절/비밀번호 유지·백업 이후 노트 제거, 정상 종료를
검수하고 생성한 리소스를 정리한다. 대상 실행은 승인하지 않는다. `--postgres-extra`는
추가 드라이버 import를 확인하지만 HTTP/복구 리허설의 저장소는 SQLite이며 실제
PostgreSQL 컨테이너 검수를 대신하지 않는다. 빌드 캐시와 내려받은 base image는
Docker에 남을 수 있다. 패키지 다운로드에는 빌드 네트워크가 필요하다.
네트워크는 Compose와 같은 일반 bridge이며 외부 송신을 차단하지 않는다.
Docker29.5.2의 internal-only 네트워크에서는 지정한 호스트 포트가 실제로 공개되지
않는 현상을 재현하여 이 구성을 사용한다. 복구 컨테이너는 `--network none`으로 실행한다.

2026-10-05에는 별도 Colima VM의 Linux arm64/Docker29.5.2에서 두 이미지 모드의
실제 build/health/HTTP/volume/restart/restore/종료 검수를 통과했다.
결과와 정리 근거는 [VALIDATION.md](VALIDATION.md)의 컨테이너 검수 항목에 기록한다.
CI에도 두 모드가 있지만 hosted 실행·amd64/멀티 아키텍처·실제 Compose 기동과
PostgreSQL 컨테이너 저장소는 아직 미검증이다.
