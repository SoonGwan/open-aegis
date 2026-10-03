import { test } from "node:test";
import assert from "node:assert/strict";
import {
  fetchReport,
  fetchPolicy,
  ReportDownloadError,
  retrySeconds,
} from "../src/report-download.ts";

test("download formats retain filenames and task IDs are query values", async () => {
  for (const [format, media, suffix] of [
    ["json", "application/json", "json"],
    ["csv", "text/csv", "csv"],
    ["markdown", "text/markdown", "md"],
  ] as const) {
    let url = "";
    const request = (async (input, init) => {
      url = String(input);
      assert.equal(init?.credentials, "same-origin");
      return new Response("report", {
        headers: { "Content-Type": media + "; charset=utf-8" },
      });
    }) as typeof fetch;
    const result = await fetchReport(
      format,
      "task?format=csv&x=1",
      new AbortController().signal,
      request,
    );
    assert.equal(
      new URL(url, "http://localhost").searchParams.get("task_id"),
      "task?format=csv&x=1",
    );
    assert.equal(
      new URL(url, "http://localhost").searchParams.get("format"),
      format,
    );
    assert.equal(await result.blob.text(), "report");
    assert.equal(result.filename, "aegis-report." + suffix);
  }
});

test("policy downloads encode task IDs and reject server eligibility failures", async () => {
  let url = "";
  const result = await fetchPolicy(
    "task?x=1/other",
    new AbortController().signal,
    (async (input) => {
      url = String(input);
      return new Response('{"format":"aegis-api-policy-v1"}', {
        headers: { "Content-Type": "application/json" },
      });
    }) as typeof fetch,
  );
  assert.equal(url, "/api/tasks/task%3Fx%3D1%2Fother/policy-reproduction");
  assert.equal(result.filename, "aegis-api-policy.json");
  await assert.rejects(
    fetchPolicy(
      "task",
      new AbortController().signal,
      (async () =>
        new Response('{"detail":"승인 필요"}', {
          status: 409,
        })) as typeof fetch,
    ),
    (error: unknown) =>
      error instanceof ReportDownloadError &&
      error.status === 409 &&
      error.message === "승인 필요",
  );
});

test("quota errors are never files and preserve status and retry delay", async () => {
  const request = (async () =>
    new Response(JSON.stringify({ detail: "한도 초과" }), {
      status: 429,
      headers: { "Retry-After": "5" },
    })) as typeof fetch;
  await assert.rejects(
    fetchReport("json", undefined, new AbortController().signal, request),
    (error: unknown) => {
      assert.ok(error instanceof ReportDownloadError);
      assert.equal(error.message, "한도 초과");
      assert.equal(error.status, 429);
      assert.equal(error.retryAfter, 5);
      return true;
    },
  );
  assert.equal(retrySeconds("invalid"), 0);
  assert.equal(retrySeconds("999999"), 600);
  assert.equal(retrySeconds("Thu, 01 Jan 1970 00:00:10 GMT", 5000), 5);
  assert.equal(retrySeconds("Thu, 01 Jan 1970 00:00:10 GMT", 11000), 0);
});

test("HTML, empty and interrupted bodies cannot become saved reports", async () => {
  for (const response of [
    new Response("<html>login</html>", {
      headers: { "Content-Type": "text/html" },
    }),
    new Response("", { headers: { "Content-Type": "application/json" } }),
  ]) {
    await assert.rejects(
      fetchReport(
        "json",
        undefined,
        new AbortController().signal,
        (async () => response) as typeof fetch,
      ),
      ReportDownloadError,
    );
  }
  const body = new ReadableStream({
    start(controller) {
      controller.enqueue(new TextEncoder().encode('{"partial":'));
      controller.error(new Error("broken stream"));
    },
  });
  await assert.rejects(
    fetchReport(
      "json",
      undefined,
      new AbortController().signal,
      (async () =>
        new Response(body, {
          headers: { "Content-Type": "application/json" },
        })) as typeof fetch,
    ),
    /다운로드를 완료하지 못했습니다/,
  );
});

test("aborted downloads do not return files and auth failures retain their status", async () => {
  const control = new AbortController();
  control.abort();
  await assert.rejects(
    fetchReport(
      "json",
      undefined,
      control.signal,
      (async () =>
        new Response("{}", {
          headers: { "Content-Type": "application/json" },
        })) as typeof fetch,
    ),
    { name: "AbortError" },
  );
  await assert.rejects(
    fetchReport(
      "json",
      undefined,
      new AbortController().signal,
      (async () => new Response("", { status: 401 })) as typeof fetch,
    ),
    (error: unknown) => {
      assert.ok(error instanceof ReportDownloadError);
      assert.equal(error.status, 401);
      return true;
    },
  );
});
