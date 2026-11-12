"""Deterministic exports. No remote HTML, macros, signatures or fabricated declarations."""
import io
import json
import textwrap
import threading
import zipfile
from xml.sax.saxutils import escape
from starlette.exceptions import HTTPException
from .catalog import WORKFLOWS
from .database import all_records, digest, get, insert

_render_lock = threading.Lock()

def docx_bytes(lines):
    ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    paragraphs = "".join('<w:p><w:r><w:t xml:space="preserve">'+escape(line)+'</w:t></w:r></w:p>' for line in lines)
    document = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="'+ns+'"><w:body>'+paragraphs+'<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1000" w:right="1000" w:bottom="1000" w:left="1000"/></w:sectPr></w:body></w:document>'
    types = '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>'
    rels = '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", document)
    return stream.getvalue()

def pdf_bytes(lines):
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib.figure import Figure
    from matplotlib.font_manager import FontProperties, findfont
    from fontTools.ttLib import TTFont
    font_path = findfont("DejaVu Sans Mono")
    with TTFont(font_path) as font:
        glyphs = font.getBestCmap()
        unsupported = sorted({c for line in lines for c in line if ord(c) not in glyphs and c not in "\n\t\r"})
    if unsupported:
        raise HTTPException(422, "PDF font does not support these characters; export company JSON or configure a suitable font: "+ "".join(unsupported[:20]))
    wrapped = []
    for line in lines:
        for part in line.splitlines() or [""]:
            wrapped.extend(textwrap.wrap(part, width=86, break_long_words=True, replace_whitespace=False) or [""])
    stream = io.BytesIO()
    with _render_lock, PdfPages(stream) as pdf:
        pages = [wrapped[i:i+65] for i in range(0, len(wrapped), 65)] or [[]]
        for index, page_lines in enumerate(pages):
            fig = Figure(figsize=(8.27, 11.69))
            fig.text(.065, .95, "\n".join(page_lines), va="top", fontsize=8.2,
                     fontproperties=FontProperties(fname=font_path), linespacing=1.5)
            fig.text(.065, .035, f"Preparation document | Page {index+1}/{len(pages)}", fontsize=8)
            pdf.savefig(fig)
            fig.clear()
    return stream.getvalue()

def pack_current(db, principal, pack):
    company = get(db, "company", pack["company_id"], principal)
    rule = get(db, "rule", pack["rule_id"], principal)
    if company["revision"] != pack["company_revision"] or rule["status"] != "approved":
        raise HTTPException(409, "Facts or rule changed: regenerate and review a new pack")
    if pack.get("template_id"):
        template = get(db, "template", pack["template_id"], principal)
        if template["status"] != "approved":
            raise HTTPException(409, "Template approval is no longer active")
    return company

def create_pack(db, principal, obligation_id, final):
    ob = get(db, "obligation", obligation_id, principal)
    company = get(db, "company", ob["company_id"], principal)
    if company["revision"] != ob["company_revision"]:
        raise HTTPException(409, "Re-evaluate after confirmed facts change")
    rule = get(db, "rule", ob["rule_id"], principal)
    if rule["status"] != "approved":
        raise HTTPException(409, "Rule is no longer approved")
    templates = [t for t in all_records(db, "template", principal)
                 if t["workflow"] == ob["workflow"] and t["status"] == "approved"
                 and (not t["synthetic"] or ob["synthetic"])]
    template = max(templates, key=lambda t: t["version"]) if templates else None
    missing = list(ob["missing_fields"])
    if final and (ob["status"] != "applicable" or missing or not template):
        raise HTTPException(409, {"message": "Final pack requires complete applicable facts and an approved template",
                                  "missing_fields": missing, "template_approved": bool(template)})
    payload = {"obligation_id": obligation_id, "company_revision": company["revision"],
               "rule_id": ob["rule_id"], "rule_version": ob["rule_version"],
               "template_id": template["id"] if template else None,
               "template_version": template["version"] if template else "worksheet-v1",
               "facts_snapshot": ob["facts_snapshot"], "fact_versions": ob["fact_versions"],
               "source_snapshot_ids": ob["source_snapshot_ids"], "missing_fields": missing,
               "workflow": ob["workflow"], "form": ob["form"], "cin": company["cin"], "as_of": ob["as_of"],
               "financial_year": ob["facts_snapshot"].get("financial_year"), "synthetic": ob["synthetic"],
               "status": "ready_for_review" if final else "working_draft", "created_by": principal["id"],
               "professional_certification_required": ob["professional_certification_required"],
               "signatory_policy": template["signatory_policy"] if template else "Verify signatories and DSC requirements against the current official form.",
               "instructions": template["instructions"] if template else ["Preparation worksheet only. Current form and professional review required."]}
    payload["snapshot_sha256"] = digest(payload)
    return insert(db, "pack", principal, payload, company["id"])

def render_pack(db, principal, pack):
    # Historical exports remain available and explicitly record stale status.
    try:
        pack_current(db, principal, pack)
        stale = False
    except HTTPException as exc:
        if exc.status_code != 409:
            raise
        stale = True
    facts = pack["facts_snapshot"]
    lines = [f'{pack["form"]} - preparation worksheet', f'CIN: {pack["cin"]}',
             f'Status: {pack["status"]}' + (" | STALE: REGENERATE BEFORE USE" if stale else ""),
             "SYNTHETIC DEMONSTRATION - NOT FOR STATUTORY USE" if pack["synthetic"] else "Not an official MCA form.",
             f'As of: {pack["as_of"]}', f'Rule version: {pack["rule_version"]}; template: {pack["template_version"]}',
             "", *pack["instructions"], "", "Confirmed facts:"]
    for field, value in sorted(facts.items()):
        lines.append(field + ": " + json.dumps(value, ensure_ascii=False, sort_keys=True))
    lines += ["", "Missing fields: " + (", ".join(pack["missing_fields"]) or "None in this workflow"),
              "", "Signature instructions:", pack["signatory_policy"],
              "A scanned signature is not a DSC. Follow the applicable portal signing process.",
              "No signature or professional certification is generated by this application."]
    attachment_ids = {v for k, v in facts.items() if k.endswith("_evidence_id") and isinstance(v, str)}
    for fact_id in pack["fact_versions"].values():
        fact = get(db, "fact", fact_id, principal)
        if fact.get("evidence_id"):
            attachment_ids.add(fact["evidence_id"])
    attachments = []
    for identity in sorted(attachment_ids):
        e = get(db, "evidence", identity, principal)
        attachments.append({k: e[k] for k in ["id", "filename", "sha256", "purpose", "scan_status", "deleted"]})
    files = {"worksheet.docx": docx_bytes(lines), "worksheet.pdf": pdf_bytes(lines),
             "filing-data.json": json.dumps(facts, ensure_ascii=False, indent=2).encode(),
             "attachments.json": json.dumps(attachments, indent=2).encode(),
             "signature-checklist.txt": ("\n".join(lines[-4:])).encode()}
    if pack["workflow"] == "board_agm":
        for index, meeting in enumerate(facts.get("meetings") or []):
            intro = ["WORKING DRAFT - confirm meeting facts and notice requirements",
                     f'Type: {meeting["kind"]}; scheduled date: {meeting["scheduled_date"]}']
            files[f"meeting-{index+1}-notice-agenda.docx"] = docx_bytes(intro + ["Agenda/decisions supplied:"] + meeting["decisions"])
            if meeting.get("held") is True:
                files[f"meeting-{index+1}-minutes.docx"] = docx_bytes(
                    ["DRAFT MINUTES - factual inputs require professional review"] + intro[1:] +
                    ["Attendance: " + ", ".join(meeting["attendance"]), "Decisions:"] + meeting["decisions"])
    manifest = {k: v for k, v in pack.items() if k not in {"facts_snapshot"}}
    manifest["stale"] = stale
    manifest["files"] = {name: digest(value) for name, value in files.items()}
    files["manifest.json"] = json.dumps(manifest, indent=2).encode()
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)
    return stream.getvalue()

