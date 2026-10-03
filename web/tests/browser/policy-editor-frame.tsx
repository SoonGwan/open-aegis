import React from "react";
import { createRoot } from "react-dom/client";
import { PolicyRulesEditor } from "../../src/PolicyRulesEditor";
import "../../src/style.css";

const initial = [{ path: "/api/account", role: "customer-a-test", expected_allowed: false,
  credential_env: "AEGIS_TEST_FIXTURE", response_schema: { type: "object", required: ["tenant_id"],
    properties: { tenant_id: { type: "string" } } }, ownership: { pointer: "/tenant_id", expected: "synthetic-customer-a" } }];
createRoot(document.getElementById("root")!).render(<main style={{ padding: 12 }}>
  <div className="modal" style={{ width: "100%", padding: 12, maxHeight: "none" }}>
    <h1 style={{ fontSize: 18 }}>정책 폼 너비 검수</h1>
    <form onSubmit={event => event.preventDefault()}><PolicyRulesEditor initial={initial} /></form>
  </div>
</main>);
