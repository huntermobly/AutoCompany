from copy import deepcopy
from dataclasses import replace
import httpx
import pytest
from pydantic import ValidationError
from compliance.app import create_app
from compliance.config import Settings
from compliance.models import FactInput, RuleInput
from compliance.rules import evaluate_rule
from conftest import EXAMPLE


@pytest.mark.parametrize("workflow", ["aoc4", "mgt7", "mgt7a"])
@pytest.mark.parametrize("field", ["first_agm", "adjourned_agm", "extension_evidence_ids"])
def test_unknown_exception_facts_block_final_evaluation(workflow, field):
    rule = RuleInput(rule_key="exception_fixture", workflow=workflow, version=1,
                     effective_from="2026-01-01", source_snapshot_ids=["source"],
                     required_fields=[], interpretation="Synthetic fixture").model_dump(mode="json")
    result = evaluate_rule(rule, {**EXAMPLE["facts"], field: None}, "2026-09-30")
    assert result["status"] == "needs_information"
    assert field in result["missing_fields"]


@pytest.mark.parametrize("kind,field", [
    ("appointment", "director_consent_evidence_id"),
    ("resignation", "director_cessation_evidence_id"),
    ("other_cessation", "director_cessation_evidence_id"),
])
def test_director_evidence_is_required_by_engine(kind, field):
    rule = RuleInput(rule_key="director_fixture", workflow="dir12", version=1,
                     effective_from="2026-01-01", source_snapshot_ids=["source"],
                     required_fields=[], interpretation="Synthetic fixture").model_dump(mode="json")
    facts = {**EXAMPLE["facts"], "director_change_kind": kind, field: None}
    result = evaluate_rule(rule, facts, "2026-09-30")
    assert result["status"] == "needs_information" and field in result["missing_fields"]


def test_questionnaire_includes_approved_rule_requirements(harness):
    company, facts, _ = harness.company(full=False)
    source = harness.source()
    harness.rule(facts, source, required_fields=["employee_count"])
    q = harness.request("GET", f'/api/companies/{company["id"]}/questionnaire/aoc4?as_of=2026-09-30').json()
    assert "employee_count" in {q["field"] for q in q["questions"]}


@pytest.mark.parametrize("status,content,expected", [
    (200, b"official page captured for review", "review_required"),
    (302, b"", "fetch_failed"),
    (403, b"access denied", "fetch_failed"),
    (200, b"x" * 2_000_001, "fetch_failed"),
], ids=["ordinary", "redirect", "forbidden", "oversized"])
def test_source_monitor_is_bounded_and_never_publishes_rules(harness, status, content, expected):
    calls = []
    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(status, content=content, headers={"Location": "http://127.0.0.1/private"})
    harness.app.state.settings = replace(harness.app.state.settings, external_enabled=True)
    harness.app.state.source_client.close()
    harness.app.state.source_client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)
    try:
        result = harness.request("POST", "/api/sources/S22/check").json()
        assert result["status"] == expected and result["rules_auto_updated"] is False
        register = harness.request("GET", "/api/sources").json()["sources"]
        allowed = next(s for s in register if s["id"] == "S22")["urls"]
        assert len(calls) == 1 and calls[0] in allowed
        assert harness.request("GET", "/api/rules").json()["rules"] == []
    finally:
        harness.app.state.source_client.close()


def test_production_rejects_existing_synthetic_release(harness):
    harness.source()
    with pytest.raises(ValueError, match="active synthetic"):
        create_app(Settings(db_path=harness.app.state.database.path, mode="production"))


def test_production_blocks_mock_and_synthetic_verification(harness):
    company, _, _ = harness.company(full=False)
    harness.app.state.settings = replace(harness.app.state.settings, mode="production")
    harness.request("POST", f'/api/companies/{company["id"]}/lookup', {"provider": "mock"}, expected=409)
    source = next(s for s in harness.request("GET", "/api/sources").json()["sources"] if s["id"] == "S22")
    row = harness.request("POST", "/api/sources/snapshots", {
        "source_id": "S22", "title": "Synthetic", "url": source["urls"][0],
        "text": "SYNTHETIC TEST DATA", "published_on": "2026-01-01",
        "effective_from": "2026-01-01", "locator": "fixture", "synthetic": True}, expected=201).json()
    harness.request("POST", f'/api/sources/snapshots/{row["id"]}/verify',
                    {"notes": "synthetic"}, role="content_reviewer", expected=409)


def test_invalid_governance_values_rejected():
    meeting = deepcopy(EXAMPLE["facts"]["meetings"])
    meeting[0]["votes"] = {"for": -1}
    with pytest.raises(ValidationError):
        FactInput(field="meetings", value=meeting, valid_from="2026-01-01")
    auditor = {**EXAMPLE["facts"]["auditor"], "tenure_end": "1900-01-01"}
    with pytest.raises(ValidationError):
        FactInput(field="auditor", value=auditor, valid_from="2026-01-01")


def test_consent_revocation_wins_when_timestamps_collide(harness, monkeypatch):
    company, _, ob, _ = harness.prepared()
    from compliance import database
    monkeypatch.setattr(database, "now", lambda: "2026-09-30T00:00:00+00:00")
    identities = iter(["consent-z", "consent-a"])
    monkeypatch.setattr(database, "uuid4", lambda: next(identities))
    for allowed in [True, False]:
        harness.request("POST", f'/api/companies/{company["id"]}/consents',
                        {"purpose": "ai_explanation", "allowed": allowed, "version": "test"}, expected=201)
    harness.request("POST", f'/api/obligations/{ob["id"]}/explain',
                    {"question": "Explain", "use_ai": True}, expected=409)
