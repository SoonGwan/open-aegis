# Show HN introduction

Prepared for the [official Show HN guidelines](https://news.ycombinator.com/showhn.html).
The linked demo requires no account and uses sample data; real checks require a
self-hosted workspace and explicit target authorization.

Title: **Show HN: Open Aegis – Self-hosted security checks with approvals and evidence**

URL: https://aegis.no-money-do-you-have-money.com/demo/

## Submission text

I built Open Aegis after seeing repeated scanning and attacks against our own company's infrastructure. I wanted a workspace where a security check has a clear approved scope, observable evidence, a remediation record, and a separately approved retest.

It is MIT-licensed and self-hosted, with a Python/FastAPI backend and React/TypeScript console. The bounded GET checks cover HTTP security headers, transport security, cookie attributes, CORS declarations, scoped link observation, and operator-defined API authorization expectations. Plans freeze the scope and tools; an administrator approves execution separately. Finding history and original evidence survive remediation and retesting.

The link opens an account-free interactive sample: create a plan, approve it, inspect evidence, record a header fix, and approve its retest. It sends no scan requests and uses prepared sample responses. The real engine runs in your own workspace. The source console and demo default to English, with Korean available.

Source and local setup: https://github.com/SoonGwan/open-aegis

This is scoped configuration and policy verification, not a claim to find every vulnerability. AI planning is optional, and AI proposals still require execution approval. I would appreciate feedback on whether the approval/evidence/retest workflow fits your team's actual work and where the scope model falls short.

## Published result

The live submission URL is added here after Hacker News confirms publication.
