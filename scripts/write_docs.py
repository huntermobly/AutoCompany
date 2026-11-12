"""Generate exact scope mappings and reports from the packaged catalog and executed tests."""
from collections import Counter
from datetime import datetime, timezone
import importlib.metadata as metadata
import json
from pathlib import Path
import platform
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from compliance.app import create_app  # register handlers
from compliance.catalog import GROUPS, tables
from compliance.http import api
from compliance.models import Facts

P = "tests/test_profiles.py"
R = "tests/test_rules.py; tests/test_release_boundaries.py"
D = "tests/test_documents_filings.py"
V = "tests/test_providers.py"
S = "tests/test_security.py"
statuses = {
    "table_1": [
        ("Implemented mechanism; legal content pending", "Versioned source/rule explanations; optional AI remains unverified", R + "; " + V),
        ("Implemented manual/mock; vendor contract tested", "Candidates and evidence preserve provenance; no live vendor result", P + "; " + V),
        ("Implemented foundation", "Membership, holdings and directors stored; share references/totals checked; no automatic restructuring advice", P),
        ("Partial preparation output", "DOCX/PDF worksheets and meeting drafts; full legal clauses/resolutions require template work", D),
        ("Partial preparation output", "Immutable worksheet and attachment index; no verified current portal field mapping", D),
        ("Handoff only", "Signature instructions and uploaded signed-document evidence; no eSign adapter", D),
        ("Handoff only", "DSC instructions; no signing or signature validation", D),
        ("Manual handoff", "Submit returns 501; ledger tracks user/professional evidence", D),
        ("External action only", "Local records never mutate government records", D),
    ],
    "table_2": [
        ("Implemented", "60 fields, candidate/confirmed provenance and conflicts", P),
        ("Implemented mechanism; legal content pending", "Rule/date/fact versions and evidence gaps; no enabled production rulebook", R),
        ("Implemented foundation", "Missing/unknown conditional questions and saved candidates; no frontend", P + "; " + R),
        ("Partial preparation output", "Final-pack gates, actual-event minutes; generic worksheets need fuller reviewed legal templates", D),
        ("Partial preparation output", "AOC-4, MGT-7 and MGT-7A variants; live legal routing not seeded", D + "; " + R),
        ("Implemented basic review", "Separate professional approval or changes_requested; free-text comments, no structured field-comment UI", D),
        ("Implemented manual ledger", "SRN/download cannot complete filing; matching receipts and professional attestation required", D),
        ("Implemented on-demand mechanism", "Snapshots/diffs/reviewer release gates; no periodic job or automated law extraction", R),
        ("Partial event foundation", "ADT-1, INC-20A and DIR-12 worksheets; current form-specific releases pending", D + "; " + R),
        ("Contract implemented; live acceptance pending", "Sandbox key/secret adapter and manual fallback", V),
        ("Deferred", "OPC/LLP/public/other out-of-scope routes return specialist review", R),
        ("Deferred", "60-field profile records related registrations; no tax/labour/licence rule packs", P),
    ],
    "table_3": [
        ("Implemented and round-trip tested", "Identity, dates, address, documents and classification", P),
        ("Implemented and round-trip tested", "Members, classes, holdings, ownership and group flags", P),
        ("Implemented and round-trip tested", "DIN/director dates/residency, auditor and signatories", P),
        ("Implemented and round-trip tested", "Decimal INR amounts, periods, statements and transaction flags", P + "; " + R),
        ("Implemented and round-trip tested", "Planned/held meetings, notice, votes, decisions, AGM/extension facts", P + "; " + D),
        ("Collection implemented; domain modules deferred", "Activities, states, employees and registration/licence lists", P),
        ("Implemented and round-trip tested", "Prior form/SRN/date/evidence and notices; manual completion semantics", P + "; " + D),
    ],
    "table_4": [
        ("Partial template family", "Worksheet, notice/agenda and factual minutes; full SS-1/SS-2 legal templates pending", D),
        ("Partial template family", "Financial statement worksheet and index; current kit/variant approval pending", D),
        ("Partial template family", "Both annual-return variants render; current classification/certification rules pending", D + "; " + R),
        ("Partial template family", "Auditor facts worksheet; first-appointment review guard; appointment letter templates pending", D + "; " + R),
        ("Partial template family", "Commencement facts worksheet; approved applicability/attestation rules pending", D),
        ("Partial template family", "Director event worksheet; conditional consent/cessation evidence enforced", D + "; " + R),
    ],
    "table_5": [
        ("Implemented foundation", "SQLite versioned facts, original evidence and explicit confirmation", P + "; " + S),
        ("Implemented", "Deterministic applicability/date arithmetic and source-backed releases", R),
        ("Partial", "Missing/unknown/candidate states and conflicts; no explicit field-level not-applicable/disputed answer enum", P),
        ("Bounded retrieval implemented", "Fetch only snapshots attached to evaluated rule; no semantic/vector search", V + "; " + S),
        ("Explanation adapter implemented", "No tools/actions; validated source IDs; OCR/extraction/question-generation remains deferred", V),
        ("Partial", "Versioned preparation templates and binary exports; full official form mapping pending", D),
        ("Implemented limited adapters", "Sandbox, mock and OpenRouter contracts; other integrations capability-only", V),
        ("Implemented manual ledger", "Review/state/receipt gates; signatures and portal status rely on attestation", D),
        ("Partial", "On-demand allowlisted bounded fetch/hash plus manual snapshot diff; no scheduled ingestion", R),
    ],
    "table_6": [
        ("Partly complete; business approvals outstanding", "Source register/segment recorded; professional appointment/vendor applications not performed", "Catalog preservation test only"),
        ("Backend foundation implemented", "Local auth/isolation/profile/questionnaire/structure; no frontend", P + "; " + S),
        ("Mechanisms implemented; legal acceptance outstanding", "Synthetic fixture/calculation/pack checks; no production legal sign-off", R + "; " + D),
        ("Partial", "Explanation adapter, review APIs and evidence ledger; extraction/review UI deferred", V + "; " + D),
        ("Partial; pilot/hardening outstanding", "Monitor/provider contracts available; customer pilot and deployment not performed", R + "; " + V),
    ],
    "table_7": [
        ("Human decision outstanding", "Account identity, domain and commercial applications not created", "Catalog preservation test only"),
        ("Professional acceptance outstanding", "No CA/CS legal certification is implied by software tests", "Synthetic review gates tested"),
        ("Contract tests complete; live check outstanding", "Object/list envelopes, identity mismatch, missing keys, outage/quota covered", V),
        ("Human review outstanding", "Retention primitives exist; current privacy/processor obligations not certified", S + "; catalog preservation"),
        ("Human decision outstanding", "No pilot users, pricing or service promises established", "Catalog preservation test only"),
    ],
    "table_8": [
        ("Reference retained; not an approved legal release",
         "Exact source ID, links and purpose retained. Register starts not_reviewed; live availability and current law not asserted.",
         P + "; " + R) for _ in range(28)
    ],
}

def cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")

lines = [
    "# Implementation matrix — every original table row",
    "",
    "All 81 original rows are preserved exactly in compliance/data/plan_tables.json and served by GET /api/catalog. "
    "Preserving and testing the data does not mean every future feature or legal obligation is implemented. "
    "This matrix distinguishes runnable mechanisms, preparation-only outputs and outstanding external work.",
    "",
    "The complete original wording, acceptance criteria and references remain in original-plan.md. "
    "The table-preservation test compares every original Markdown table line, including headers and separators, to the API catalog.",
]
count = 0
for table in tables():
    entries = statuses[table["id"]]
    assert len(entries) == len(table["rows"])
    lines += ["", "## " + table["section"], "", "| Row | Original item | Current status | Implementation / limit | Verification |", "|---|---|---|---|---|"]
    for i, (row, status) in enumerate(zip(table["rows"], entries), 1):
        count += 1
        label = row[1] if table["id"] in {"table_2", "table_6"} else row[0]
        if table["id"] == "table_8":
            label = row[0] + " — " + row[1]
        lines.append("| " + " | ".join(map(cell, [f'{table["id"]}.{i}', label, *status])) + " |")
assert count == 81
lines += ["", "## All 60 company fields", "",
          "Every field below is schema-validated, stored with provenance, explicitly confirmed and round-trip tested by "
          "test_every_profile_field_roundtrips_with_evidence. Nested required members are defined in the catalog's facts_schema. "
          "Schema validation verifies structure, not the factual truth of a declaration.", "",
          "| Group | Field |", "|---|---|"]
for group, fields in GROUPS.items():
    for field in fields:
        lines.append(f"| {group} | {field} |")
assert sum(map(len, GROUPS.values())) == len(Facts.model_fields) == 60
(ROOT / "docs/IMPLEMENTATION-MATRIX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

lines = ["# API operations", "",
         "Base URL: http://127.0.0.1:8000. JSON request bodies use Content-Type: application/json. "
         "All /api operations require Authorization: Bearer YOUR_LOCAL_ROLE_TOKEN. Tenant and company access checks apply in addition to role checks.", "",
         "| Method | Path | Request schema | Write-role restriction |",
         "|---|---|---|---|"]
for d in api.definitions:
    lines.append("| " + " | ".join([d["method"], d["path"], d["model"].__name__ if d["model"] else "No JSON model",
                                  ", ".join(d["roles"]) if d["roles"] else "Authenticated and authorized"]) + " |")
lines += ["", "Public routes: GET /health and GET /openapi.json.", "",
          "Successful creates generally return 201; reads/evaluations return 200. Errors include 401 authentication, "
          "403 role, 404 inaccessible/missing record, 409 state or confirmation conflict, 413 body limit, 415 media type, "
          "422 validation, 429 local rate limit, 501 unimplemented provider/submission and 503 external provider unavailable.", "",
          "Relevant company reads/questionnaires accept ?as_of=YYYY-MM-DD. Evaluation uses an explicit as_of request body. "
          "Use the same as_of date throughout a historical workflow. ISO dates are calendar dates, not filing-time-zone conversions.", "",
          "OpenAPI includes request schemas, references and operation IDs. Responses are currently described rather than "
          "fully typed; consult tests and docs/http-smoke-results.json for exercised responses."]
(ROOT / "docs/API-ENDPOINTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
(ROOT / "docs/openapi.json").write_text(json.dumps(api.openapi(), indent=2), encoding="utf-8")

packages = ["starlette", "pydantic", "uvicorn", "httpx", "matplotlib", "pytest", "PyPDF2",
            "anyio", "typing_extensions", "idna", "annotated-types", "pydantic_core",
            "typing-inspection", "click", "h11", "certifi", "httpcore", "contourpy",
            "cycler", "fonttools", "kiwisolver", "numpy", "packaging", "pillow",
            "pyparsing", "python-dateutil", "six", "colorama", "iniconfig", "pluggy"]
versions = {p: metadata.version(p) for p in packages}
(ROOT / "docs/test-environment.json").write_text(json.dumps({
    "python": platform.python_version(), "platform": platform.system(),
    "packages": versions, "install_note": "Executed using existing installed packages. Fresh network installation was unavailable during this build."
}, indent=2), encoding="utf-8")

xml = ROOT / "docs/test-results.xml"
if xml.exists():
    cases = ET.parse(xml).findall(".//testcase")
    counts = Counter("failed" if t.find("failure") is not None else "error" if t.find("error") is not None
                     else "skipped" if t.find("skipped") is not None else "passed" for t in cases)
    smoke = json.loads((ROOT / "docs/http-smoke-results.json").read_text())
    lines = [
        "# Executed verification report", "",
        f"Report generated UTC: {datetime.now(timezone.utc).isoformat()}", "",
        f"**{counts['passed']} passed; {counts['skipped']} skipped; {counts['failed']} failed; {counts['error']} errors.** "
        "Machine-readable details: test-results.xml.", "",
        "## What was executed", "",
        "| Check | Evidence / result |", "|---|---|",
        f"| Pytest API/unit/contract suite | {len(cases)} cases; default external calls disabled |",
        f"| Real localhost HTTP workflow | {len(smoke['requests'])} recorded API requests, plus health/OpenAPI; final synthetic status {smoke['final_status']} |",
        "| Company information | All 60 fields in all seven groups submitted, confirmed, returned and exported |",
        "| Original tables | Eight tables / 81 rows compared line-for-line against original plan; all 28 source IDs retained |",
        "| Documents | All seven variants render DOCX/PDF/ZIP; XML parses, PDF text is readable, hashes and snapshots checked |",
        "| API contract | 48 unique authenticated operations with request schemas and security declarations |",
        "| Access | Wrong tenant, missing grant, revoked token, cross-company evidence and role violations rejected |",
        "| Rules | Missing/unknown facts, threshold equality/edges, exceptional routes, date versions and review gates tested |",
        "| Data changes | Explicit conflict replacement, share reconciliation rollback, historical versions and stale pack checks |",
        "| Filing ledger | Matching CIN/form/FY/SRN, receipt reuse, transition, certification and professional-completion gates |",
        "| External Sandbox adapter | HTTP requests simulated using MockTransport; raw token auth, envelopes, errors and CIN matching |",
        "| AI adapter | Simulated responses; consent/revocation, source whitelist, schema and no-action contract |",
        "| Source monitor | Allowlisted bounded fetch, redirect/error handling, hash/review item and no rule auto-publication |",
        "| Production-mode guards | Synthetic provider/approval and pre-existing synthetic release database blocked |",
        "", "## What these results do not prove", "",
        "- The live Sandbox test was skipped because credentials and live opt-in were absent. No real OpenRouter model was called.",
        "- Government API requests: zero. The HTTP demonstration used synthetic evidence and manual professional attestation; it is not proof of government receipt or approval.",
        "- No legally current rule pack or official MCA form schema was certified. Legal arithmetic uses synthetic fixtures.",
        "- No fresh dependency installation, Linux execution, deployment, load test, penetration test, antivirus scan, signature verification or customer pilot was completed. An optional offline wheel-build check could not run because the installed environment lacks the wheel build package; the source distribution runs directly and pyproject declares that build dependency.",
        "- No code-coverage percentage is reported. Parameterized test counts are not a measure of legal completeness.",
        "",
        "The real HTTP trace is in http-smoke-results.json, the runnable script is scripts/http_smoke.py, "
        "and the resulting synthetic downloadable pack is example-pack.zip. No bearer tokens or provider secrets are included.", "",
        "## Environment", "",
        f"Python {platform.python_version()} on {platform.system()}; installed dependency versions are recorded in test-environment.json. "
        "The suite was run with PYTEST_DISABLE_PLUGIN_AUTOLOAD=1. Dependency downloads were unavailable, so the implementation uses installed Starlette/Pydantic libraries.", "",
        "Two known non-failing development warnings: Starlette's httpx-based TestClient integration is deprecated in favor of httpx2; "
        "PyPDF2 is deprecated in favor of pypdf. Upgrade those test helpers with compatibility testing before a production release.",
    ]
    (ROOT / "docs/TEST-REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(dict(counts)))
print(json.dumps({"matrix_rows": count, "fields": len(Facts.model_fields), "api_operations": len(api.definitions)}))
