/** Manual browser regression fixture: uses the production Modal, never calls the API. */
import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import Modal from "../../src/components/Modal";
import "../../src/style.css";

function Fixture() {
  const [open, setOpen] = useState(false);
  const [tick, setTick] = useState(0);
  const [closedAt, setClosedAt] = useState<number | null>(null);
  const regionLast =
    new URLSearchParams(location.search).get("last") === "region";
  useEffect(() => {
    const timer = setInterval(() => setTick((value) => value + 1), 1000);
    return () => clearInterval(timer);
  }, []);
  return (
    <main>
      <h1>모달 키보드 회귀 검수</h1>
      <p>
        갱신 번호 {tick} · 닫은 갱신 번호 {closedAt ?? "없음"}
      </p>
      <button onClick={() => setOpen(true)}>검수 모달 열기</button>
      {open && (
        <Modal
          title="키보드 검수"
          subtitle="검수용 설명"
          onClose={() => {
            setClosedAt(tick);
            setOpen(false);
          }}
        >
          <button>중간 버튼</button>
          <button tabIndex={-1}>Tab 순서 제외</button>
          <fieldset disabled>
            <legend>비활성 입력</legend>
            <input aria-label="비활성 필드" />
          </fieldset>
          <details>
            <summary>마지막 펼침</summary>
            <p>펼친 원본을 확인합니다.</p>
          </details>
          {regionLast && (
            <div
              role="region"
              aria-label="키보드 스크롤"
              tabIndex={0}
              style={{ maxHeight: 100, overflow: "auto" }}
            >
              <p style={{ height: 400 }}>
                Tab으로 접근하고 방향키로 스크롤합니다.
              </p>
            </div>
          )}
        </Modal>
      )}
    </main>
  );
}
createRoot(document.getElementById("root")!).render(<Fixture />);
