# 컬러와 Neo-brutalism 디자인 규칙

## 출처와 토큰

사용자 지정 출처: [Wanted Montage Semantic colors](https://montage.wanted.co.kr/docs/foundations/base-material/colors/semantic).
2026-10-03 공식 문서 사이트에서 사용하는 테마 값(light/dark)을 확인했다.
62개 의미별 색상은 `web/src/design/montage-semantic.json`, 실제 CSS 변수는
`web/src/design/tokens.css`에 있다. 원티드의 로고·이미지·컴포넌트는 사용하지 않는다.

현재 제품은 밝은 테마다. dark 값은 자료에 정리했으며 테마 전환을 구현했다고 주장하지 않는다.
값의 마지막 두 자리는 alpha다. 알파 색은 바탕 위에 합성되므로 원색과 다르다.

| 역할 | 이 서비스에서 사용하는 위치 |
|---|---|
| Primary | 실행 생성·저장·현재 탐색 위치·키보드 포커스 |
| Label | 본문·제목·보조 텍스트; 보조 설명에도 neutral 사용 |
| Background | 페이지/카드/대화상자, 상태 배지의 옅은 바탕 |
| Status | 긍정/주의/오류 표시; 텍스트와 아이콘을 함께 표시 |
| Accent | 히어로·통계 아이콘·검증 단계의 구분 |
| Line / Fill | 표의 구분선·비활성 또는 보조 영역 |
| Static / Inverse | 주요 버튼의 흰 글자·반전 표시 |
| Material | 모달 뒤 배경 dimmer |

Montage의 assistive/disable은 작은 본문에 그대로 사용하면 대비가 부족할 수 있다.
실제 설명은 neutral, 상태 배지 글자는 normal을 사용한다.
긍정은 '검증 결과 상태'를 뜻하며 사이트 전체가 안전하다는 뜻으로 사용하지 않는다.

## Neo-brutalism 적용 원칙

[Neobrutalism.com](https://neobrutalism.com/docs)의 디자인 원칙을 참고했다.
장식적 거칠음으로 운영 정보가 읽기 어려워지지 않도록 제품 규칙을 별도로 정의한다.

- 구조 테두리 2px, 모서리 2px, 그림자는 blur 없는 단색 offset.
- 그림자 깊이: 버튼 2px, 카드 4px, 대화상자 8px. 표 내부 행은 그림자 없음.
- 활성 버튼은 이동하며 그림자를 줄인다. hover/active/disabled/focus 상태가 별도로 보인다.
- 그라데이션·유리 효과·부드러운 그림자 대신 단색 영역과 강한 제목으로 계층을 만든다.
- 상태는 색+텍스트; 통계와 표는 숫자·기준·행 제목이 먼저 읽혀야 한다.
- 본문은 13~14px, 보조·기록은 최소 12px. 로고의 영문 부제는 정보 본문과 별도로 9px.
- 주요 컨트롤 높이 44px. 이동 애니메이션은 reduced-motion 설정에서 제거한다.
  버튼의 hover/active 위치 이동도 제거하고 색상·그림자·포커스 표시로 상태를 전달한다.
  배치용 transform과 그래프 확대/축소는 이 버튼 규칙으로 변경하지 않는다.
- 인증 후 첫 키보드 링크는 ‘본문으로 건너뛰기’다. 포커스 시에만 표시하며 현재
  페이지 제목에 포커스를 옮긴다. URL과 탐색 이력은 바꾸지 않는다. 본문 landmark도
  같은 제목으로 이름을 연결한다. 모달을 열면 배경의 건너뛰기 링크도 inert다.
- focus-visible 3px blue outline, modal focus trap에서 숨겨진 입력은 제외한다.
  네이티브 라디오 그룹은 선택된 항목 또는 현재 포커스 항목을 하나의 Tab 경계로
  취급한다. 미선택 그룹의 방향별 진입과 서로 다른 폼 소유자를 구분하고 포커스
  순환으로 선택값을 변경하지 않는다. [W3C 모달](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/)과
  [라디오 그룹](https://www.w3.org/WAI/ARIA/apg/patterns/radio/)의 키보드 기준을 참고한다.
- 모바일에서는 장식 그래픽을 숨기고, 표는 표 영역 안에서 가로 스크롤한다.

구조 토큰 `--stroke`, `--radius`, `--shadow-*`는 Open Aegis가 정의했다.
Montage 원본 elevation과 Neo-brutalism 그림자를 혼동하지 않는다.
도넛은 비율을 인코딩하는 차트로만 conic-gradient를 사용한다. 장식 그라데이션은 없다.

## 검증

`python scripts/check_design.py`는 alpha 합성 후 본문·보조 설명·주요 버튼·히어로·상태 배지의
대표 foreground/background 조합을 WCAG AA의 4.5:1과 비교한다. 전체 화면의 접근성 인증을
대신하지 않으며, 브라우저에서 키보드·포커스·화면 크기·오류 흐름도 따로 검증한다.

## 확인한 원본 값

| Semantic | Light | Dark |
|---|---|---|
| `static.white` | `#ffffff` | `#ffffff` |
| `static.black` | `#000000` | `#000000` |
| `primary.normal` | `#0066FF` | `#3385FF` |
| `primary.strong` | `#005EEB` | `#1A75FF` |
| `primary.heavy` | `#0054D1` | `#0066FF` |
| `label.normal` | `#171719` | `#F7F7F8` |
| `label.strong` | `#000000` | `#ffffff` |
| `label.neutral` | `#2E2F33E0` | `#C2C4C8E0` |
| `label.alternative` | `#37383C9C` | `#AEB0B69C` |
| `label.assistive` | `#37383C47` | `#AEB0B647` |
| `label.disable` | `#37383C29` | `#989BA229` |
| `background.normal.normal` | `#ffffff` | `#1B1C1E` |
| `background.normal.alternative` | `#F7F7F8` | `#0F0F10` |
| `background.elevated.normal` | `#ffffff` | `#212225` |
| `background.elevated.alternative` | `#F7F7F8` | `#141415` |
| `background.transparent.normal` | `#ffffff14` | `#2122259C` |
| `background.transparent.alternative` | `#ffffff47` | `#2122259C` |
| `background.status.negative` | `#FF424214` | `#FF636314` |
| `background.status.cautionary` | `#FF920014` | `#FFA93814` |
| `background.status.positive` | `#00BF4014` | `#1ED45A14` |
| `interaction.inactive` | `#989BA2` | `#5A5C63` |
| `interaction.disable` | `#F4F4F5` | `#2E2F33` |
| `line.normal.normal` | `#70737C38` | `#70737C52` |
| `line.normal.neutral` | `#70737C29` | `#70737C47` |
| `line.normal.alternative` | `#70737C14` | `#70737C38` |
| `line.solid.normal` | `#E1E2E4` | `#37383C` |
| `line.solid.neutral` | `#EAEBEC` | `#333438` |
| `line.solid.alternative` | `#F4F4F5` | `#2E2F33` |
| `line.primary.normal` | `#0066FF47` | `#3385FF47` |
| `line.primary.strong` | `#0066FF6E` | `#3385FF6E` |
| `line.status.negative.normal` | `#FF42426E` | `#FF63636E` |
| `line.status.negative.strong` | `#FF424285` | `#FF636385` |
| `line.status.cautionary.normal` | `#FF92006E` | `#FFA9386E` |
| `line.status.positive.normal` | `#00BF406E` | `#1ED45A6E` |
| `status.positive` | `#00BF40` | `#1ED45A` |
| `status.cautionary` | `#FF9200` | `#FFA938` |
| `status.negative` | `#FF4242` | `#FF6363` |
| `accent.background.redOrange` | `#FF5E00` | `#FF7B2E` |
| `accent.background.lime` | `#58CF04` | `#6BE016` |
| `accent.background.cyan` | `#00BDDE` | `#28D0ED` |
| `accent.background.lightBlue` | `#00AEFF` | `#3DC2FF` |
| `accent.background.violet` | `#6541F2` | `#7D5EF7` |
| `accent.background.purple` | `#CB59FF` | `#D478FF` |
| `accent.background.pink` | `#F553DA` | `#FA73E3` |
| `accent.foreground.red` | `#E52222` | `#FF6363` |
| `accent.foreground.redOrange` | `#F55A00` | `#FF7B2E` |
| `accent.foreground.orange` | `#D17600` | `#FF9200` |
| `accent.foreground.lime` | `#429E00` | `#58CF04` |
| `accent.foreground.green` | `#009632` | `#1ED45A` |
| `accent.foreground.cyan` | `#0098B2` | `#00BDDE` |
| `accent.foreground.lightBlue` | `#008DCF` | `#00AEFF` |
| `accent.foreground.blue` | `#005EEB` | `#4F95FF` |
| `accent.foreground.violet` | `#5B37ED` | `#9E86FC` |
| `accent.foreground.purple` | `#AD36E3` | `#D478FF` |
| `accent.foreground.pink` | `#E846CD` | `#FA73E3` |
| `inverse.primary` | `#3385FF` | `#0066FF` |
| `inverse.background` | `#1B1C1E` | `#ffffff` |
| `inverse.label` | `#F7F7F8` | `#171719` |
| `fill.normal` | `#70737C14` | `#70737C38` |
| `fill.strong` | `#70737C29` | `#70737C47` |
| `fill.alternative` | `#70737C0D` | `#70737C1F` |
| `material.dimmer` | `#17171985` | `#171719BD` |
