import { test } from "node:test";
import assert from "node:assert/strict";
import { api } from "../src/api.ts";

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}
const json = (status: number) =>
  new Response(JSON.stringify({ detail: "synthetic response" }), {
    status,
    headers: { "Content-Type": "application/json" },
  });

test("an earlier unauthorized API reply cannot expire a subsequently logged-in session", async (t) => {
  const events: string[] = [];
  const originalWindow = Object.getOwnPropertyDescriptor(globalThis, "window");
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: {
      dispatchEvent: (event: Event) => {
        events.push(event.type);
        return true;
      },
    },
  });
  t.after(() => {
    if (originalWindow)
      Object.defineProperty(globalThis, "window", originalWindow);
    else Reflect.deleteProperty(globalThis, "window");
  });
  const old = deferred<Response>();
  t.mock.method(globalThis, "fetch", async (url: string) =>
    url === "/api/overview" ? old.promise : json(200),
  );
  const request = api("/overview");
  const rejected = assert.rejects(request, /synthetic response/);
  await api("/auth/login", "POST", { username: "owned-fixture" });
  old.resolve(json(401));
  await rejected;
  assert.deepEqual(events, []);
});

import { captureSession, expireSession } from "../src/api.ts";
import { fetchReport, ReportDownloadError } from "../src/report-download.ts";
import type { TestContext } from "node:test";

function observeExpiration(t: TestContext) {
  const events: string[] = [];
  const original = Object.getOwnPropertyDescriptor(globalThis, "window");
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: {
      dispatchEvent: (event: Event) => {
        events.push(event.type);
        return true;
      },
    },
  });
  t.after(() => {
    if (original) Object.defineProperty(globalThis, "window", original);
    else Reflect.deleteProperty(globalThis, "window");
  });
  return events;
}

test("current unauthorized requests expire once, while a request after re-login can expire again", async (t) => {
  const events = observeExpiration(t);
  const old = deferred<Response>();
  t.mock.method(globalThis, "fetch", async (url: string) =>
    url === "/api/old"
      ? old.promise
      : url === "/api/auth/login"
        ? json(200)
        : json(401),
  );
  const pending = assert.rejects(api("/old"));
  await assert.rejects(api("/overview"));
  old.resolve(json(401));
  await pending;
  assert.deepEqual(events, ["aegis-session-expired"]);
  await api("/auth/login", "POST", {});
  await assert.rejects(api("/overview"));
  assert.equal(events.length, 2);
});

test("failed login and auth-status reads do not silence current unauthorized replies", async (t) => {
  const events = observeExpiration(t);
  const old = deferred<Response>();
  t.mock.method(globalThis, "fetch", async (url: string) =>
    url === "/api/old"
      ? old.promise
      : url === "/api/auth/status"
        ? json(200)
        : json(401),
  );
  const pending = assert.rejects(api("/old"));
  await assert.rejects(api("/auth/login", "POST", {}));
  await api("/auth/status");
  assert.deepEqual(events, []);
  old.resolve(json(401));
  await pending;
  assert.deepEqual(events, ["aegis-session-expired"]);
});

test("logout, password change and setup invalidate the preceding request session", async (t) => {
  const events = observeExpiration(t);
  t.mock.method(globalThis, "fetch", async () => json(200));
  for (const path of ["/auth/logout", "/auth/password", "/auth/setup"]) {
    const current = captureSession();
    await api(path, "POST", {});
    expireSession(current);
  }
  assert.deepEqual(events, []);
});

test("login completed while a 401 body is decoding prevents the stale expiration", async (t) => {
  const events = observeExpiration(t);
  const detail = deferred<{ detail: string }>();
  const started = deferred<boolean>();
  t.mock.method(globalThis, "fetch", async (url: string) => {
    if (url === "/api/auth/login") return json(200);
    const response = json(401);
    response.json = async () => {
      started.resolve(true);
      return detail.promise;
    };
    return response;
  });
  const pending = assert.rejects(api("/overview"), /late body/);
  await started.promise;
  await api("/auth/login", "POST", {});
  detail.resolve({ detail: "late body" });
  await pending;
  assert.deepEqual(events, []);
});

test("an aborted request whose 401 body finishes late cannot expire the session", async (t) => {
  const events = observeExpiration(t);
  const detail = deferred<{ detail: string }>();
  const started = deferred<boolean>();
  t.mock.method(globalThis, "fetch", async () => {
    const response = json(401);
    response.json = async () => {
      started.resolve(true);
      return detail.promise;
    };
    return response;
  });
  const controller = new AbortController();
  const pending = assert.rejects(
    api("/overview", "GET", undefined, controller.signal),
  );
  await started.promise;
  controller.abort();
  detail.resolve({ detail: "aborted body" });
  await pending;
  assert.deepEqual(events, []);
});

test("a held unauthorized report retains its HTTP error without expiring a newer session", async (t) => {
  const events = observeExpiration(t);
  const old = deferred<Response>();
  const current = captureSession();
  const pending = fetchReport(
    "json",
    undefined,
    new AbortController().signal,
    async () => old.promise,
  ).catch((error: ReportDownloadError) => {
    assert.equal(error.status, 401);
    expireSession(current);
  });
  t.mock.method(globalThis, "fetch", async () => json(200));
  await api("/auth/login", "POST", {});
  old.resolve(json(401));
  await pending;
  assert.deepEqual(events, []);
});

test("successful auth headers invalidate old requests even if the response body is malformed", async (t) => {
  const events = observeExpiration(t);
  const current = captureSession();
  t.mock.method(
    globalThis,
    "fetch",
    async () => new Response("not JSON", { status: 200 }),
  );
  await assert.rejects(api("/auth/login", "POST", {}));
  expireSession(current);
  assert.deepEqual(events, []);
});

test("an earlier successful read cannot restore data after a new login", async (t) => {
  const old = deferred<Response>();
  t.mock.method(globalThis, "fetch", async (url: string) =>
    url === "/api/overview" ? old.promise : json(200),
  );
  const request = api("/overview");
  const rejected = assert.rejects(request, { name: "AbortError" });
  await api("/auth/login", "POST", {});
  old.resolve(
    new Response(JSON.stringify({ ownedBy: "previous-user" }), { status: 200 }),
  );
  await rejected;
});

test("a read body finishing after session replacement cannot return old identity", async (t) => {
  const body = deferred<{ authenticated: boolean; user: string }>();
  const started = deferred<boolean>();
  t.mock.method(globalThis, "fetch", async (url: string) => {
    if (url === "/api/auth/login") return json(200);
    const response = json(200);
    response.json = async () => {
      started.resolve(true);
      return body.promise;
    };
    return response;
  });
  const rejected = assert.rejects(api("/auth/status"), { name: "AbortError" });
  await started.promise;
  await api("/auth/login", "POST", {});
  body.resolve({ authenticated: true, user: "previous-user" });
  await rejected;
});

test("current reads return normally and committed mutation acknowledgments remain available", async (t) => {
  const old = deferred<Response>();
  t.mock.method(globalThis, "fetch", async (url: string) =>
    url === "/api/mutation" ? old.promise : json(200),
  );
  assert.deepEqual(await api("/overview"), { detail: "synthetic response" });
  const mutation = api("/mutation", "POST", {});
  await api("/auth/login", "POST", {});
  old.resolve(json(200));
  assert.deepEqual(await mutation, { detail: "synthetic response" });
});

test("an aborted successful read cannot deliver a body that finished late", async (t) => {
  const body = deferred<unknown>();
  const started = deferred<boolean>();
  t.mock.method(globalThis, "fetch", async () => {
    const response = json(200);
    response.json = async () => {
      started.resolve(true);
      return body.promise;
    };
    return response;
  });
  const controller = new AbortController();
  const rejected = assert.rejects(
    api("/overview", "GET", undefined, controller.signal),
    { name: "AbortError" },
  );
  await started.promise;
  controller.abort();
  body.resolve({ ownedBy: "previous-read" });
  await rejected;
});
