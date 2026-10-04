/** Production policy editor with an owned local form; no API or target requests. */
import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import { PolicyRulesEditor } from "../../src/PolicyRulesEditor";
import "../../src/style.css";
const initial = [
  {
    path: "/api/account",
    role: "customer-a-test",
    expected_allowed: false,
    credential_env: "AEGIS_TEST_FIXTURE",
    response_schema: {
      type: "object",
      required: ["tenant_id"],
      properties: { tenant_id: { type: "string" } },
    },
    ownership: { pointer: "/tenant_id", expected: "synthetic-customer-a" },
  },
];
if (new URLSearchParams(location.search).has("schema_error"))
  initial[0].response_schema = {
    ...initial[0].response_schema,
    properties: {
      tenant_id: { type: "합성".repeat(6000) },
    },
  };
function Fixture() {
  const [submitted, setSubmitted] = useState(0);
  return (
    <main style={{ padding: 12 }}>
      <div
        className="modal"
        style={{ width: "100%", padding: 12, maxHeight: "none" }}
      >
        <h1 style={{ fontSize: 18 }}>정책 폼 너비 검수</h1>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            setSubmitted((value) => value + 1);
          }}
        >
          <PolicyRulesEditor initial={initial} />
          <button type="submit">합성 정책 저장</button>
        </form>
        <p role="status">유효한 폼 제출: {submitted}</p>
      </div>
    </main>
  );
}
createRoot(document.getElementById("root")!).render(<Fixture />);
