/** Production identity panels with owned synthetic transport, never real credentials. */
import { useState } from "react";
import { createRoot } from "react-dom/client";
import { PasswordPanel, UserPanel, type User } from "../../src/identity";
import { api } from "../../src/api";
import "../../src/style.css";
const user: User = {
  id: "fixture_admin",
  username: "fixture_admin",
  name: "합성 관리자",
  role: "admin",
  disabled: false,
  created_at: 1,
  updated_at: 1,
};
const held: Array<(response: Response) => void> = [];
const response = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
const originalFetch = window.fetch.bind(window);
window.fetch = async (input, init) => {
  const url = String(input);
  if (url === "/api/users" && (!init?.method || init.method === "GET"))
    return response([user]);
  if (url === "/api/auth/login") return response({ user });
  if (
    url === "/api/auth/password" ||
    (url.startsWith("/api/users/") && init?.method !== "GET")
  )
    return new Promise((resolve) => held.push(resolve));
  return originalFetch(input, init);
};
function Fixture() {
  const [generation, setGeneration] = useState(0),
    [callbacks, setCallbacks] = useState(0);
  return (
    <main style={{ padding: 24 }}>
      <h1>계정 변경 지연 응답 검수</h1>
      <p>실제 계정·인증·쿠키를 사용하지 않는 합성 fixture입니다.</p>
      <p role="status">세션 변경 콜백: {callbacks}</p>
      <p>화면 세대: {generation}</p>
      <button onClick={() => setGeneration((v) => v + 1)}>
        화면 다시 열기
      </button>
      <button
        onClick={() => setTimeout(() => setGeneration((v) => v + 1), 5000)}
      >
        5초 뒤 화면 다시 열기
      </button>
      <button
        onClick={() =>
          setTimeout(
            () =>
              held
                .splice(0)
                .forEach((resolve) => resolve(response({ ok: true }))),
            5000,
          )
        }
      >
        5초 뒤 성공 응답 해제
      </button>
      <button
        onClick={() =>
          setTimeout(
            () =>
              held
                .splice(0)
                .forEach((resolve) =>
                  resolve(response({ detail: "합성 저장 실패" }, 503)),
                ),
            5000,
          )
        }
      >
        5초 뒤 실패 응답 해제
      </button>
      <button
        onClick={() =>
          setTimeout(async () => {
            await api("/auth/login", "POST", {});
            setGeneration((v) => v + 1);
          }, 5000)
        }
      >
        5초 뒤 새 로그인
      </button>
      <button
        onClick={async () => {
          await api("/auth/login", "POST", {});
          setGeneration((v) => v + 1);
        }}
      >
        새 로그인으로 다시 열기
      </button>
      <button
        onClick={() =>
          held.splice(0).forEach((resolve) => resolve(response({ ok: true })))
        }
      >
        이전 성공 응답 해제
      </button>
      <button
        onClick={() =>
          held
            .splice(0)
            .forEach((resolve) =>
              resolve(response({ detail: "합성 저장 실패" }, 503)),
            )
        }
      >
        이전 실패 응답 해제
      </button>
      <PasswordPanel
        key={"password-" + generation}
        onChanged={() => setCallbacks((v) => v + 1)}
      />
      <UserPanel
        key={"users-" + generation}
        currentUser={user}
        onSessionChanged={() => setCallbacks((v) => v + 1)}
      />
    </main>
  );
}
createRoot(document.getElementById("root")!).render(<Fixture />);
