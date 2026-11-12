from datetime import date, timedelta
from starlette.exceptions import HTTPException
from .database import all_records, audit, get, insert, now, update

def values_at(db, principal, company_id, as_of):
    values, versions = {}, {}
    for row in all_records(db, "fact", principal, company_id):
        if row["status"] != "confirmed" or row["valid_from"] > as_of:
            continue
        if row["valid_to"] and row["valid_to"] < as_of:
            continue
        current = versions.get(row["field"])
        if current is None or row["confirmation_sequence"] > current["confirmation_sequence"]:
            versions[row["field"]] = row
            values[row["field"]] = row["value"]
    return values, {k: v["id"] for k, v in versions.items()}

def validate_references(db, principal, company_id, field, value):
    refs = []
    if field.endswith("_evidence_id") and value:
        refs = [value]
    elif field == "extension_evidence_ids" and value:
        refs = value
    elif field == "prior_filings" and value:
        refs = [v["evidence_id"] for v in value]
    for identity in refs:
        e = get(db, "evidence", identity, principal)
        if e["company_id"] != company_id or e.get("deleted"):
            raise HTTPException(422, "Evidence must belong to this company and be retained")

def add_fact(db, principal, company_id, body):
    get(db, "company", company_id, principal)
    if body.evidence_id:
        validate_references(db, principal, company_id, "source_evidence_id", body.evidence_id)
    validate_references(db, principal, company_id, body.field, body.value)
    return insert(db, "fact", principal, {**body.model_dump(mode="json"), "status": "candidate",
                  "confirmed_by": None, "confirmed_at": None, "confirmation_sequence": 0}, company_id)

def validate_structure(values):
    for field, key in [("members", "member_id"), ("share_classes", "class_id"), ("directors", "din")]:
        rows = values.get(field) or []
        if len({r[key] for r in rows}) != len(rows):
            raise HTTPException(422, f"Duplicate identifier in {field}")
    if all(values.get(k) is not None for k in ("members", "share_classes", "shareholdings")):
        members = {x["member_id"] for x in values["members"]}
        classes = {x["class_id"]: x for x in values["share_classes"]}
        totals = {key: 0 for key in classes}
        for h in values["shareholdings"]:
            if h["member_id"] not in members or h["class_id"] not in classes:
                raise HTTPException(422, "Shareholding references an unknown member or class")
            totals[h["class_id"]] += h["shares"]
        if any(totals[k] != v["issued_shares"] for k, v in classes.items()):
            raise HTTPException(422, "Holdings must reconcile with issued shares per class")

def confirm(db, principal, company_id, body):
    company = get(db, "company", company_id, principal)
    if len(body.fact_ids) != len(set(body.fact_ids)):
        raise HTTPException(422, "Duplicate fact IDs")
    candidates = [get(db, "fact", identity, principal) for identity in body.fact_ids]
    if any(r["company_id"] != company_id for r in candidates):
        raise HTTPException(422, "Fact belongs to another company")
    if any(r["status"] != "candidate" for r in candidates):
        raise HTTPException(409, "Only unconfirmed candidates can be confirmed")
    if len({r["field"] for r in candidates}) != len(candidates):
        raise HTTPException(422, "Confirm one version of each field at a time")
    for row in candidates:
        for old in all_records(db, "fact", principal, company_id):
            overlap = old["valid_from"] <= (row["valid_to"] or "9999-12-31") and row["valid_from"] <= (old["valid_to"] or "9999-12-31")
            if old["field"] == row["field"] and old["status"] == "confirmed" and overlap and old["value"] != row["value"] and not body.replace_conflicts:
                raise HTTPException(409, {"message": "Conflicting confirmed fact; explicit replacement required", "field": row["field"], "existing_fact_id": old["id"]})
    revision = company["revision"] + 1
    for row in candidates:
        update(db, row, {"status": "confirmed", "confirmed_by": principal["id"], "confirmed_at": now(), "confirmation_sequence": revision})
    history = all_records(db, "fact", principal, company_id)
    boundaries = {r["valid_from"] for r in history}
    for row in history:
        if row["valid_to"] and row["valid_to"] < "9999-12-31":
            boundaries.add((date.fromisoformat(row["valid_to"]) + timedelta(days=1)).isoformat())
    for boundary in boundaries:
        values, _ = values_at(db, principal, company_id, boundary)
        validate_structure(values)
    update(db, company, {"revision": revision})
    audit(db, principal, "facts.confirmed", company_id, company_id)
    return {"company_id": company_id, "revision": revision, "confirmed_fact_ids": body.fact_ids}

def scope(values):
    expected = {"company_class": "private", "company_status": "active", "domestic": True,
                "limited_by_shares": True, "listed": False, "regulated": False,
                "government_company": False, "holding_company": False, "subsidiary": False,
                "foreign_ownership": False, "xbrl_required": False, "ind_as_required": False,
                "complex_securities": False}
    mismatch = [k for k, v in expected.items() if values.get(k) is not None and values[k] != v]
    missing = [k for k in expected if values.get(k) is None]
    return {"status": "specialist_review" if mismatch else ("needs_information" if missing else "supported"),
            "reasons": mismatch, "missing": missing}

