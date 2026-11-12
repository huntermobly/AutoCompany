import json
from compliance.http import api
from compliance.database import Database
from compliance.models import Facts

def test_every_route_has_openapi_request_contract_and_unique_operation_id(harness):
    spec=harness.client.get("/openapi.json").json()
    assert spec["openapi"]=="3.1.0"
    operations=[]
    for definition in api.definitions:
        op=spec["paths"][definition["path"]][definition["method"].lower()]
        operations.append(op["operationId"])
        assert op["security"]==[{"BearerAuth":[]}]
        if definition["model"]:
            assert "requestBody" in op
    assert len(operations)==len(set(operations))==48
    assert len(spec["components"]["schemas"]["Facts"]["properties"])==len(Facts.model_fields)
    assert harness.client.get("/").status_code==404
    assert harness.client.get("/docs").status_code==404

def test_database_persists_on_reopen_and_migration_is_idempotent(harness):
    company,_,_=harness.company(full=False)
    reopened=Database(harness.app.state.database.path)
    with reopened.transaction() as db:
        assert db.execute("SELECT count(*) FROM schema_migrations").fetchone()[0]==1
        row=db.execute("SELECT payload FROM records WHERE id=?",(company["id"],)).fetchone()
        assert json.loads(row[0])["cin"]==company["cin"]

def test_invalid_json_extra_fields_and_media_type(harness):
    headers={"Authorization":"Bearer "+harness.identities["owner"]["token"],"Content-Type":"application/json"}
    assert harness.client.post("/api/companies",content=b"{broken",headers=headers).status_code==422
    assert harness.client.post("/api/companies",json={"cin":"U72900AS2024PTC123456","name":"x","tenant_id":"injected"},headers=headers).status_code==422
    headers["Content-Type"]="text/plain"
    assert harness.client.post("/api/companies",content=b"{}",headers=headers).status_code==415
