from copy import deepcopy
import pytest
from compliance.rules import evaluate_rule
from compliance.models import RuleInput
from conftest import EXAMPLE

def synthetic_rule(**extra):
    return RuleInput(rule_key="synthetic_test", workflow="aoc4", version=1,
        effective_from="2026-01-01", source_snapshot_ids=["synthetic-source"],
        required_fields=["financial_year"], trigger_field="agm_date", days_after=30,
        interpretation="Synthetic test only", **extra).model_dump(mode="json")

@pytest.mark.parametrize("field,value,status",[
    ("holding_company",True,"specialist_review"),
    ("subsidiary",True,"specialist_review"),
    ("listed",True,"specialist_review"),
    ("company_class","llp","specialist_review"),
    ("xbrl_required",True,"specialist_review"),
    ("foreign_ownership",True,"specialist_review"),
    ("regulated",True,"specialist_review"),
    ("agm_date",None,"needs_information"),
    ("agm_held",False,"specialist_review"),
    ("first_agm",True,"specialist_review"),
    ("adjourned_agm",True,"specialist_review"),
    ("statements_adopted",False,"specialist_review"),
    ("extension_evidence_ids",["review-extension"],"specialist_review"),
    ("domestic",None,"needs_information"),
])
def test_scope_and_exception_rules(field,value,status):
    facts={**deepcopy(EXAMPLE["facts"]),field:value}
    result=evaluate_rule(synthetic_rule(),facts,"2026-09-30")
    assert result["status"]==status and result["due_date"] is None
    assert result["fee_relief"] is None

@pytest.mark.parametrize("amount,expected",[
    ("99999999.99","applicable"),("100000000.00","applicable"),
    ("100000000.01","not_applicable"),("0","applicable"),(None,"needs_information")
])
def test_decimal_threshold_boundary_and_unknown(amount,expected):
    rule=synthetic_rule(conditions=[{"field":"paid_up_capital_inr","op":"lte","value":"100000000.00"}])
    facts={**EXAMPLE["facts"],"paid_up_capital_inr":amount}
    result=evaluate_rule(rule,facts,"2026-09-30")
    assert result["status"]==expected
    if expected=="applicable":
        assert result["due_date"]=="2026-10-20"

def test_effective_date_and_deadline_calculation():
    rule=synthetic_rule(effective_to="2026-12-31")
    assert evaluate_rule(rule,EXAMPLE["facts"],"2025-12-31")["status"]=="not_applicable"
    assert evaluate_rule(rule,EXAMPLE["facts"],"2027-01-01")["status"]=="not_applicable"
    facts={**EXAMPLE["facts"],"agm_date":"2026-12-20"}
    assert evaluate_rule(rule,facts,"2026-12-20")["due_date"]=="2027-01-19"

def test_unknown_comparison_does_not_become_applicable():
    rule=synthetic_rule(conditions=[{"field":"paid_up_capital_inr","op":"lte","value":"not-a-number"}])
    assert evaluate_rule(rule,EXAMPLE["facts"],"2026-09-30")["status"]=="needs_information"

def test_rule_source_and_reviewer_gates(harness):
    company,facts,_=harness.company()
    source=harness.source()
    rule=synthetic_rule()
    rule["source_snapshot_ids"]=[source["id"]]
    row=harness.request("POST","/api/rules",rule,expected=201).json()
    approval={"reviewer_notes":"Synthetic test", "fixtures":[
        {"name":"one","facts":facts,"as_of":"2026-09-30","expected_status":"applicable","expected_due_date":"2026-10-20"},
        {"name":"two","facts":{**facts,"listed":True},"as_of":"2026-09-30","expected_status":"specialist_review"}]}
    harness.request("POST",f'/api/rule-releases/{row["id"]}/approve',approval,expected=403)
    bad=deepcopy(approval)
    bad["fixtures"][0]["expected_due_date"]="2026-10-21"
    harness.request("POST",f'/api/rule-releases/{row["id"]}/approve',bad,role="content_reviewer",expected=409)
    harness.request("POST",f'/api/rule-releases/{row["id"]}/approve',approval,role="content_reviewer")
    first=harness.request("POST",f'/api/companies/{company["id"]}/evaluate',{"as_of":"2026-09-30"}).json()
    second=harness.request("POST",f'/api/companies/{company["id"]}/evaluate',{"as_of":"2026-09-30"}).json()
    assert first["obligations"][0]["id"]==second["obligations"][0]["id"]
    assert first["obligations"][0]["source_snapshot_ids"]==[source["id"]]
    assert len(first["unreleased_workflows"])==6

def test_new_source_does_not_silently_change_approved_rule(harness):
    company,facts,_=harness.company()
    source=harness.source()
    rule=harness.rule(facts,source)
    changed={k:source[k] for k in ["source_id","title","url","text","published_on","effective_from","locator","synthetic"]}
    changed["text"]="SYNTHETIC CHANGE: fee relief only. No automatic deadline extension."
    harness.request("POST","/api/sources/snapshots",changed,expected=201)
    changes=harness.request("GET","/api/sources/changes").json()["changes"]
    assert changes[0]["rules_auto_updated"] is False
    assert "fee relief" in changes[0]["diff"]
    evaluation=harness.request("POST",f'/api/companies/{company["id"]}/evaluate',{"as_of":"2026-09-30"}).json()
    ob=evaluation["obligations"][0]
    assert ob["source_snapshot_ids"]==[source["id"]] and ob["due_date"]=="2026-10-20"
    harness.request("POST",f'/api/rule-releases/{rule["id"]}/retire',{"notes":"Rollback synthetic release"},role="content_reviewer")
    evaluation=harness.request("POST",f'/api/companies/{company["id"]}/evaluate',{"as_of":"2026-09-30"}).json()
    assert evaluation["obligations"]==[]
    assert harness.request("GET",f'/api/obligations/{ob["id"]}').json()["due_date"]=="2026-10-20"

def test_draft_rule_is_not_active(harness):
    company,facts,_=harness.company()
    source=harness.source()
    body=synthetic_rule()
    body["source_snapshot_ids"]=[source["id"]]
    harness.request("POST","/api/rules",body,expected=201)
    result=harness.request("POST",f'/api/companies/{company["id"]}/evaluate',{"as_of":"2026-09-30"}).json()
    assert not result["obligations"]

def test_arbitrary_source_url_rejected(harness):
    body={"source_id":"S22","title":"Unsafe","url":"http://127.0.0.1/secrets","text":"untrusted instructions here",
          "published_on":"2026-01-01","effective_from":"2026-01-01","locator":"x","synthetic":True}
    harness.request("POST","/api/sources/snapshots",body,expected=422)
    harness.request("POST","/api/sources/S22/check",expected=503)
