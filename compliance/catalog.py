"""Questionnaire and workflow catalog; exact planning tables are archived separately."""
import json
from pathlib import Path
from .models import Facts

DATA = Path(__file__).parent / "data"
GROUPS = {
    "company_identity": "name incorporation_date company_class company_status registered_address financial_year domestic listed limited_by_shares regulated government_company coi_evidence_id moa_evidence_id aoa_evidence_id".split(),
    "ownership": "members share_classes shareholdings beneficial_ownership_flag holding_company subsidiary group_relationships foreign_ownership complex_securities".split(),
    "governance": "directors auditor signatories auditor_appointment_kind director_change_kind director_change_date director_consent_evidence_id director_cessation_evidence_id".split(),
    "financial_context": "paid_up_capital_inr turnover_inr turnover_period loans_flag deposits_flag related_party_flag xbrl_required ind_as_required audited_statements_evidence_id board_report_evidence_id auditor_report_evidence_id commencement_applicable subscription_paid".split(),
    "meeting_history": "meetings agm_date agm_held first_agm adjourned_agm statements_adopted approvals extension_evidence_ids".split(),
    "other_obligations": "business_activities operating_states employee_count tax_registrations labour_registrations sector_licences".split(),
    "filing_history": "prior_filings outstanding_notices".split(),
}
WORKFLOWS = {
    "board_agm": {"form": "BOARD-AGM", "sources": ["S21"], "fields": ["meetings", "directors", "signatories"], "output": "Meeting notice, agenda, resolution and factual minutes preparation worksheet"},
    "aoc4": {"form": "AOC-4", "sources": ["S22"], "fields": ["financial_year", "agm_held", "agm_date", "first_agm", "adjourned_agm", "statements_adopted", "audited_statements_evidence_id", "board_report_evidence_id", "auditor_report_evidence_id", "xbrl_required", "ind_as_required"], "output": "Financial statements filing worksheet and attachments index"},
    "mgt7": {"form": "MGT-7", "sources": ["S23"], "fields": ["financial_year", "members", "directors", "meetings", "share_classes", "shareholdings", "turnover_inr", "turnover_period", "paid_up_capital_inr", "holding_company", "subsidiary"], "output": "Annual return worksheet and ownership schedule"},
    "mgt7a": {"form": "MGT-7A", "sources": ["S23", "S27"], "fields": ["financial_year", "members", "directors", "meetings", "share_classes", "shareholdings", "turnover_inr", "turnover_period", "paid_up_capital_inr", "holding_company", "subsidiary"], "output": "Abridged annual return preparation worksheet"},
    "adt1": {"form": "ADT-1", "sources": ["S24"], "fields": ["auditor", "auditor_appointment_kind", "meetings", "signatories"], "output": "Auditor appointment and eligibility worksheet"},
    "inc20a": {"form": "INC-20A", "sources": ["S25"], "fields": ["incorporation_date", "commencement_applicable", "subscription_paid", "coi_evidence_id", "signatories"], "output": "Commencement preparation worksheet"},
    "dir12": {"form": "DIR-12", "sources": ["S26"], "fields": ["directors", "director_change_kind", "director_change_date", "signatories"], "output": "Director change and supporting evidence worksheet"},
}
PROVIDERS = [
    {"id": "manual", "status": "available", "purpose": "User-confirmed input", "read": True, "file": False},
    {"id": "mock", "status": "synthetic_only", "purpose": "Local integration fixture", "read": True, "file": False},
    {"id": "sandbox", "status": "credentials_required", "purpose": "Commercial CIN lookup", "read": True, "file": False, "onboarding": "https://console.sandbox.co.in"},
    {"id": "apisetu", "status": "publisher_approval_required", "purpose": "Official API discovery", "read": False, "file": False, "onboarding": "https://partners.apisetu.gov.in/"},
    {"id": "ogd", "status": "resource_contract_required", "purpose": "Open-data reference import", "read": False, "file": False, "onboarding": "https://data.gov.in/help"},
    {"id": "cashfree", "status": "vendor_contract_required", "purpose": "Alternative lookup", "read": False, "file": False, "onboarding": "https://www.cashfree.com/kyb-solutions"},
    {"id": "openrouter", "status": "credentials_and_consent_required", "purpose": "Bounded explanation", "read": False, "file": False, "onboarding": "https://openrouter.ai/keys"},
    {"id": "esign", "status": "provider_approval_required", "purpose": "Supporting-document signatures", "read": False, "file": False, "onboarding": "https://www.cca.gov.in/avail_service.html"},
    {"id": "gst", "status": "gsp_agreement_required", "purpose": "Future GST module", "read": False, "file": False, "onboarding": "https://www.gstn.org.in/faqs-category-details"},
    {"id": "mca_filing", "status": "manual_handoff", "purpose": "Authorized user/professional portal filing", "read": False, "file": False, "onboarding": "https://www.mca.gov.in/"},
]

def tables():
    return json.loads((DATA / "plan_tables.json").read_text(encoding="utf-8"))

def sources():
    return json.loads((DATA / "sources.json").read_text(encoding="utf-8"))

def required_fields(workflow, facts):
    fields = list(WORKFLOWS[workflow]["fields"])
    if workflow in {"aoc4", "mgt7", "mgt7a"}:
        fields += ["agm_held", "agm_date", "first_agm", "adjourned_agm", "extension_evidence_ids"]
    if workflow == "dir12":
        if facts.get("director_change_kind") == "appointment":
            fields.append("director_consent_evidence_id")
        elif facts.get("director_change_kind") in {"resignation", "other_cessation"}:
            fields.append("director_cessation_evidence_id")
    return list(dict.fromkeys(fields))

def question(field):
    return {"field": field, "question": "Provide " + field.replace("_", " ") + ".",
            "why_needed": "Required by the selected preparation workflow; retained with source and confirmation.",
            "allows_unknown": True, "schema": Facts.model_json_schema()["properties"][field]}

