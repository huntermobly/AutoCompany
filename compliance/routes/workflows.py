from starlette.exceptions import HTTPException
from starlette.responses import Response
from .. import documents, filings
from ..database import all_records, audit, get, insert, update
from ..http import api
from ..models import Ask, FilingCreate, FilingObservation, PackRequest, Review
from ..providers import ProviderFailure, as_http

WRITE = ["owner", "operator", "professional"]

@api.route("GET", "/api/obligations/{obligation_id}")
def obligation_get(c, body):
    return get(c.db, "obligation", c.path["obligation_id"], c.principal)

@api.route("POST", "/api/obligations/{obligation_id}/document-packs", PackRequest, roles=WRITE, status=201)
def pack_create(c, body):
    return documents.create_pack(c.db, c.principal, c.path["obligation_id"], body.final)

@api.route("GET", "/api/document-packs/{pack_id}")
def pack_get(c, body):
    return get(c.db, "pack", c.path["pack_id"], c.principal)

@api.route("GET", "/api/document-packs/{pack_id}/download")
def pack_download(c, body):
    pack = get(c.db, "pack", c.path["pack_id"], c.principal)
    content = documents.render_pack(c.db, c.principal, pack)
    audit(c.db, c.principal, "pack.downloaded", pack["id"], pack["company_id"])
    return Response(content, media_type="application/zip",
                    headers={"Content-Disposition": 'attachment; filename="preparation-'+pack["id"]+'.zip"'})

@api.route("POST", "/api/document-packs/{pack_id}/reviews", Review, roles=["professional"], status=201)
def pack_review(c, body):
    pack = get(c.db, "pack", c.path["pack_id"], c.principal)
    documents.pack_current(c.db, c.principal, pack)
    if pack["created_by"] == c.principal["id"]:
        raise HTTPException(403, "Pack author cannot approve their own pack")
    if pack["status"] not in {"ready_for_review", "changes_requested"}:
        raise HTTPException(409, "Pack is not ready for review")
    if body.decision == "approved" and pack["professional_certification_required"]:
        if not body.certification_evidence_id:
            raise HTTPException(409, "Required professional certification evidence is missing")
        evidence = get(c.db, "evidence", body.certification_evidence_id, c.principal)
        if evidence["company_id"] != pack["company_id"] or evidence["purpose"] != "professional_certificate" or evidence["deleted"]:
            raise HTTPException(422, "Invalid certification evidence")
    decision = insert(c.db, "review", c.principal, {**body.model_dump(), "pack_id": pack["id"],
                      "reviewed_snapshot_sha256": pack["snapshot_sha256"]}, pack["company_id"])
    update(c.db, pack, {"status": body.decision, "review_id": decision["id"]})
    return decision

@api.route("POST", "/api/filing-attempts", FilingCreate, roles=WRITE, status=201)
def filing_create(c, body):
    return filings.create(c.db, c.principal, body)

@api.route("GET", "/api/filing-attempts/{filing_id}")
def filing_get(c, body):
    return get(c.db, "filing", c.path["filing_id"], c.principal)

@api.route("POST", "/api/filing-attempts/{filing_id}/evidence", FilingObservation, roles=WRITE, status=201)
def filing_evidence(c, body):
    return filings.observe(c.db, c.principal, c.path["filing_id"], body)

@api.route("POST", "/api/filing-attempts/{filing_id}/submit", roles=WRITE)
def filing_submit(c, body):
    get(c.db, "filing", c.path["filing_id"], c.principal)
    raise HTTPException(501, "No approved government submission integration. Use the MCA portal handoff.")

@api.route("GET", "/api/filing-attempts/{filing_id}/handoff")
def filing_handoff(c, body):
    filing = get(c.db, "filing", c.path["filing_id"], c.principal)
    pack = get(c.db, "pack", filing["pack_id"], c.principal)
    documents.pack_current(c.db, c.principal, pack)
    return {"portal": "https://www.mca.gov.in/", "form": filing["form"], "srn": filing["srn"],
            "signatory_policy": pack["signatory_policy"], "automatic_submission": False,
            "steps": ["Verify the current form and instructions with your professional.",
                      "Prepare the form in your authorized MCA account.",
                      "Follow the applicable portal-generated PDF and DSC process.",
                      "Complete required upload/payment steps and inspect status.",
                      "Upload the acknowledgement and status evidence here.",
                      "Resolve resubmission requests; retain the original signed files."],
            "status": filing["status"], "completed": filing["completed"]}

@api.route("POST", "/api/obligations/{obligation_id}/explain", Ask)
def explain(c, body):
    ob = get(c.db, "obligation", c.path["obligation_id"], c.principal)
    rule = get(c.db, "rule", ob["rule_id"], c.principal)
    if rule["status"] != "approved":
        raise HTTPException(409, "Rule no longer active; re-evaluate")
    company = get(c.db, "company", ob["company_id"], c.principal)
    if company["revision"] != ob["company_revision"]:
        raise HTTPException(409, "Facts changed; re-evaluate")
    passages = [get(c.db, "source_snapshot", identity, c.principal) for identity in ob["source_snapshot_ids"]]
    context = {"status": ob["status"], "due_date": ob["due_date"], "reason": ob["reason"],
               "missing_fields": ob["missing_fields"], "interpretation": rule["interpretation"],
               "sources": [{"id": s["id"], "source_id": s["source_id"], "url": s["url"], "locator": s["locator"],
                            "effective_from": s["effective_from"], "text": s["text"][:10000]} for s in passages]}
    if not body.use_ai:
        return {**context, "mode": "deterministic", "actions_executed": [],
                "notice": "This explains the evaluated workflow, not arbitrary legal questions."}
    consents = [r for r in all_records(c.db, "consent", c.principal, ob["company_id"]) if r["purpose"] == "ai_explanation"]
    if not consents or not consents[-1]["allowed"]:
        raise HTTPException(409, "Current company permission for AI explanations is required")
    try:
        return c.app.state.ai.explain(body.question, context, [s["id"] for s in passages])
    except ProviderFailure as error:
        raise as_http(error)
