import base64
from copy import deepcopy
import json
from pathlib import Path
import pytest
from starlette.testclient import TestClient
from compliance.app import create_app
from compliance.config import Settings

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = json.loads((ROOT / "examples/company.json").read_text())

class Harness:
    def __init__(self, client, app, identities):
        self.client, self.app, self.identities = client, app, identities

    def request(self, method, path, payload=None, role="owner", expected=200, **kwargs):
        r = self.client.request(method, path, json=payload, headers={"Authorization": "Bearer "+self.identities[role]["token"]}, **kwargs)
        assert r.status_code == expected, (method, path, r.status_code, r.text[:2000])
        return r

    def evidence(self, company_id, purpose="company_record", content=b"synthetic source evidence"):
        return self.request("POST", f"/api/companies/{company_id}/evidence", {
            "filename": "synthetic.txt", "media_type": "text/plain", "content_base64": base64.b64encode(content).decode(),
            "purpose": purpose, "observed_on": "2026-09-30"}, expected=201).json()

    def company(self, full=True, cin=None):
        row = self.request("POST", "/api/companies", {"cin": cin or EXAMPLE["cin"], "name": EXAMPLE["name"]}, expected=201).json()
        for role in ["professional", "operator", "director"]:
            self.request("POST", f'/api/companies/{row["id"]}/grants', {"principal_id": self.identities[role]["id"]}, expected=201)
        e = self.evidence(row["id"])
        facts = json.loads(json.dumps(EXAMPLE["facts"]).replace("EVIDENCE_ID", e["id"]))
        if full:
            candidates = []
            for key, value in facts.items():
                candidates.append(self.request("POST", f'/api/companies/{row["id"]}/facts',
                    {"field": key, "value": value, "valid_from": "2026-04-01", "evidence_id": e["id"],
                     "provenance": "document"}, expected=201).json()["id"])
            self.request("POST", f'/api/companies/{row["id"]}/facts/confirm', {"fact_ids": candidates})
        return row, facts, e

    def source(self, source_id="S22", synthetic=True):
        register = self.request("GET", "/api/sources").json()["sources"]
        url = next(s for s in register if s["id"] == source_id)["urls"][0]
        row = self.request("POST", "/api/sources/snapshots", {
            "source_id": source_id, "title": "Synthetic reviewed test passage", "url": url,
            "text": "SYNTHETIC TEST ONLY. Ordinary fixture deadline is thirty days after the AGM.",
            "published_on": "2026-01-01", "effective_from": "2026-01-01", "locator": "synthetic fixture",
            "synthetic": synthetic}, expected=201).json()
        self.request("POST", f'/api/sources/snapshots/{row["id"]}/verify', {"notes":"Synthetic fixture verification, not legal approval"}, role="content_reviewer")
        return row

    def rule(self, facts, source, workflow="aoc4", certification=False, version=1, **overrides):
        body = {"rule_key":"fixture_"+workflow, "workflow":workflow, "version":version,
                "effective_from":"2026-01-01", "source_snapshot_ids":[source["id"]],
                "required_fields":["financial_year"], "conditions":[], "exclusions":[],
                "required_evidence_fields":[], "professional_certification_required":certification,
                "synthetic":True, "interpretation":"Synthetic preparation fixture; not legal advice."}
        expected_due = None
        if workflow in {"aoc4", "mgt7", "mgt7a"}:
            body.update(trigger_field="agm_date", days_after=30)
            expected_due = "2026-10-20"
        body.update(overrides)
        row = self.request("POST", "/api/rules", body, expected=201).json()
        valid = deepcopy(facts)
        invalid = {**valid, "company_class":"public"}
        fixtures = [
            {"name":"ordinary", "facts":valid, "as_of":"2026-09-30", "expected_status":"applicable", "expected_due_date":expected_due},
            {"name":"excluded", "facts":invalid, "as_of":"2026-09-30", "expected_status":"specialist_review"}
        ]
        self.request("POST", f'/api/rule-releases/{row["id"]}/approve',
                     {"reviewer_notes":"Approve synthetic fixture only", "fixtures":fixtures}, role="content_reviewer")
        return row

    def template(self, source, workflow="aoc4"):
        row = self.request("POST", "/api/templates", {"workflow":workflow, "version":1,
            "source_snapshot_ids":[source["id"]], "title":"Synthetic preparation worksheet",
            "instructions":["Verify all facts with the responsible professional."],
            "signatory_policy":"Synthetic test: director and professional as applicable; use official portal DSC instructions.",
            "synthetic":True}, expected=201).json()
        self.request("POST", f'/api/templates/{row["id"]}/approve', {"notes":"Synthetic test approval"}, role="content_reviewer")
        return row

    def prepared(self, workflow="aoc4", certification=False):
        company, facts, e = self.company()
        source = self.source()
        rule = self.rule(facts, source, workflow, certification)
        self.template(source, workflow)
        evaluation = self.request("POST", f'/api/companies/{company["id"]}/evaluate', {"as_of":"2026-09-30"}).json()
        ob = evaluation["obligations"][0]
        pack = self.request("POST", f'/api/obligations/{ob["id"]}/document-packs', {"final":True}, expected=201).json()
        return company, facts, ob, pack

@pytest.fixture
def harness(tmp_path):
    app = create_app(Settings(db_path=str(tmp_path/"test.sqlite3")))
    roles = ["owner", "operator", "director", "professional", "content_reviewer"]
    ids = {role: app.state.database.provision("tenant-one", role) for role in roles}
    ids["other"] = app.state.database.provision("tenant-two", "owner")
    ids["ungranted"] = app.state.database.provision("tenant-one", "professional")
    with TestClient(app) as client:
        yield Harness(client, app, ids)
