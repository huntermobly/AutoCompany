from copy import deepcopy
import json
from pathlib import Path
import pytest
from compliance.catalog import GROUPS
from compliance.models import Facts
from conftest import EXAMPLE, ROOT

def test_all_plan_tables_and_sources_are_preserved(harness):
    catalog = harness.request("GET", "/api/catalog").json()
    text = (ROOT/"docs/original-plan.md").read_text(encoding="utf-8")
    table_lines = [line for line in text.splitlines() if line.startswith("|")]
    actual = [line for table in catalog["planning_tables"] for line in table["raw_markdown"].splitlines()]
    assert actual == table_lines
    assert len(catalog["planning_tables"]) == 8
    assert sum(len(t["rows"]) for t in catalog["planning_tables"]) == 81
    assert {s["id"] for s in catalog["sources"]} == {f"S{i}" for i in range(1,29)}
    assert set(Facts.model_fields) == set(EXAMPLE["facts"]) == {f for group in GROUPS.values() for f in group}
    assert len(GROUPS) == 7
    assert set(catalog["workflows"]) == {"board_agm","aoc4","mgt7","mgt7a","adt1","inc20a","dir12"}
    assert all(not p["file"] for p in catalog["providers"])

def test_every_profile_field_roundtrips_with_evidence(harness):
    company, facts, evidence = harness.company()
    result = harness.request("GET", f'/api/companies/{company["id"]}?as_of=2026-09-30').json()
    assert result["confirmed_facts"] == Facts.model_validate(facts).model_dump(mode="json")
    assert set(result["fact_versions"]) == set(Facts.model_fields)
    assert result["scope"]["status"] == "supported"
    rows = harness.request("GET", f'/api/companies/{company["id"]}/facts').json()["facts"]
    assert all(r["evidence_id"] == evidence["id"] and r["confirmed_by"] == harness.identities["owner"]["id"] for r in rows)
    structure = harness.request("GET", f'/api/companies/{company["id"]}/structure?as_of=2026-09-30').json()
    assert structure["ownership"]["shareholdings"][0]["shares"] == 6000
    assert len(structure["governance"]["directors"]) == 2
    export = harness.request("GET", f'/api/companies/{company["id"]}/export').json()
    assert any(r["kind"] == "fact" for r in export["records"])

@pytest.mark.parametrize("field,value", [
    ("unknown_field",1), ("turnover_inr",-1), ("turnover_inr",True), ("turnover_inr","NaN"),
    ("paid_up_capital_inr","1.234"), ("employee_count",-1),
    ("financial_year",{"start":"2026-04-01","end":"2026-03-31"}),
    ("registered_address",{"line1":"x","city":"x","state":"x","pin":"abc"}),
    ("directors",[{"name":"x","din":"bad","appointment_date":"2024-01-01"}]),
])
def test_invalid_fact_rejected(harness, field, value):
    company,_,_ = harness.company(full=False)
    harness.request("POST", f'/api/companies/{company["id"]}/facts',
                    {"field":field,"value":value,"valid_from":"2026-04-01"},expected=422)

def test_unknown_is_not_zero(harness):
    company,_,_ = harness.company(full=False)
    path=f'/api/companies/{company["id"]}'
    row=harness.request("POST", path+"/facts",{"field":"turnover_inr","value":None,"valid_from":"2026-04-01"},expected=201).json()
    harness.request("POST",path+"/facts/confirm",{"fact_ids":[row["id"]]})
    q=harness.request("GET",path+"/questionnaire/mgt7a?as_of=2026-09-30").json()
    assert next(v for v in q["questions"] if v["field"]=="turnover_inr")["answer_state"]=="unknown"
    assert not q["complete"]

def test_conflict_requires_explicit_confirmation_and_preserves_history(harness):
    company,_,_ = harness.company()
    path=f'/api/companies/{company["id"]}'
    candidate=harness.request("POST",path+"/facts",{"field":"name","value":"Changed legal name","valid_from":"2026-10-01"},expected=201).json()
    harness.request("POST",path+"/facts/confirm",{"fact_ids":[candidate["id"]]},expected=409)
    harness.request("POST",path+"/facts/confirm",{"fact_ids":[candidate["id"]],"replace_conflicts":True})
    old=harness.request("GET",path+"?as_of=2026-09-30").json()
    new=harness.request("GET",path+"?as_of=2026-10-01").json()
    assert old["confirmed_facts"]["name"]==EXAMPLE["name"]
    assert new["confirmed_facts"]["name"]=="Changed legal name"

def test_shareholding_inconsistency_rolls_back(harness):
    company,_,_ = harness.company()
    path=f'/api/companies/{company["id"]}'
    before=harness.request("GET",path).json()["revision"]
    bad=harness.request("POST",path+"/facts",{"field":"shareholdings","value":[{"member_id":"member-a","class_id":"equity","shares":1}],"valid_from":"2026-04-01"},expected=201).json()
    harness.request("POST",path+"/facts/confirm",{"fact_ids":[bad["id"]],"replace_conflicts":True},expected=422)
    assert harness.request("GET",path).json()["revision"]==before
    assert next(r for r in harness.request("GET",path+"/facts").json()["facts"] if r["id"]==bad["id"])["status"]=="candidate"

def test_questionnaire_answer_save_and_conditional_fields(harness):
    company,_,_=harness.company(full=False)
    path=f'/api/companies/{company["id"]}'
    row=harness.request("POST",path+"/questionnaire/dir12/answers",{"answers":[
        {"field":"director_change_kind","value":"resignation","valid_from":"2026-04-01"}]},expected=201).json()
    assert row["confirmation_required"]
    harness.request("POST",path+"/facts/confirm",{"fact_ids":row["candidate_fact_ids"]})
    q=harness.request("GET",path+"/questionnaire/dir12?as_of=2026-09-30").json()
    fields={x["field"] for x in q["questions"]}
    assert "director_cessation_evidence_id" in fields and "director_consent_evidence_id" not in fields

def test_duplicate_company_invalid_identifier_and_unknown_query(harness):
    harness.request("POST","/api/companies",{"cin":"invalid","name":"x"},expected=422)
    company,_,_=harness.company(full=False)
    harness.request("POST","/api/companies",{"cin":company["cin"],"name":"x"},expected=409)
    harness.request("GET",f'/api/companies/{company["id"]}?as_of=bad',expected=422)
