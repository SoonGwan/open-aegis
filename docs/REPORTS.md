# Report exports

`GET /api/reports/export?format=json|csv|markdown&task_id=...` requires authentication.
All three roles may export the shared workspace. Omitting task_id exports the workspace;
a missing requested task is 404 and an unknown format is 422. Downloads retain their
existing `aegis-report.json|csv|md` filenames and media types, with `Cache-Control: no-store`.

## Complete streams and one snapshot

Exports have no list-page cap. A dedicated SQLite `mode=ro` connection begins one read
transaction before the first content chunk. Tasks, findings, evidence, finding history,
coverage and traffic are read from that same snapshot; writes after the export starts
appear in a subsequent export. This differs from list insertion watermarks, whose
existing rows remain live. Coverage includes expected cells missing from older records,
with the existing provenance and status checks.

Records stream directly in reverse insertion order. SQL explicitly traverses rowids
rather than sorting all matching payloads into a temporary tree. JSON emits its existing
version/generated_at metadata and all six arrays, with full stored finding associations.
Whitespace is compact instead of the old pretty printing. CSV still contains findings
only, starts with a UTF-8 BOM, and quotes values starting with spreadsheet formula
characters after leading whitespace. Markdown retains task policy/termination/retry,
coverage denominators, finding decisions, evidence and remediation.

A task export includes findings linked to that task and evidence/traffic recorded for it.
History follows the selected findings, including their decisions from other times/tasks;
it is not restricted to only decisions made during that task. A workspace export includes
all tasks/findings and related history; evidence/traffic with no existing task are omitted,
as before. An export is a saved-record report, not an independent proof that every stored
association is valid or that an asset is secure.

## Resource lifecycle and limits

The async response requests one synchronous chunk at a time in the threadpool. A worker
may change between chunks, but connection access remains serial. The connection closes
on normal completion, a data/SQL error, early iterator close and either ASGI disconnect
path (disconnect event or send failure). No whole-workspace Python list or joined report
string is built. Memory still depends on the largest individual stored record, its JSON
encoding and SQLite's cache; this is not a universal process-memory limit.

A slow download keeps its read snapshot open and can delay WAL checkpointing. All
formats and authenticated roles share admission slots per server process. The default
is **2 concurrent exports** and **120 seconds** from admission, including SQL, encoding
and sends. Excess requests are rejected before opening a stream with **429** and
`Retry-After: 5`; there is no waiting queue. Configure and restart with:

| Environment | Default | Accepted range |
| --- | --- | --- |
| `AEGIS_EXPORT_PARALLEL` | 2 | integer 1–4 |
| `AEGIS_EXPORT_TIMEOUT` | 120 | finite seconds 1–600 |

Invalid configuration fails before the workspace lock opens and does not echo the value.
These limits are independent of scan approvals and do not change target request budgets.
The entire response has a monotonic deadline, SQLite progress callbacks interrupt long
queries, and SQLite lock waits are capped at the smaller of one second or remaining time.
Disconnect events also interrupt an active SQL worker. Admission slots release exactly
once on completion, cancellation, timeout or failure.

SQLite cancellation is cooperative. An individual Python decode/encode operation or
blocking OS call is not forcibly preempted; cleanup waits for an active worker to finish.
The ASGI send-error path detects disconnect at the next send, whereas the disconnect-event
path can signal an active SQL worker. This is not a hard process CPU/RSS limit. There is
still no retention policy or multi-process shared quota.
A corrupt record or connection failure after response headers can leave an incomplete
file; clients must retry a failed download rather than treat partial bytes as complete.
The HTTP response streams without Content-Length. No schema migration is needed.

## Validation

`tests/test_report_streams.py` verifies complete scoped exports beyond 1,000 records,
role/query checks, no Store.all reads, consistent coverage during writes, CSV formula
handling, read-only connections, Unicode URI filenames, cleanup on errors/disconnects
and absence of a sorting temporary tree. A 6,000-record-per-collection JSON export exceeds
12 MB while measured Python allocations stay below 2 MB. The allocation test excludes
SQLite native allocations and does not establish an RSS or long-running load bound.
Existing coverage, secret-redaction and triage export tests also pass.


## Runtime counters

`GET /api/runtime` adds `exports` with `policy`, `active`, `started`, `completed`,
`cancelled`, `timed_out`, `failed` and `rejected`. It requires authentication and counts
reset at process restart. Completed means ASGI accepted the final body send, not proof
that the client saved its file. The settings screen refreshes export policy/counters
alongside the existing execution metrics every four seconds. Timeout after headers
aborts the response instead of returning a valid truncated report or replacing its status.

`tests/test_export_limits.py` covers invalid environment values, atomic admission under
concurrent threads, rejection before stream creation, blocked-send timeouts, real SQL
interruption, prompt disconnect during SQL, exactly-once release and outcome counters.
