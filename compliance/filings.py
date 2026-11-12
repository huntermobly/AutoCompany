from starlette.exceptions import HTTPException
from .database import all_records, audit, get, insert, update
from .documents import pack_current

ALLOWED = {
    "created": {"submitted", "payment_pending"},
    "submitted": {"payment_pending", "resubmission", "rejected", "recorded", "approved"},
    "payment_pending": {"submitted", "resubmission", "rejected", "recorded", "approved"},
    "resubmission": {"submitted", "rejected"},
    "recorded": set(), "approved": set(), "rejected": set(),
}

def create(db, principal, body):
    pack = get(db, "pack", body.pack_id, principal)
    pack_current(db, principal, pack)
    if pack["status"] != "approved" or not pack["financial_year"]:
        raise HTTPException(409, "An approved pack and confirmed financial year are required")
    for old in all_records(db, "filing", principal, pack["company_id"]):
        if old["srn"] == body.srn:
            raise HTTPException(409, "SRN already exists for this company")
        if old["pack_id"] == pack["id"] and old["status"] != "rejected":
            raise HTTPException(409, "This pack already has an active filing attempt")
    return insert(db, "filing", principal, {"pack_id": pack["id"], "obligation_id": pack["obligation_id"],
                  "srn": body.srn, "form": pack["form"], "cin": pack["cin"],
                  "financial_year": pack["financial_year"], "status": "created",
                  "verification": "not_verified", "completed": False}, pack["company_id"])

def observe(db, principal, identity, body):
    filing = get(db, "filing", identity, principal)
    pack = get(db, "pack", filing["pack_id"], principal)
    pack_current(db, principal, pack)
    for key in ["cin", "form", "srn", "financial_year"]:
        if body.model_dump(mode="json")[key] != filing[key]:
            raise HTTPException(422, f"Evidence metadata does not match filing: {key}")
    evidence = get(db, "evidence", body.evidence_id, principal)
    if evidence["company_id"] != filing["company_id"] or evidence["purpose"] != "filing_receipt" or evidence["deleted"]:
        raise HTTPException(422, "A retained filing receipt for this company is required")
    observations = all_records(db, "filing_observation", principal, filing["company_id"])
    if any(o["evidence_id"] == body.evidence_id for o in observations):
        raise HTTPException(409, "Receipt already recorded; append distinct status evidence")
    prior = [o for o in observations if o["filing_id"] == identity]
    if prior and body.observed_on.isoformat() < max(o["observed_on"] for o in prior):
        raise HTTPException(409, "An older observation cannot overwrite current status")
    if body.status not in ALLOWED[filing["status"]]:
        raise HTTPException(409, "Invalid filing status transition")
    complete = body.status in {"recorded", "approved"}
    if complete:
        if principal["role"] != "professional":
            raise HTTPException(403, "A professional must attest completion evidence")
        if not body.signatory_confirmed or not body.payment_confirmed or not body.signed_document_evidence_id:
            raise HTTPException(409, "Signature, signed document and payment confirmation required")
        signed = get(db, "evidence", body.signed_document_evidence_id, principal)
        if signed["company_id"] != filing["company_id"] or signed["purpose"] != "signed_document" or signed["deleted"]:
            raise HTTPException(422, "Valid signed-document evidence required")
        if pack["professional_certification_required"]:
            if not body.certification_confirmed or not body.professional_certificate_evidence_id:
                raise HTTPException(409, "Required professional certification is missing")
            certificate = get(db, "evidence", body.professional_certificate_evidence_id, principal)
            if certificate["company_id"] != filing["company_id"] or certificate["purpose"] != "professional_certificate" or certificate["deleted"]:
                raise HTTPException(422, "Valid professional certificate evidence required")
    observation = insert(db, "filing_observation", principal, {**body.model_dump(mode="json"), "filing_id": identity,
                         "attested_by": principal["id"], "verification": "manual_professional_attestation" if complete else "user_reported"}, filing["company_id"])
    result = update(db, filing, {"status": body.status, "completed": complete, "verification": observation["verification"]})
    obligation = get(db, "obligation", filing["obligation_id"], principal)
    update(db, obligation, {"filing_status": body.status, "completion_verification": observation["verification"]})
    audit(db, principal, "filing.status_observed", identity, filing["company_id"])
    return result
