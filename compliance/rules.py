"""Deterministic, date-aware evaluations. Nothing in this module invents current law."""
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from starlette.exceptions import HTTPException
from .catalog import WORKFLOWS, required_fields
from .database import all_records, audit, digest, get, insert, now, update
from .profiles import scope, values_at

def comparison(clause, facts):
    left = facts.get(clause["field"])
    if left is None:
        return None
    right = clause["value"]
    op = clause["op"]
    if clause["field"].endswith("_inr"):
        try:
            left, right = Decimal(str(left)), Decimal(str(right))
        except InvalidOperation:
            return None
    try:
        return {"eq": lambda: type(left) is type(right) and left == right,
                "ne": lambda: not (type(left) is type(right) and left == right),
                "lt": lambda: left < right, "lte": lambda: left <= right,
                "gt": lambda: left > right, "gte": lambda: left >= right,
                "contains": lambda: right in left}[op]()
    except (TypeError, KeyError):
        return None

def evaluate_rule(rule, facts, as_of):
    out = {"status": "needs_information", "due_date": None, "statutory_due_date": None,
           "extension": None, "fee_relief": None, "missing_fields": [], "trace": []}
    if as_of < rule["effective_from"] or (rule.get("effective_to") and as_of > rule["effective_to"]):
        return {**out, "status": "not_applicable", "reason": "Rule outside effective period"}
    scoped = scope(facts)
    out["scope"] = scoped
    if scoped["status"] == "specialist_review":
        return {**out, "status": "specialist_review", "reason": "Entity outside initial supported segment"}
    clauses = [(False, c) for c in rule["conditions"]] + [(True, c) for c in rule["exclusions"]]
    clause_missing = []
    for exclude, clause in clauses:
        result = comparison(clause, facts)
        out["trace"].append({"clause": clause, "result": result, "exclusion": exclude})
        if result is None:
            clause_missing.append(clause["field"])
        if (exclude and result is True) or (not exclude and result is False):
            return {**out, "status": "not_applicable", "reason": "Applicability condition not met"}
    required = rule["required_fields"] + rule["required_evidence_fields"] + required_fields(rule["workflow"], facts) + scoped["missing"]
    if rule.get("trigger_field"):
        required.append(rule["trigger_field"])
    out["missing_fields"] = sorted({f for f in required if facts.get(f) is None} | set(clause_missing))
    if out["missing_fields"]:
        return {**out, "reason": "Required confirmed facts are missing"}
    if rule["workflow"] in {"aoc4", "mgt7", "mgt7a"}:
        if facts.get("agm_held") is False or facts.get("first_agm") is True or facts.get("adjourned_agm") is True or facts.get("extension_evidence_ids"):
            return {**out, "status": "specialist_review", "reason": "Exceptional AGM or extension requires a separate reviewed route"}
    if rule["workflow"] == "aoc4" and facts.get("statements_adopted") is False:
        return {**out, "status": "specialist_review", "reason": "Unadopted statements require a separately reviewed route"}
    if rule["workflow"] == "adt1" and facts.get("auditor_appointment_kind") == "first":
        return {**out, "status": "specialist_review", "reason": "First appointment route must be separately verified"}
    if rule.get("trigger_field"):
        try:
            due = date.fromisoformat(facts[rule["trigger_field"]]) + timedelta(days=rule["days_after"])
        except (TypeError, ValueError, OverflowError):
            return {**out, "status": "specialist_review", "reason": "Invalid deadline trigger"}
        out["due_date"] = out["statutory_due_date"] = due.isoformat()
    return {**out, "status": "applicable", "reason": "Reviewed rule and confirmed facts matched"}

def approve_rule(db, principal, identity, body, mode):
    rule = get(db, "rule", identity, principal)
    if rule["status"] != "draft":
        raise HTTPException(409, "Only draft rules can be approved")
    if rule["authored_by"] == principal["id"]:
        raise HTTPException(403, "Rule author cannot approve their own rule")
    if mode == "production" and rule["synthetic"]:
        raise HTTPException(409, "Synthetic rules cannot be activated in production")
    for source_id in rule["source_snapshot_ids"]:
        source = get(db, "source_snapshot", source_id, principal)
        if source["status"] != "verified" or (source["synthetic"] and not rule["synthetic"]):
            raise HTTPException(409, "Rule requires appropriately verified source snapshots")
    cases = body.fixtures
    if len({c.name for c in cases}) != len(cases) or not any(c.expected_status != "applicable" for c in cases):
        raise HTTPException(422, "Fixtures require distinct names and a non-applicable/missing/exception case")
    for case in cases:
        result = evaluate_rule(rule, case.facts.model_dump(mode="json", exclude_none=True), case.as_of.isoformat())
        expected_date = case.expected_due_date.isoformat() if case.expected_due_date else None
        if result["status"] != case.expected_status or result["due_date"] != expected_date:
            raise HTTPException(409, {"message": "Regression fixture failed", "fixture": case.name, "actual": result})
    for other in all_records(db, "rule", principal):
        if other["id"] != identity and other["rule_key"] == rule["rule_key"] and other["status"] == "approved":
            if other["effective_from"] <= (rule.get("effective_to") or "9999-12-31") and rule["effective_from"] <= (other.get("effective_to") or "9999-12-31"):
                raise HTTPException(409, "Approved versions of the same rule cannot overlap")
    result = update(db, rule, {"status": "approved", "reviewed_by": principal["id"], "reviewed_at": now(),
                              "reviewer_notes": body.reviewer_notes,
                              "fixtures": [c.model_dump(mode="json") for c in cases]})
    audit(db, principal, "rule.approved", identity)
    return result

def evaluate_company(db, principal, company_id, as_of):
    company = get(db, "company", company_id, principal)
    facts, fact_versions = values_at(db, principal, company_id, as_of)
    active = [r for r in all_records(db, "rule", principal) if r["status"] == "approved"
              and r["effective_from"] <= as_of and (not r.get("effective_to") or r["effective_to"] >= as_of)]
    outputs = []
    for rule in active:
        result = evaluate_rule(rule, facts, as_of)
        fingerprint = digest({"rule": rule["id"], "facts": fact_versions, "as_of": as_of, "revision": company["revision"]})
        existing = next((x for x in all_records(db, "obligation", principal, company_id) if x["fingerprint"] == fingerprint), None)
        if existing:
            outputs.append(existing)
            continue
        payload = {**result, "workflow": rule["workflow"], "form": WORKFLOWS[rule["workflow"]]["form"],
                   "rule_id": rule["id"], "rule_version": rule["version"], "source_snapshot_ids": rule["source_snapshot_ids"],
                   "fact_versions": fact_versions, "facts_snapshot": facts, "company_revision": company["revision"],
                   "as_of": as_of, "fingerprint": fingerprint, "synthetic": rule["synthetic"], "filing_status": "not_started",
                   "responsible_principal_id": principal["id"], "professional_certification_required": rule["professional_certification_required"]}
        outputs.append(insert(db, "obligation", principal, payload, company_id))
    covered = {r["workflow"] for r in active}
    return {"company_id": company_id, "as_of": as_of, "scope": scope(facts),
            "obligations": outputs, "unreleased_workflows": sorted(set(WORKFLOWS) - covered),
            "coverage": "Limited to explicitly approved preparation rules; no overall compliance certification"}

