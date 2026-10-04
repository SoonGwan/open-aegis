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
window.fetch = async (input, init) => {
  const url = String(input);
  if (url === "/api/auth/login") return json(200);
  if (url === "/api/fixture-current") return json(401);
  if (url === "/api/fixture-held" || url.startsWith("/api/reports/export?"))
    return new Promise<Response>((resolve) => held.push(resolve));
  return originalFetch(input, init);
};
function Fixture() {
  const [expired, setExpired] = useState(0);
  const [result, setResult] = useState("대기");
  useEffect(() => {
    const listener = () => setExpired((count) => count + 1);
    window.addEventListener("aegis-session-expired", listener);
    return () => window.removeEventListener("aegis-session-expired", listener);
  }, []);
  const request = async (path: string, method = "GET") => {
    try {
      await api(path, method);
      setResult("새 로그인 완료");
    } catch (error) {
      setResult((error as Error).message);
    }
  };
  return (
    <main style={{ padding: 24 }}>
      <h1>세션 지연 응답 회귀 검수</h1>
      <p>실제 인증과 대상 요청을 수행하지 않는 합성 fixture입니다.</p>
      <p role="status">만료 이벤트: {expired}</p>
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
      <ReportDownload format="json" label="지연 보고서" />
    </main>
  );
}
createRoot(document.getElementById("root")!).render(<Fixture />);
