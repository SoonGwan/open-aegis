# Architecture

```mermaid
flowchart LR
  UI[React console] --> API[FastAPI / session auth]
  API --> DB[(SQLite / WAL)]
  API --> Gate[Task approval / scope snapshot]
  Gate --> Planner[Rules or optional LLM ordering]
  Planner --> Workers[1–4 Workers per task]
  Workers --> Transport[Scoped, DNS-pinned GET transport]
  Transport --> Target[Registered origin and path]
  Workers --> Checks[Reviewed check registry]
  Checks --> DB
  Transport --> DB
  DB --> Reports[Markdown / CSV / JSON]
  DB --> MCP[Read-only MCP stdio]
  DB --> Events[SSE activity stream]
  Events --> UI
```

`aegis/app.py` owns API validation, authentication, scheduling, report exports,
and the process lifecycle. `aegis/store.py` owns persistence. `aegis/engine.py`
owns task state transitions and parallel execution. `aegis/network.py` is the
only transport for target HTTP requests. `aegis/checks.py` defines observations
and expected policy comparisons. `aegis/mcp.py` opens an existing DB read-only.

`aegis/response_policy.py` validates a bounded JSON Schema subset and JSON Pointer
ownership expectations on complete JSON responses. It rejects remote references,
ambiguous/truncated bodies and excessive structure. Findings retain schema keyword
names or match booleans, never response values. See [API-POLICY.md](API-POLICY.md).

## Task states

`pending → queued → running → completed/failed/stopped`.
Pending rejection becomes `rejected`. Mid-run stop becomes `stopping` until
in-flight bounded socket operations finish. On restart, queued/running tasks
become `interrupted`; they are not automatically resumed. Scope snapshots
preserve the exact assets and policy rules approved for that task.

An LLM can reorder the selected checks only. Its result must be an exact
permutation of approved check IDs. Provider errors and invalid plans fall
back to the deterministic order and are visible in the activity log.

## Evidence and conclusions

A finding fingerprint is derived from asset ID, check ID, and observation
code. Evidence records are appended to the finding rather than replaced.
Retest resolves the original finding only when the relevant check completed
and no longer reported that fingerprint. A failed connection, skipped check,
server error, or cancellation produces an inconclusive retest.

Target bodies are held transiently (max 128 KiB for checks), never persisted.
Traffic stores a bounded-body hash and allowlisted response headers. Cookies,
Authorization, query values, and response bodies are excluded. User-entered
metadata is not automatically a safe place for secrets.

The UI uses server data rather than seeded production findings. Graph columns
are aggregate relationships; they are not a claim of a complete attack graph.

## Operational limits

One server process, shared workspace with admin/operator/viewer roles, SQLite WAL; no distributed scheduling or tenant isolation.
Task concurrency is capped at 2; workers per task at 4; target requests per
asset at 24. Socket timeout is 8 seconds. Stop is cooperative, not a forced
thread interruption. Records require an operator-controlled backup
and retention policy. Existing report exports include finding lifecycle state
as of export time, not an immutable historical status snapshot.

Schema version 1 adds users and user-bound sessions. Legacy administrator
credentials move transactionally to the admin account after an automatic backup;
legacy sessions are revoked. Server and restore share an OS workspace lease.
Offline restore normalizes the staging DB to DELETE journal mode before replacing
the database, so session deletion cannot remain only in an uninstalled WAL file.
