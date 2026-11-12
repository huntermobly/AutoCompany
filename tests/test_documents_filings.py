import io
import json
import zipfile
from xml.etree import ElementTree
import pytest
from PyPDF2 import PdfReader
from compliance.database import digest

@pytest.mark.parametrize("workflow",["board_agm","aoc4","mgt7","mgt7a","adt1","inc20a","dir12"])
def test_every_workflow_generates_valid_frozen_export(harness,workflow):
    company,facts,ob,pack=harness.prepared(workflow)
    response=harness.request("GET",f'/api/document-packs/{pack["id"]}/download')
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        assert {"worksheet.docx","worksheet.pdf","filing-data.json","attachments.json","manifest.json","signature-checklist.txt"} <= set(z.namelist())
        manifest=json.loads(z.read("manifest.json"))
        assert manifest["rule_id"]==ob["rule_id"] and manifest["synthetic"] is True and manifest["stale"] is False
        for name,sha in manifest["files"].items():
            assert digest(z.read(name))==sha
        assert set(json.loads(z.read("filing-data.json")))==set(facts)
        with zipfile.ZipFile(io.BytesIO(z.read("worksheet.docx"))) as docx:
            xml=ElementTree.fromstring(docx.read("word/document.xml"))
            assert company["cin"] in "".join(xml.itertext())
        pdf=PdfReader(io.BytesIO(z.read("worksheet.pdf")))
        text="\n".join(page.extract_text() for page in pdf.pages)
        assert company["cin"] in text and "SYNTHETIC" in text
        if workflow=="board_agm":
            assert "meeting-1-minutes.docx" in z.namelist()
    assert harness.request("GET",f'/api/document-packs/{pack["id"]}').json()["status"]=="ready_for_review"

def approve_pack(h,pack):
    return h.request("POST",f'/api/document-packs/{pack["id"]}/reviews',
        {"decision":"approved","comments":"Synthetic professional review only"},role="professional",expected=201)

def test_complete_filing_evidence_flow_and_no_direct_submission(harness):
    company,facts,ob,pack=harness.prepared()
    harness.request("POST","/api/filing-attempts",{"pack_id":pack["id"],"srn":"DEMO123"},expected=409)
    approve_pack(harness,pack)
    filing=harness.request("POST","/api/filing-attempts",{"pack_id":pack["id"],"srn":"DEMO123"},expected=201).json()
    assert filing["completed"] is False
    harness.request("POST",f'/api/filing-attempts/{filing["id"]}/submit',expected=501)
    assert harness.request("GET",f'/api/filing-attempts/{filing["id"]}/handoff').json()["automatic_submission"] is False
    receipt=harness.evidence(company["id"],"filing_receipt",b"synthetic submission receipt")
    body={"evidence_id":receipt["id"],"cin":company["cin"],"form":"AOC-4","financial_year":facts["financial_year"],
          "srn":"DEMO123","status":"submitted","observed_on":"2026-09-30"}
    harness.request("POST",f'/api/filing-attempts/{filing["id"]}/evidence',body,expected=201)
    harness.request("POST",f'/api/filing-attempts/{filing["id"]}/evidence',body,expected=409)
    receipt2=harness.evidence(company["id"],"filing_receipt",b"synthetic recorded-status receipt")
    body.update(evidence_id=receipt2["id"],status="recorded")
    harness.request("POST",f'/api/filing-attempts/{filing["id"]}/evidence',body,role="professional",expected=409)
    signed=harness.evidence(company["id"],"signed_document",b"synthetic signed file - no real signature")
    body.update(signatory_confirmed=True,payment_confirmed=True,signed_document_evidence_id=signed["id"])
    harness.request("POST",f'/api/filing-attempts/{filing["id"]}/evidence',body,expected=403)
    result=harness.request("POST",f'/api/filing-attempts/{filing["id"]}/evidence',body,role="professional",expected=201).json()
    assert result["completed"] and result["verification"]=="manual_professional_attestation"
    assert harness.request("GET",f'/api/obligations/{ob["id"]}').json()["filing_status"]=="recorded"

def test_changed_facts_invalidate_pack_and_historical_export_marks_stale(harness):
    company,facts,ob,pack=harness.prepared()
    path=f'/api/companies/{company["id"]}'
    r=harness.request("POST",path+"/facts",{"field":"turnover_inr","value":"99","valid_from":"2026-04-01"},expected=201).json()
    harness.request("POST",path+"/facts/confirm",{"fact_ids":[r["id"]],"replace_conflicts":True})
    harness.request("POST",f'/api/document-packs/{pack["id"]}/reviews',{"decision":"approved","comments":"review"},role="professional",expected=409)
    with zipfile.ZipFile(io.BytesIO(harness.request("GET",f'/api/document-packs/{pack["id"]}/download').content)) as z:
        assert json.loads(z.read("manifest.json"))["stale"]
        assert json.loads(z.read("filing-data.json"))["turnover_inr"]==facts["turnover_inr"]

def test_certification_gate_and_mismatched_receipts(harness):
    company,facts,ob,pack=harness.prepared(certification=True)
    harness.request("POST",f'/api/document-packs/{pack["id"]}/reviews',
        {"decision":"approved","comments":"Missing certificate"},role="professional",expected=409)
    cert=harness.evidence(company["id"],"professional_certificate",b"synthetic certificate")
    harness.request("POST",f'/api/document-packs/{pack["id"]}/reviews',
        {"decision":"approved","comments":"Synthetic reviewed","certification_evidence_id":cert["id"]},role="professional",expected=201)
    filing=harness.request("POST","/api/filing-attempts",{"pack_id":pack["id"],"srn":"DEMO456"},expected=201).json()
    receipt=harness.evidence(company["id"],"filing_receipt")
    body={"evidence_id":receipt["id"],"cin":company["cin"],"form":"DIR-12","financial_year":facts["financial_year"],
          "srn":"DEMO456","status":"submitted","observed_on":"2026-09-30"}
    harness.request("POST",f'/api/filing-attempts/{filing["id"]}/evidence',body,expected=422)

def test_final_pack_requires_approved_template(harness):
    company,facts,_=harness.company()
    source=harness.source()
    harness.rule(facts,source)
    ob=harness.request("POST",f'/api/companies/{company["id"]}/evaluate',{"as_of":"2026-09-30"}).json()["obligations"][0]
    harness.request("POST",f'/api/obligations/{ob["id"]}/document-packs',{"final":True},expected=409)
    draft=harness.request("POST",f'/api/obligations/{ob["id"]}/document-packs',{"final":False},expected=201).json()
    assert draft["status"]=="working_draft"

def test_cross_tenant_pack_filing_and_obligation(harness):
    company,facts,ob,pack=harness.prepared()
    for path in [f'/api/obligations/{ob["id"]}',f'/api/document-packs/{pack["id"]}',f'/api/document-packs/{pack["id"]}/download']:
        harness.request("GET",path,role="other",expected=404)
    approve_pack(harness,pack)
    filing=harness.request("POST","/api/filing-attempts",{"pack_id":pack["id"],"srn":"DEMO999"},expected=201).json()
    harness.request("GET",f'/api/filing-attempts/{filing["id"]}',role="other",expected=404)
