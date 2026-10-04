/** Owned browser fixture: production API + ReportDownload, synthetic fetch only. */
import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { api } from "../../src/api";
import { ReportDownload } from "../../src/ReportDownload";
import "../../src/style.css";

const held: Array<(response: Response) => void> = [];
const json = (status: number) =>
  new Response(JSON.stringify({ detail: "합성 미인증 응답" }), {
    status,
    headers: { "Content-Type": "application/json" },
  });
const originalFetch = window.fetch.bind(window);
// Observe the production save path without creating a file in Downloads.
const originalObjectURL = URL.createObjectURL.bind(URL);
URL.createObjectURL = (blob) => {
  window.dispatchEvent(new Event("aegis-fixture-file-created"));
  return originalObjectURL(blob);
};
HTMLAnchorElement.prototype.click = () => {};
window.fetch = async (input, init) => {
  const url = String(input);
  if (url === "/api/auth/login") return json(200);
  if (url === "/api/fixture-current") return json(401);
  if (url === "/api/fixture-current-read") return json(200);
  if (url === "/api/fixture-held" || url.startsWith("/api/reports/export?"))
    return new Promise<Response>((resolve) => held.push(resolve));
  return originalFetch(input, init);
};
function Fixture() {
  const [expired, setExpired] = useState(0);
  const [result, setResult] = useState("대기");
  const [files, setFiles] = useState(0);
  useEffect(() => {
    const listener = () => setExpired((count) => count + 1);
    window.addEventListener("aegis-session-expired", listener);
    const file = () => setFiles((count) => count + 1);
    window.addEventListener("aegis-fixture-file-created", file);
    return () => {
      window.removeEventListener("aegis-session-expired", listener);
      window.removeEventListener("aegis-fixture-file-created", file);
    };
  }, []);
  const request = async (path: string, method = "GET") => {
    try {
      await api(path, method);
      setResult(path === "/auth/login" ? "새 로그인 완료" : "조회 성공 반영");
    } catch (error) {
      setResult((error as Error).message);
    }
  };
  return (
    <main style={{ padding: 24 }}>
      <h1>세션 지연 응답 회귀 검수</h1>
      <p>실제 인증과 대상 요청을 수행하지 않는 합성 fixture입니다.</p>
      <p role="status">만료 이벤트: {expired}</p>
      <p>파일 생성 경로: {files}</p>
      <p>API 결과: {result}</p>
      <button
        onClick={() => {
          setResult("이전 요청 대기");
          void request("/fixture-held");
        }}
      >
        이전 API 요청
      </button>
      <button onClick={() => void request("/auth/login", "POST")}>
        새 로그인
      </button>
      <button
        onClick={() => held.splice(0).forEach((resolve) => resolve(json(401)))}
      >
        이전 401 응답 해제
      </button>
      <button onClick={() => void request("/fixture-current")}>
        현재 401 요청
      </button>
      <button
        onClick={() => held.splice(0).forEach((resolve) => resolve(json(200)))}
      >
        이전 성공 응답 해제
      </button>
      <button onClick={() => void request("/fixture-current-read")}>
        현재 조회
      </button>
      <ReportDownload format="json" label="지연 보고서" />
    </main>
  );
}
createRoot(document.getElementById("root")!).render(<Fixture />);
