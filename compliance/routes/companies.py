import base64
from datetime import date
import json
from starlette.exceptions import HTTPException
from starlette.responses import Response
from .. import catalog, evidence, profiles, rules
from ..database import all_records, audit, get, insert, update
from ..http import api
from ..models import (Ask, CompanyCreate, Consent, EvaluationRequest, EvidenceInput, FactConfirm,
                      FactInput, Facts, Grant, Lookup, QuestionnaireAnswer, Retention)
from ..providers import MockProvider, ProviderFailure, as_http

WRITE = ["owner", "operator", "professional"]

def as_of(ctx):
    try:
        return date.fromisoformat(ctx.query.get("as_of", date.today().isoformat())).isoformat()
    except ValueError:
        raise HTTPException(422, "as_of must be an ISO calendar date")

@api.route("GET", "/api/me")
def me(c, body):
    return c.principal

@api.route("GET", "/api/catalog")
def catalog_get(c, body):
    return {"groups": catalog.GROUPS, "facts_schema": Facts.model_json_schema(),
            "workflows": catalog.WORKFLOWS, "providers": catalog.PROVIDERS, "sources": catalog.sources(),
            "planning_tables": catalog.tables(), "government_submission": False,
            "source_register_is_not_an_approved_rulebook": True}

@api.route("GET", "/api/integrations")
def integrations(c, body):
    s = c.app.state.settings
    return {"external_enabled": s.external_enabled,
            "sandbox_configured": bool(s.sandbox_key and s.sandbox_secret),
            "ai_configured": bool(s.ai_key and s.ai_model), "sandbox_environment": s.sandbox_env,
            "providers": catalog.PROVIDERS, "live_connectivity_verified": False,
            "direct_government_filing": False}

@api.route("POST", "/api/companies", CompanyCreate, roles=["owner"], status=201)
def company_create(c, body):
    if any(x["cin"] == body.cin for x in all_records(c.db, "company", c.principal)):
        raise HTTPException(409, "Company already exists in this tenant")
    row = insert(c.db, "company", c.principal, {**body.model_dump(), "revision": 0})
    return row

@api.route("GET", "/api/companies")
def company_list(c, body):
    return {"companies": all_records(c.db, "company", c.principal)}

@api.route("POST", "/api/companies/{company_id}/grants", Grant, roles=["owner"], status=201)
def company_grant(c, body):
    company = get(c.db, "company", c.path["company_id"], c.principal)
    target = c.db.execute("SELECT id FROM principals WHERE id=? AND tenant_id=?", (body.principal_id, c.principal["tenant_id"])).fetchone()
    if not target:
        raise HTTPException(404, "Principal not found")
    c.db.execute("INSERT OR IGNORE INTO grants VALUES(?,?)", (body.principal_id, company["id"]))
    audit(c.db, c.principal, "company.granted", body.principal_id, company["id"])
    return {"company_id": company["id"], "principal_id": body.principal_id}

@api.route("DELETE", "/api/companies/{company_id}/grants/{principal_id}", roles=["owner"])
def company_revoke(c, body):
    company = get(c.db, "company", c.path["company_id"], c.principal)
    c.db.execute("DELETE FROM grants WHERE principal_id=? AND company_id=?", (c.path["principal_id"], company["id"]))
    audit(c.db, c.principal, "company.grant_revoked", c.path["principal_id"], company["id"])
    return {"revoked": True}

@api.route("GET", "/api/companies/{company_id}")
def company_profile(c, body):
    company = get(c.db, "company", c.path["company_id"], c.principal)
    values, versions = profiles.values_at(c.db, c.principal, company["id"], as_of(c))
    return {**company, "as_of": as_of(c), "confirmed_facts": values, "fact_versions": versions,
            "scope": profiles.scope(values)}

@api.route("GET", "/api/companies/{company_id}/structure")
def company_structure(c, body):
    profile = company_profile(c, body)
    values = profile["confirmed_facts"]
    return {"company_id": profile["id"], "fact_versions": profile["fact_versions"],
            "ownership": {f: values.get(f) for f in catalog.GROUPS["ownership"]},
            "governance": {f: values.get(f) for f in catalog.GROUPS["governance"]},
            "registered_address": values.get("registered_address"), "scope": profile["scope"],
            "unconfirmed_gaps": [f for f in ["members", "directors", "auditor", "signatories"] if values.get(f) is None]}

@api.route("POST", "/api/companies/{company_id}/facts", FactInput, roles=WRITE, status=201)
def fact_create(c, body):
    return profiles.add_fact(c.db, c.principal, c.path["company_id"], body)

@api.route("GET", "/api/companies/{company_id}/facts")
def fact_list(c, body):
    return {"facts": all_records(c.db, "fact", c.principal, c.path["company_id"])}

@api.route("POST", "/api/companies/{company_id}/facts/confirm", FactConfirm, roles=WRITE)
def fact_confirm(c, body):
    return profiles.confirm(c.db, c.principal, c.path["company_id"], body)

@api.route("POST", "/api/companies/{company_id}/evidence", EvidenceInput, roles=WRITE, status=201)
def evidence_upload(c, body):
    return evidence.upload(c.db, c.principal, c.path["company_id"], body)

@api.route("GET", "/api/companies/{company_id}/evidence")
def evidence_list(c, body):
    return {"evidence": all_records(c.db, "evidence", c.principal, c.path["company_id"])}

@api.route("GET", "/api/evidence/{evidence_id}/download")
def evidence_download(c, body):
    record, raw = evidence.content(c.db, c.path["evidence_id"], c.principal)
    audit(c.db, c.principal, "evidence.downloaded", record["id"], record["company_id"])
    return Response(raw, media_type=record["media_type"],
                    headers={"Content-Disposition": 'attachment; filename="evidence-'+record["id"]+'.bin"',
                             "X-Content-SHA256": record["sha256"]})

@api.route("PUT", "/api/evidence/{evidence_id}/retention", Retention, roles=["owner"])
def evidence_retention(c, body):
    row = get(c.db, "evidence", c.path["evidence_id"], c.principal)
    audit(c.db, c.principal, "evidence.retention_changed", row["id"], row["company_id"])
    return update(c.db, row, body.model_dump(mode="json"))

@api.route("DELETE", "/api/evidence/{evidence_id}", roles=["owner"])
def evidence_delete(c, body):
    row = get(c.db, "evidence", c.path["evidence_id"], c.principal)
    if row["legal_hold"] or (row["retain_until"] and row["retain_until"] >= date.today().isoformat()):
        raise HTTPException(409, "Retention/hold prevents deletion")
    records = c.db.execute("SELECT payload FROM records WHERE tenant_id=? AND company_id=? AND id<>?",
                           (c.principal["tenant_id"], row["company_id"], row["id"])).fetchall()
    if any(row["id"] in r[0] for r in records):
        raise HTTPException(409, "Evidence is referenced by a fact, pack or filing; preserve it")
    c.db.execute("DELETE FROM blobs WHERE id=?", (row["id"],))
    audit(c.db, c.principal, "evidence.deleted", row["id"], row["company_id"])
    return update(c.db, row, {"deleted": True})

@api.route("POST", "/api/companies/{company_id}/consents", Consent, roles=["owner"], status=201)
def consent_record(c, body):
    get(c.db, "company", c.path["company_id"], c.principal)
    return insert(c.db, "consent", c.principal, body.model_dump(), c.path["company_id"])

@api.route("GET", "/api/companies/{company_id}/questionnaire/{workflow}")
def questionnaire(c, body):
    company_id, workflow = c.path["company_id"], c.path["workflow"]
    if workflow not in catalog.WORKFLOWS:
        raise HTTPException(404, "Unknown workflow")
    values, versions = profiles.values_at(c.db, c.principal, company_id, as_of(c))
    scoped = profiles.scope(values)
    fields = list(dict.fromkeys(scoped["missing"] + catalog.required_fields(workflow, values)))
    for rule in all_records(c.db, "rule", c.principal):
        if rule["workflow"] == workflow and rule["status"] == "approved" and rule["effective_from"] <= as_of(c) and (not rule["effective_to"] or as_of(c) <= rule["effective_to"]):
            fields += rule["required_fields"] + rule["required_evidence_fields"]
            fields += [clause["field"] for clause in rule["conditions"] + rule["exclusions"]]
            if rule["trigger_field"]:
                fields.append(rule["trigger_field"])
    fields = list(dict.fromkeys(fields))
    candidates = all_records(c.db, "fact", c.principal, company_id)
    questions = []
    for f in fields:
        if values.get(f) is None:
            q = catalog.question(f)
            q["answer_state"] = "unknown" if f in values else "missing"
            q["candidate_fact_ids"] = [r["id"] for r in candidates if r["field"] == f and r["status"] == "candidate"]
            questions.append(q)
    return {"workflow": workflow, "scope": scoped, "questions": questions, "fact_versions": versions,
            "schema_definitions": Facts.model_json_schema().get("$defs", {}), "complete": not questions}

@api.route("POST", "/api/companies/{company_id}/questionnaire/{workflow}/answers", QuestionnaireAnswer, roles=WRITE, status=201)
def questionnaire_answers(c, body):
    questionnaire(c, None)
    rows = [profiles.add_fact(c.db, c.principal, c.path["company_id"], a) for a in body.answers]
    return insert(c.db, "questionnaire_session", c.principal, {"workflow": c.path["workflow"],
                  "candidate_fact_ids": [r["id"] for r in rows], "confirmation_required": True}, c.path["company_id"])

@api.route("POST", "/api/companies/{company_id}/evaluate", EvaluationRequest, roles=WRITE)
def company_evaluate(c, body):
    return rules.evaluate_company(c.db, c.principal, c.path["company_id"], body.as_of.isoformat())

@api.route("GET", "/api/companies/{company_id}/obligations")
def obligation_list(c, body):
    company = get(c.db, "company", c.path["company_id"], c.principal)
    return {"obligations": [{**row, "stale": row["company_revision"] != company["revision"]}
                            for row in all_records(c.db, "obligation", c.principal, company["id"])]}

@api.route("POST", "/api/companies/{company_id}/lookup", Lookup, roles=WRITE)
def company_lookup(c, body):
    company = get(c.db, "company", c.path["company_id"], c.principal)
    if body.provider not in {"mock", "sandbox"}:
        raise HTTPException(501, {"provider": body.provider, "message": "Provider approval/resource contract required; no invented endpoint"})
    if body.provider == "mock" and c.app.state.settings.mode == "production":
        raise HTTPException(409, "Synthetic provider disabled in production")
    try:
        result = (MockProvider() if body.provider == "mock" else c.app.state.sandbox).lookup(company["cin"])
    except ProviderFailure as error:
        raise as_http(error)
    raw = json.dumps(result, ensure_ascii=False).encode()
    e = EvidenceInput(filename="provider-response.json", media_type="application/json",
                      content_base64=base64.b64encode(raw).decode(), purpose="company_record", observed_on=date.today())
    record = evidence.upload(c.db, c.principal, company["id"], e)
    candidates = [profiles.add_fact(c.db, c.principal, company["id"], FactInput(field=key, value=value,
                  evidence_id=record["id"], provenance="provider", valid_from=date.today()))
                  for key, value in result["fields"].items()]
    return {**{k: v for k, v in result.items() if k != "raw"}, "evidence_id": record["id"],
            "candidate_fact_ids": [r["id"] for r in candidates], "confirmed_facts_modified": False}

@api.route("GET", "/api/companies/{company_id}/audit")
def audit_list(c, body):
    get(c.db, "company", c.path["company_id"], c.principal)
    rows = c.db.execute("SELECT * FROM audit WHERE tenant_id=? AND company_id=? ORDER BY id",
                        (c.principal["tenant_id"], c.path["company_id"])).fetchall()
    return {"events": [dict(r) for r in rows]}

@api.route("GET", "/api/companies/{company_id}/export")
def company_export(c, body):
    company = get(c.db, "company", c.path["company_id"], c.principal)
    rows = c.db.execute("SELECT payload FROM records WHERE tenant_id=? AND company_id=?",
                        (c.principal["tenant_id"], company["id"])).fetchall()
    audit(c.db, c.principal, "company.exported", company["id"], company["id"])
    return {"company": company, "records": [json.loads(r[0]) for r in rows],
            "binary_evidence": "Use authenticated evidence download endpoints to retrieve original files"}
