/** Manual browser regression fixture: uses the production Modal, never calls the API. */
import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import Modal from "../../src/components/Modal";
import "../../src/style.css";

function Fixture() {
  const parameters = new URLSearchParams(location.search);
  const [open, setOpen] = useState(parameters.get("frame") === "1");
  const longLabels = parameters.get("long") === "1";
  const separateForm = parameters.get("forms") === "two";
  const [tick, setTick] = useState(0);
  const [closedAt, setClosedAt] = useState<number | null>(null);
  const regionLast =
    new URLSearchParams(location.search).get("last") === "region";
  const radioLast =
    new URLSearchParams(location.search).get("last") === "radio";
  const radioEmpty =
    new URLSearchParams(location.search).get("choice") === "none";
  useEffect(() => {
    const timer = setInterval(() => setTick((value) => value + 1), 1000);
    return () => clearInterval(timer);
  }, []);
  useEffect(() => {
    if (window.parent === window) return;
    const dialog = document.querySelector<HTMLElement>('[role="dialog"]');
    const box = dialog?.getBoundingClientRect();
    window.parent.postMessage({
      type: "modal-width-metrics",
      viewport: innerWidth,
      rootClientWidth: document.documentElement.clientWidth,
      rootScrollWidth: document.documentElement.scrollWidth,
      dialog: box ? { left: box.left, right: box.right, width: box.width, height: box.height,
        clientWidth: dialog!.clientWidth, scrollWidth: dialog!.scrollWidth,
        clientHeight: dialog!.clientHeight, scrollHeight: dialog!.scrollHeight } : null,
    }, location.origin);
  }, [tick, open]);
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
          {radioLast && separateForm && <form aria-label="별도 폼 라디오">
            <fieldset><legend>별도 폼 그룹</legend>
              {["별도 폼 첫 번째", "별도 폼 두 번째"].map((label, index) =>
                <label className="checkbox-label scopesentry-connection" key={label}>
                  <input type="radio" name="fixture-choice" defaultChecked={index === 0} /><span>{label}</span>
                </label>
              )}
            </fieldset>
          </form>}
          {radioLast && (
            <fieldset>
              <legend>마지막 라디오 그룹</legend>
              {["첫 번째", "두 번째", "세 번째"].map((label, index) => (
                <label
                  className="checkbox-label scopesentry-connection"
                  key={label}
                >
                  <input
                    type="radio"
                    name="fixture-choice"
                    defaultChecked={!radioEmpty && index === 0}
                  />
                  <span>{label}{longLabels ? ` · https://owned-fixture.invalid/${"long-source-path-".repeat(35)}` : ""}</span>
                </label>
              ))}
            </fieldset>
          )}
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
