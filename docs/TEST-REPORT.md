# Executed verification report

Report generated UTC: 2026-11-11T22:21:10.019602+00:00

**109 passed; 1 skipped; 0 failed; 0 errors.** Machine-readable details: test-results.xml.

## What was executed

| Check | Evidence / result |
|---|---|
| Pytest API/unit/contract suite | 110 cases; default external calls disabled |
| Real localhost HTTP workflow | 84 recorded API requests, plus health/OpenAPI; final synthetic status recorded |
| Company information | All 60 fields in all seven groups submitted, confirmed, returned and exported |
| Original tables | Eight tables / 81 rows compared line-for-line against original plan; all 28 source IDs retained |
| Documents | All seven variants render DOCX/PDF/ZIP; XML parses, PDF text is readable, hashes and snapshots checked |
| API contract | 48 unique authenticated operations with request schemas and security declarations |
| Access | Wrong tenant, missing grant, revoked token, cross-company evidence and role violations rejected |
| Rules | Missing/unknown facts, threshold equality/edges, exceptional routes, date versions and review gates tested |
| Data changes | Explicit conflict replacement, share reconciliation rollback, historical versions and stale pack checks |
| Filing ledger | Matching CIN/form/FY/SRN, receipt reuse, transition, certification and professional-completion gates |
| External Sandbox adapter | HTTP requests simulated using MockTransport; raw token auth, envelopes, errors and CIN matching |
| AI adapter | Simulated responses; consent/revocation, source whitelist, schema and no-action contract |
| Source monitor | Allowlisted bounded fetch, redirect/error handling, hash/review item and no rule auto-publication |
| Production-mode guards | Synthetic provider/approval and pre-existing synthetic release database blocked |

## What these results do not prove

- The live Sandbox test was skipped because credentials and live opt-in were absent. No real OpenRouter model was called.
- Government API requests: zero. The HTTP demonstration used synthetic evidence and manual professional attestation; it is not proof of government receipt or approval.
- No legally current rule pack or official MCA form schema was certified. Legal arithmetic uses synthetic fixtures.
- No fresh dependency installation, Linux execution, deployment, load test, penetration test, antivirus scan, signature verification or customer pilot was completed. An optional offline wheel-build check could not run because the installed environment lacks the wheel build package; the source distribution runs directly and pyproject declares that build dependency.
- No code-coverage percentage is reported. Parameterized test counts are not a measure of legal completeness.

The real HTTP trace is in http-smoke-results.json, the runnable script is scripts/http_smoke.py, and the resulting synthetic downloadable pack is example-pack.zip. No bearer tokens or provider secrets are included.

## Environment

Python 3.12.4 on Windows; installed dependency versions are recorded in test-environment.json. The suite was run with PYTEST_DISABLE_PLUGIN_AUTOLOAD=1. Dependency downloads were unavailable, so the implementation uses installed Starlette/Pydantic libraries.

Two known non-failing development warnings: Starlette's httpx-based TestClient integration is deprecated in favor of httpx2; PyPDF2 is deprecated in favor of pypdf. Upgrade those test helpers with compatibility testing before a production release.
