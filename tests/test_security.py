import base64
import io
import zipfile
import pytest

def test_auth_and_token_storage(harness):
    assert harness.client.get("/api/companies").status_code==401
    assert harness.client.get("/api/companies",headers={"Authorization":"Bearer invalid"}).status_code==401
    with harness.app.state.database.transaction() as db:
        hashes=[r[0] for r in db.execute("SELECT token_hash FROM principals")]
        assert not any(i["token"] in hashes for i in harness.identities.values())
        db.execute("UPDATE principals SET revoked=1 WHERE id=?",(harness.identities["operator"]["id"],))
    harness.request("GET","/api/me",role="operator",expected=401)

def test_cross_tenant_and_company_access_isolated(harness):
    company,_,e=harness.company()
    path=f'/api/companies/{company["id"]}'
    for role in ["other","ungranted"]:
        for suffix in ["","/facts","/evidence","/structure","/audit","/export","/obligations","/questionnaire/aoc4"]:
            harness.request("GET",path+suffix,role=role,expected=404)
        harness.request("GET",f'/api/evidence/{e["id"]}/download',role=role,expected=404)
        assert harness.request("GET","/api/companies",role=role).json()["companies"]==[]
    harness.request("POST",path+"/grants",{"principal_id":harness.identities["other"]["id"]},expected=404)
    harness.request("POST",path+"/facts",{"field":"name","value":"x","valid_from":"2026-01-01"},role="director",expected=403)
    harness.request("DELETE",path+"/grants/"+harness.identities["professional"]["id"])
    harness.request("GET",path,role="professional",expected=404)

def test_cross_company_fact_evidence_reference_rejected(harness):
    first,_,e=harness.company(full=False)
    second,_,_=harness.company(full=False,cin="U72900AS2024PTC123457")
    harness.request("POST",f'/api/companies/{second["id"]}/facts',
                    {"field":"coi_evidence_id","value":e["id"],"valid_from":"2026-01-01"},expected=422)

def test_original_evidence_integrity_and_retention(harness):
    company,_,e=harness.company(full=False)
    raw=harness.request("GET",f'/api/evidence/{e["id"]}/download')
    assert raw.content==b"synthetic source evidence" and raw.headers["x-content-sha256"]==e["sha256"]
    harness.request("PUT",f'/api/evidence/{e["id"]}/retention',{"legal_hold":True,"reason":"Preserve statutory evidence"})
    harness.request("DELETE",f'/api/evidence/{e["id"]}',expected=409)
    harness.request("PUT",f'/api/evidence/{e["id"]}/retention',{"legal_hold":False,"reason":"Test fixture release"})
    harness.request("DELETE",f'/api/evidence/{e["id"]}')
    harness.request("GET",f'/api/evidence/{e["id"]}/download',expected=410)

def test_referenced_evidence_cannot_be_deleted(harness):
    company,_,e=harness.company()
    harness.request("DELETE",f'/api/evidence/{e["id"]}',expected=409)

@pytest.mark.parametrize("filename,media,content,status",[
    ("../../x","text/plain",b"hello",422),
    ("x.pdf","application/pdf",b"not pdf",422),
    ("x.json","application/json",b"{bad",422),
    ("x.txt","text/plain",b"\xff",422),
    ("x.docx","application/vnd.openxmlformats-officedocument.wordprocessingml.document",b"not zip",422),
])
def test_evidence_validation(harness,filename,media,content,status):
    company,_,_=harness.company(full=False)
    harness.request("POST",f'/api/companies/{company["id"]}/evidence',
        {"filename":filename,"media_type":media,"content_base64":base64.b64encode(content).decode(),
         "purpose":"company_record","observed_on":"2026-01-01"},expected=status)

def test_docx_archive_traversal_blocked(harness):
    company,_,_=harness.company(full=False)
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,"w") as z:
        z.writestr("word/document.xml","<x/>")
        z.writestr("../payload","bad")
    harness.request("POST",f'/api/companies/{company["id"]}/evidence',{"filename":"x.docx",
        "media_type":"application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "content_base64":base64.b64encode(buf.getvalue()).decode(),"purpose":"company_record","observed_on":"2026-01-01"},expected=422)

def test_security_headers_and_large_body(harness):
    r=harness.client.get("/health")
    assert r.headers["cache-control"]=="no-store"
    assert r.headers["x-content-type-options"]=="nosniff"
    r=harness.client.post("/api/companies",content=b"x"*7_000_001,
        headers={"Content-Type":"application/json","Authorization":"Bearer "+harness.identities["owner"]["token"]})
    assert r.status_code==413
