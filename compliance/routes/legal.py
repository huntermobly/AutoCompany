import difflib
from urllib.parse import urlparse
import httpx
from starlette.exceptions import HTTPException
from ..catalog import sources
from ..database import all_records, audit, digest, get, insert, now, update
from ..http import api
from ..models import (RuleApproval, RuleInput, SourceSnapshot, SourceVerification,
                      TemplateApproval, TemplateInput)
from ..rules import approve_rule

@api.route("GET", "/api/sources")
def source_register(c, body):
    return {"sources": sources(), "snapshots": all_records(c.db, "source_snapshot", c.principal)}

@api.route("POST", "/api/sources/snapshots", SourceSnapshot, roles=["owner", "content_reviewer"], status=201)
def source_snapshot(c, body):
    entry = next((s for s in sources() if s["id"] == body.source_id), None)
    if not entry or body.url not in entry["urls"]:
        raise HTTPException(422, "Source URL must exactly match the registered source")
    prior = [s for s in all_records(c.db, "source_snapshot", c.principal) if s["source_id"] == body.source_id]
    if prior and prior[-1]["sha256"] == digest(body.text.encode()):
        raise HTTPException(409, "Identical source content already captured")
    row = insert(c.db, "source_snapshot", c.principal, {**body.model_dump(mode="json"),
                 "status": "draft", "sha256": digest(body.text.encode()), "submitted_by": c.principal["id"],
                 "retrieved_at": now(), "previous_snapshot_id": prior[-1]["id"] if prior else None})
    if prior:
        changes = "\n".join(difflib.unified_diff(prior[-1]["text"].splitlines(), body.text.splitlines()))
        insert(c.db, "source_change", c.principal, {"source_id": body.source_id,
               "snapshot_id": row["id"], "previous_snapshot_id": prior[-1]["id"],
               "diff": changes, "status": "review_required", "rules_auto_updated": False})
    return row

@api.route("POST", "/api/sources/snapshots/{snapshot_id}/verify", SourceVerification, roles=["content_reviewer"])
def source_verify(c, body):
    row = get(c.db, "source_snapshot", c.path["snapshot_id"], c.principal)
    if row["status"] != "draft" or row["submitted_by"] == c.principal["id"]:
        raise HTTPException(409, "Verification requires a draft and a different reviewer")
    if row["synthetic"] and c.app.state.settings.mode == "production":
        raise HTTPException(409, "Synthetic sources cannot be verified in production")
    audit(c.db, c.principal, "source.verified", row["id"])
    return update(c.db, row, {"status": "verified", "verified_by": c.principal["id"],
                            "verified_at": now(), "verification_notes": body.notes})

@api.route("GET", "/api/sources/changes")
def source_changes(c, body):
    return {"changes": all_records(c.db, "source_change", c.principal)}

@api.route("POST", "/api/sources/{source_id}/check", roles=["owner", "content_reviewer"])
def source_check(c, body):
    entry = next((s for s in sources() if s["id"] == c.path["source_id"]), None)
    if not entry:
        raise HTTPException(404, "Unknown source")
    if not c.app.state.settings.external_enabled:
        raise HTTPException(503, "External fetching disabled; upload a source snapshot for review")
    url = entry["urls"][0]
    if urlparse(url).scheme != "https":
        raise HTTPException(422, "Only registered HTTPS sources can be fetched")
    try:
        with c.app.state.source_client.stream("GET", url, headers={"User-Agent": "ComplianceSourceMonitor/0.1"}) as response:
            if response.status_code != 200:
                raise ValueError("Source returned a non-success status; no redirect or bypass attempted")
            buf = bytearray()
            for part in response.iter_bytes():
                buf.extend(part)
                if len(buf) > 2_000_000:
                    raise ValueError("Source exceeds monitor size limit; use manual upload")
        status, reason = "review_required", "Review publication/effective dates before creating a source version"
        sha = digest(bytes(buf))
    except (httpx.RequestError, ValueError) as exc:
        status, reason, sha = "fetch_failed", "Source unavailable or outside bounded fetch limits; use manual upload", None
    return insert(c.db, "source_change", c.principal, {"source_id": entry["id"], "url": url,
                  "sha256": sha, "status": status, "reason": reason, "rules_auto_updated": False,
                  "checked_at": now()})

@api.route("POST", "/api/rules", RuleInput, roles=["owner", "content_reviewer"], status=201)
def rule_create(c, body):
    for identity in body.source_snapshot_ids:
        source = get(c.db, "source_snapshot", identity, c.principal)
        if source["effective_from"] > body.effective_from.isoformat():
            raise HTTPException(422, "Rule cannot become effective before its cited source")
    if any(r["rule_key"] == body.rule_key and r["version"] == body.version for r in all_records(c.db, "rule", c.principal)):
        raise HTTPException(409, "Rule key/version already exists")
    return insert(c.db, "rule", c.principal, {**body.model_dump(mode="json"),
                  "status": "draft", "authored_by": c.principal["id"]})

@api.route("GET", "/api/rules")
def rule_list(c, body):
    return {"rules": all_records(c.db, "rule", c.principal)}

@api.route("POST", "/api/rule-releases/{rule_id}/approve", RuleApproval, roles=["content_reviewer"])
def rule_approve(c, body):
    return approve_rule(c.db, c.principal, c.path["rule_id"], body, c.app.state.settings.mode)

@api.route("POST", "/api/rule-releases/{rule_id}/retire", SourceVerification, roles=["content_reviewer"])
def rule_retire(c, body):
    row = get(c.db, "rule", c.path["rule_id"], c.principal)
    if row["status"] != "approved":
        raise HTTPException(409, "Only active rules can be retired")
    affected = [o["id"] for o in all_records(c.db, "obligation", c.principal) if o["rule_id"] == row["id"]]
    audit(c.db, c.principal, "rule.retired", row["id"])
    return {**update(c.db, row, {"status": "retired", "retirement_notes": body.notes}), "reevaluation_required": affected}

@api.route("POST", "/api/templates", TemplateInput, roles=["owner", "content_reviewer"], status=201)
def template_create(c, body):
    for identity in body.source_snapshot_ids:
        get(c.db, "source_snapshot", identity, c.principal)
    if any(t["workflow"] == body.workflow and t["version"] == body.version for t in all_records(c.db, "template", c.principal)):
        raise HTTPException(409, "Template workflow/version already exists")
    return insert(c.db, "template", c.principal, {**body.model_dump(mode="json"), "status": "draft",
                  "authored_by": c.principal["id"]})

@api.route("GET", "/api/templates")
def template_list(c, body):
    return {"templates": all_records(c.db, "template", c.principal)}

@api.route("POST", "/api/templates/{template_id}/approve", TemplateApproval, roles=["content_reviewer"])
def template_approve(c, body):
    row = get(c.db, "template", c.path["template_id"], c.principal)
    if row["status"] != "draft" or row["authored_by"] == c.principal["id"]:
        raise HTTPException(409, "Approval requires a draft and a different reviewer")
    if c.app.state.settings.mode == "production" and row["synthetic"]:
        raise HTTPException(409, "Synthetic template cannot be activated in production")
    for identity in row["source_snapshot_ids"]:
        source = get(c.db, "source_snapshot", identity, c.principal)
        if source["status"] != "verified" or (source["synthetic"] and not row["synthetic"]):
            raise HTTPException(409, "Verified sources required")
    audit(c.db, c.principal, "template.approved", row["id"])
    return update(c.db, row, {"status": "approved", "reviewed_by": c.principal["id"],
                            "reviewed_at": now(), "reviewer_notes": body.notes})
