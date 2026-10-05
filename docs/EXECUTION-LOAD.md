# 실제 승인 실행·조회·프로세스 장애 리허설

`scripts/review_execution_load.py`는 별도 임시 워크스페이스·loopback 서비스와
소유한 HTTP fixture를 만들고 실제 검사를 승인해 실행한다. 개발 환경의 Python
3.11+, httpx와 POSIX `ps`/socket 전달을 사용하며 SQLite가 기본이다.

```sh
.venv/bin/python scripts/review_execution_load.py \
  --duration 300 --clients 2 --output artifacts/execution-load-sqlite.json

PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH" \
  .venv/bin/python scripts/review_execution_load.py --postgres \
  --duration 300 --clients 2 --output artifacts/execution-load-postgres.json
```

PostgreSQL 모드는 psycopg와 `initdb`/`pg_ctl`이 필요하다. `/tmp` 아래 소유한 임시
클러스터를 새로 만들며 TCP를 열지 않고 전용 Unix socket만 사용한다. 새 네이티브
스키마를 초기화한다. 사용자의 DB나 워크스페이스 설정은 사용하지 않는다.
PostgreSQL 모드에서는 SQLite 워크스페이스가 생성되지 않는 것도 확인한다.

`--duration`은 반복 실행 구간 2–3,600초, `--clients`는 조회 사용자 1–8개다.
시작·후속 동시 승인·프로세스 장애/복구와 정리에 필요한 시간은 duration 밖이다.
모든 자격증명과 데이터는 합성이며 대상은 부모가 생성한 127.0.0.1 HTTP 서버다.
외부 대상·AI 제공자·원격 연동은 사용하지 않는다. 기존 `AEGIS_*`/`PG*` 환경을
제거하고 검수용 요청 속도20/s·재시도0·요청 timeout5s를 명시한다.

각 반복은 보안 헤더·쿠키·엔드포인트 검사를 승인하기 전 대상 요청이 없음을
확인한다. 실제 약한 응답에서 발견을 얻고 사람이 수용 사유를 저장한다. 실제503
응답의 새 승인 재검증은 판정 불가와 수용 상태 보존을 확인한다. 헤더를 수정한
응답의 별도 승인 재검증은 해결 기록을 확인한다. 이 세 작업과 함께 목록·요약·
운영 지표·전체 JSON 보고서를 반복 조회한다. 목록 페이지 크기25·HTTP/JSON
성공·백그라운드 처리 오류0을 검사한다. 내보내기429와 양의 Retry-After는 정상
입장 제한으로 기록한다. 읽기 클라이언트는 약20ms 간격이며 승인·재검증 주기는
실행 시간에 더해 약200ms를 둔다. 포화 처리량 벤치마크는 아니다.

조회 구간 종료 후6개 작업을 먼저 승인 대기로 만들고 대상 무요청을 확인한 뒤
동시 승인해 모두 완료한다. 이어 별도 미승인 작업1개와 승인 작업4개를 만들고
fixture가 응답을 보류한 상태에서 실제 실행2개/대기2개를 확인한다. 소유한 서비스
프로세스만 SIGKILL로 종료한다. 같은 저장소로 재시작하면4개가 interrupted이고
미승인 작업은 pending이어야 하며 자동 대상 요청이 없어야 한다. 새 재실행 작업도
승인 전에는 요청이 없고 명시 승인 후 완료해야 한다.

이벤트 계획 처리의 복구 후 제안 준비·오류0·감사 연결 검증, 누적 작업 상태 건수,
정상 종료 완료 표식·실제 워크스페이스 잠금 재획득을 확인한다. 임시 서비스·대상·
클러스터·데이터를 제거하고 결과 JSON만 남긴다. 실패하면 단계·오류 종류와 당시
건수를 결과에 남기고 명령이 비정상 종료한다. 실패 기록은 정리 완료 보장이 아니다.

결과는 서비스 Python 코드 지문·Python/플랫폼·반복/요청 건수·응답별 건수·마지막
최대2,000개 조회의 p50/p95·반복별 RSS/누적CPU 표본·표본 최대RSS·운영 지표와
복구/감사 근거를 포함한다. Linux만 열린FD 건수를 제공하며 macOS는 null이다.
부모·클라이언트·PostgreSQL 프로세스의 RSS/CPU는 측정하지 않는다.

현재 리허설은 조회한 `/runtime`의 이벤트 진행 상태도 기록한다. 마지막 최대2,000개
표본에는 처리/최신 위치·실제 대기 건수·오래된 대기 시간이 포함되며, 전체 구간의
표본 최대 대기 건수/시간은 별도로 유지한다. 잘못된 위치나 배경 처리 오류를 정상
진행으로 취급하지 않는다. 약30초마다 `<output>.progress.json`을 임시 파일에서
원자적으로 교체하고 stdout에 단계·경과 시간·반복/조회 건수·RSS·최신 진행 지표를
기록한다. 중간 파일은 완료/통과 증거가 아니며 실제 프로세스 생존을 대신하지 않는다.

반복 시작/종료의 SQLite 워크스페이스 또는 PostgreSQL 클러스터 파일 크기를
측정한다. WAL을 포함하며 PostgreSQL 초기 클러스터/시스템 카탈로그도 포함한다.
파일을 순회하는 동안 변경될 수 있는 근사치이고 일관된 DB 백업 크기나 저장소
보존 한도를 뜻하지 않는다. 서로 다른 저장소 크기를 직접 성능 비교하지 않는다.

완료된 결과의 RSS 표본을 시간 구간4개로 나누어 비교하려면 다음 명령을 사용한다.
중간/실패/정리 미확인 결과는 요약하지 않는다. 구간별 중앙값·최소/최대 RSS와
CPU 관측값, 최대 이벤트 대기량·파일 크기와 복구 근거를 출력한다. 구간 변화의
원인을 메모리 누수로 판정하거나 자동 통과 기준을 만들지는 않는다.

```sh
.venv/bin/python scripts/summarize_execution_load.py \
  artifacts/execution-load-sqlite.json --output artifacts/execution-load-summary.json
```

5분 또는1시간 통과는 수일 운영·생산 환경의 SLO·디스크 보존 정책을 증명하지
않는다. 순간 메모리 최대·전체 인증 부하·다수 origin·TLS/프록시·느린 보고서
소비자·브라우저/모바일·LLM·DB 장애·PITR·컨테이너 검수도 별도 항목이다.
