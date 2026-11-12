# India Company Compliance Backend — initial version

A backend-only preparation and evidence API for an initial segment of existing, active, domestic, unlisted private companies limited by shares. Python 3.12, Starlette, Pydantic and SQLite. There is no frontend.

The API stores all 60 profile fields across the seven information groups in your plan. Its catalog preserves all eight original tables and all 81 rows, including 28 source references. Seven workflow variants prepare worksheets: Board/AGM, AOC-4, MGT-7, MGT-7A, ADT-1, INC-20A and DIR-12.

**This is a runnable initial backend, not a released legal rulebook or an MCA filing integration.** A fresh database has no approved rules. The included demonstration explicitly uses synthetic rules, reviewer actions and receipts. Document exports are preparation worksheets, not official government forms. Read [implementation coverage](docs/IMPLEMENTATION-MATRIX.md) for the status of every plan row.

## Start on Windows / PowerShell

Run these commands from the extracted company-compliance-backend directory. Python 3.12 is the tested version.

~~~powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m compliance bootstrap
.\.venv\Scripts\python.exe -m compliance serve
~~~

The server binds to http://127.0.0.1:8000. Health: http://127.0.0.1:8000/health. Machine-readable API contract: http://127.0.0.1:8000/openapi.json. There is intentionally no dashboard or Swagger page.

Bootstrap creates a local SQLite database and five separate role tokens in .local/credentials.json. It refuses to overwrite an existing credential file. Keep that file private; it is excluded from the source package and version control. Tokens are stored as hashes in the database. A company owner must explicitly grant company access to operators, directors and professionals.

In a second PowerShell terminal:

~~~powershell
$credentials = Get-Content .local/credentials.json -Raw | ConvertFrom-Json
$headers = @{Authorization = "Bearer $($credentials.owner.token)"}
Invoke-RestMethod http://127.0.0.1:8000/api/catalog -Headers $headers
.\.venv\Scripts\python.exe scripts/demo_flow.py
~~~

The demo uses a synthetic CIN and creates a company, 60 confirmed facts, reviewed sources/rules/templates, a document pack and a manually attested filing record. It saves its output under .local/demo. Run it once per fresh database; duplicate company/rule/SRN checks deliberately prevent repeating it against the same database.

For a repeatable demonstration that creates and removes its own isolated database/server:

~~~powershell
.\.venv\Scripts\python.exe scripts/http_smoke.py
~~~

## Start on Ubuntu / WSL

~~~bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m compliance bootstrap
.venv/bin/python -m compliance serve
~~~

Use the same .venv interpreter for the demo and tests. Windows was executed during this build; the WSL commands are provided for portability and were not executed here.

## Verify

~~~powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
.\.venv\Scripts\python.exe -m pytest -q --junitxml=docs/test-results.xml
.\.venv\Scripts\python.exe scripts/http_smoke.py
~~~

On Linux, prefix pytest with PYTEST_DISABLE_PLUGIN_AUTOLOAD=1. The default suite performs no external provider calls. Live Sandbox testing is a separate opt-in; see [API setup](docs/API-SETUP.md). See [test report](docs/TEST-REPORT.md) for the executed results and their limits. No test coverage percentage is claimed.

## How the backend works

1. Create a company and upload its evidence. Add values as candidates; explicitly confirm them. Changes retain provenance, validity dates and earlier values. Conflicting confirmed values require explicit replacement.
2. Query the workflow questionnaire. It returns missing/unknown facts, nested schemas, conditional director evidence and approved-rule requirements. Saved answers remain candidates until confirmed.
3. Add dated source snapshots from the registered URLs. A separate content reviewer verifies sources and approves rules with passing positive and negative fixtures. Updated source content creates a review item; it never silently changes an active rule.
4. Evaluate confirmed facts as of a date. Each obligation records its rule, source versions, facts and deterministic deadline calculation. Unsupported entities and exceptional scenarios require specialist review.
5. Create and download a pack. Final preparation packs require complete facts and an approved template. A different professional reviews the frozen snapshot. Subsequent fact/rule changes invalidate its use for new filing actions.
6. File through the authorized government portal, then upload the actual receipt and status evidence. An SRN or download alone never completes a task. Completion requires a professional's manual attestation, matching metadata, signed-document evidence and applicable certification/payment confirmation.

The pack ZIP contains worksheet.docx, worksheet.pdf, filing-data.json, attachments.json, signature-checklist.txt and a hashed manifest. The Board/AGM variant also creates notice/agenda drafts and minutes only for meetings explicitly marked as held. The attachment index references evidence; it does not embed the original evidence files. Download originals separately using authenticated evidence routes.

## Code layout

| File or directory | Responsibility |
|---|---|
| compliance/app.py, http.py | ASGI application, request handling, OpenAPI, request limits |
| compliance/config.py, auth.py | Environment settings, hashed bearer-token authentication |
| compliance/database.py | SQLite transactions, tenant/company isolation, records and audit |
| compliance/models.py, profiles.py | Typed company facts, history, confirmation and share reconciliation |
| compliance/catalog.py, data/ | Seven field groups, workflows, exact plan tables and source register |
| compliance/evidence.py | Bounded uploads, hashes, content checks, retention and downloads |
| compliance/rules.py | Date-aware rules, applicability, scope, fixtures and approval |
| compliance/documents.py | Immutable preparation snapshots, DOCX/PDF/JSON exports |
| compliance/filings.py | Evidence-based filing state transitions |
| compliance/providers.py | Sandbox HTTP adapter, explicit mock adapter, optional OpenRouter explanations |
| compliance/routes/ | Company, legal-source, review and workflow API handlers |
| tests/ | API, isolation, rules, file exports, provider contracts and regression tests |
| scripts/ | Catalog generation and reproducible HTTP demonstration |
| prompts/ | 13 original build prompts and five runtime prompts |
| docs/original-plan.md | Full original plan, including all sources and prompts |

There are 48 authenticated API operations, plus public health and OpenAPI routes. [API endpoints](docs/API-ENDPOINTS.md) lists methods, paths and write-role restrictions.

## Configuration

The application reads process environment variables. It **does not automatically load .env**. Use .env.example as a reference and set the variables in your shell or deployment secret store.

| Variable | Default / purpose |
|---|---|
| COMPLIANCE_DB | .local/compliance.sqlite3 |
| COMPLIANCE_MODE | development; also test or production |
| ENABLE_EXTERNAL_PROVIDERS | false; only literal true enables outbound providers/monitor |
| SANDBOX_ENV | test; production selects the vendor production endpoint |
| SANDBOX_API_KEY / SANDBOX_API_SECRET | Separate vendor key and secret |
| OPENROUTER_API_KEY / OPENROUTER_MODEL | Optional AI key and explicit model ID |
| ALLOW_LIVE_TESTS / LIVE_TEST_CIN | Only used by the opt-in provider test |

The production mode blocks synthetic provider use and synthetic source/rule/template approval, and refuses a database containing already verified/approved synthetic content. This setting is **not** a production-readiness certification.

## Important initial-version limits

- No MCA account creation, CAPTCHA bypass, signature generation, automated submission or payment execution. The submit endpoint explicitly returns 501. Local edits never update government records.
- No legally certified current thresholds/deadlines/templates ship enabled. A CA/CS reviewer must verify each current route, form variant, effective period and certification policy before a real release. Demo deadlines are synthetic test arithmetic.
- Worksheets are not a complete field-by-field transcription of today's MCA web forms. Full legal notices, resolutions, auditor appointment letters and event-specific declarations require reviewed content beyond the generic worksheet templates.
- Sandbox and AI adapters have contract tests. No actual provider credentials were available, so external live success has not been demonstrated. Keys cannot be generated locally for someone else's service.
- Other obligations are collected as facts; incorporation, OPC, LLP, GST, tax, labour, state licensing and complex/regulated companies need separate modules.
- SQLite and local tokens suit development. Before hosting customer data, add managed authentication/MFA, verified professional accounts, encryption/key management, malware scanning, backups/restore tests, distributed limits, secret rotation, retention/legal review and operational monitoring. The current evidence flag explicitly says not_scanned.
- Source checks are on-demand and bounded. They record a hash and review item; scheduling, PDF/text extraction, semantic change analysis, OCR and vector retrieval are not implemented.
- Current PDF output uses an embedded DejaVu font and rejects unsupported glyphs rather than losing characters. Full Indian-language PDF shaping/font support remains to be added.
- Evidence receipts and signatures are manually attested, not parsed or cryptographically verified. Audit records cover selected important actions, not every read/write; no tamper-evident external audit store is provided.
- OpenAPI describes every request model, path and authentication requirement; response models are descriptive and need fuller schemas before generating a production client SDK.

Original prompts may describe later frontend or production work. Those portions remain future work; this deliverable follows the requested backend-only scope.
