"""Complete synthetic workflow over a real HTTP server. Never calls a government API."""
import argparse
import base64
import json
from pathlib import Path
import sys
import httpx

ROOT = Path(__file__).resolve().parents[1]

def run(base_url, credentials_path, output):
    credentials = json.loads(Path(credentials_path).read_text(encoding="utf-8"))
    fixture = json.loads((ROOT/"examples/company.json").read_text(encoding="utf-8"))
    client = httpx.Client(base_url=base_url, timeout=60, trust_env=False)
    calls = []
    def api(method, path, data=None, role="owner", expected=200):
        r=client.request(method,path,json=data,headers={"Authorization":"Bearer "+credentials[role]["token"]})
        calls.append({"method":method,"path":path,"status":r.status_code})
        if r.status_code != expected:
            raise RuntimeError(f"{method} {path}: {r.status_code} {r.text[:1000]}")
        return r
    def upload(company_id,purpose,text):
        return api("POST",f"/api/companies/{company_id}/evidence",{
            "filename":"synthetic-demo.txt","media_type":"text/plain","purpose":purpose,
            "content_base64":base64.b64encode(text.encode()).decode(),"observed_on":"2026-09-30"},expected=201).json()
    try:
        health=client.get("/health")
        health.raise_for_status()
        if health.json()["mode"] == "production":
            raise RuntimeError("Synthetic demo must not run in production mode")
        company=api("POST","/api/companies",{"cin":fixture["cin"],"name":fixture["name"]},expected=201).json()
        cid=company["id"]
        api("POST",f"/api/companies/{cid}/grants",{"principal_id":credentials["professional"]["id"]},expected=201)
        evidence=upload(cid,"company_record","SYNTHETIC SOURCE. No real company records.")
        facts=json.loads(json.dumps(fixture["facts"]).replace("EVIDENCE_ID",evidence["id"]))
        ids=[]
        for field,value in facts.items():
            row=api("POST",f"/api/companies/{cid}/facts",{"field":field,"value":value,
                "provenance":"document","evidence_id":evidence["id"],"valid_from":"2026-04-01"},expected=201).json()
            ids.append(row["id"])
        api("POST",f"/api/companies/{cid}/facts/confirm",{"fact_ids":ids})
        catalog=api("GET","/api/catalog").json()
        url=next(s for s in catalog["sources"] if s["id"]=="S22")["urls"][0]
        source=api("POST","/api/sources/snapshots",{
            "source_id":"S22","title":"Synthetic demo passage","url":url,
            "text":"SYNTHETIC DEMO: exercise a thirty-day AGM-based preparation deadline. Not an approved legal source.",
            "published_on":"2026-01-01","effective_from":"2026-01-01","locator":"Synthetic demo",
            "synthetic":True},expected=201).json()
        api("POST",f'/api/sources/snapshots/{source["id"]}/verify',{"notes":"Synthetic demonstration reviewer action"},role="content_reviewer")
        rule=api("POST","/api/rules",{
            "rule_key":"synthetic_demo_aoc4","workflow":"aoc4","version":1,"effective_from":"2026-01-01",
            "source_snapshot_ids":[source["id"]],"required_fields":["financial_year"],
            "trigger_field":"agm_date","days_after":30,"synthetic":True,
            "interpretation":"Synthetic demo only; production rules require professional verification."},expected=201).json()
        api("POST",f'/api/rule-releases/{rule["id"]}/approve',{"reviewer_notes":"Synthetic demo",
            "fixtures":[
                {"name":"ordinary","facts":facts,"as_of":fixture["as_of"],"expected_status":"applicable","expected_due_date":"2026-10-20"},
                {"name":"public excluded","facts":{**facts,"listed":True},"as_of":fixture["as_of"],"expected_status":"specialist_review"}]},role="content_reviewer")
        template=api("POST","/api/templates",{
            "workflow":"aoc4","version":1,"source_snapshot_ids":[source["id"]],
            "title":"Synthetic demo worksheet","instructions":["Confirm all values before real use."],
            "signatory_policy":"Use the current official form's signatory and DSC requirements.",
            "synthetic":True},expected=201).json()
        api("POST",f'/api/templates/{template["id"]}/approve',{"notes":"Synthetic demo"},role="content_reviewer")
        ob=api("POST",f"/api/companies/{cid}/evaluate",{"as_of":fixture["as_of"]}).json()["obligations"][0]
        pack=api("POST",f'/api/obligations/{ob["id"]}/document-packs',{"final":True},expected=201).json()
        api("POST",f'/api/document-packs/{pack["id"]}/reviews',{"decision":"approved","comments":"Synthetic professional review"},role="professional",expected=201)
        filing=api("POST","/api/filing-attempts",{"pack_id":pack["id"],"srn":"SYNTHETIC-DEMO-SRN"},expected=201).json()
        receipt=upload(cid,"filing_receipt","Synthetic submission receipt.")
        observation={"evidence_id":receipt["id"],"cin":fixture["cin"],"form":"AOC-4","financial_year":facts["financial_year"],
                     "srn":filing["srn"],"status":"submitted","observed_on":fixture["as_of"]}
        api("POST",f'/api/filing-attempts/{filing["id"]}/evidence',observation,expected=201)
        receipt=upload(cid,"filing_receipt","Synthetic recorded-status receipt.")
        signed=upload(cid,"signed_document","Synthetic signed-document placeholder. No cryptographic signature.")
        observation.update(evidence_id=receipt["id"],status="recorded",signatory_confirmed=True,
                           payment_confirmed=True,signed_document_evidence_id=signed["id"])
        final=api("POST",f'/api/filing-attempts/{filing["id"]}/evidence',observation,role="professional",expected=201).json()
        assert final["completed"] and final["verification"]=="manual_professional_attestation"
        api("POST",f'/api/filing-attempts/{filing["id"]}/submit',expected=501)
        api("GET",f"/api/companies/{cid}/export")
        api("GET",f"/api/companies/{cid}/audit")
        destination=Path(output)
        destination.mkdir(parents=True,exist_ok=True)
        (destination/"example-pack.zip").write_bytes(api("GET",f'/api/document-packs/{pack["id"]}/download').content)
        (destination/"openapi.json").write_text(json.dumps(client.get("/openapi.json").json(),indent=2),encoding="utf-8")
        report={"transport":"real local HTTP","synthetic_only":True,"government_requests":0,
                "company_fields":len(facts),"plan_tables":len(catalog["planning_tables"]),
                "plan_rows":sum(len(t["rows"]) for t in catalog["planning_tables"]),
                "final_status":final["status"],"verification":final["verification"],"requests":calls}
        (destination/"http-smoke-results.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
        print(json.dumps({k:v for k,v in report.items() if k!="requests"}|{"request_count":len(calls)}))
        return report
    finally:
        client.close()

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--base-url",default="http://127.0.0.1:8000")
    parser.add_argument("--credentials",default=".local/credentials.json")
    parser.add_argument("--output",default=".local/demo")
    args=parser.parse_args()
    run(args.base_url,args.credentials,args.output)
