from datetime import date
from decimal import Decimal
from typing import Annotated, Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CIN = Annotated[str, Field(pattern=r"^[LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}$")]
Amount = Annotated[Decimal, Field(ge=0, max_digits=22, decimal_places=2, allow_inf_nan=False)]
Text = Annotated[str, Field(min_length=1, max_length=500)]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Address(Model):
    line1: Text
    line2: str = ""
    city: Text
    state: Text
    pin: Annotated[str, Field(pattern=r"^\d{6}$")]
    country: Literal["IN"] = "IN"


class Period(Model):
    start: date
    end: date

    @model_validator(mode="after")
    def ordered(self):
        if self.end < self.start:
            raise ValueError("Period end precedes start")
        return self


class Member(Model):
    member_id: Text
    name: Text
    foreign: bool = False


class ShareClass(Model):
    class_id: Text
    name: Text
    issued_shares: Annotated[int, Field(ge=0)]
    face_value_inr: Amount


class Holding(Model):
    member_id: Text
    class_id: Text
    shares: Annotated[int, Field(ge=0)]


class Director(Model):
    name: Text
    din: Annotated[str, Field(pattern=r"^\d{8}$")]
    appointment_date: date
    cessation_date: date | None = None
    days_in_india: Annotated[int, Field(ge=0, le=366)] | None = None
    residency_period: Period | None = None

    @model_validator(mode="after")
    def chronology(self):
        if self.cessation_date and self.cessation_date < self.appointment_date:
            raise ValueError("Cessation precedes appointment")
        return self


class Auditor(Model):
    name: Text
    registration_number: Text
    appointment_date: date
    tenure_end: date | None = None
    consent_confirmed: bool | None = None
    eligibility_confirmed: bool | None = None

    @model_validator(mode="after")
    def chronology(self):
        if self.tenure_end and self.tenure_end < self.appointment_date:
            raise ValueError("Auditor tenure ends before appointment")
        return self


class Signatory(Model):
    name: Text
    role: Text
    identifier: Text
    dsc_associated: bool | None = None


class Meeting(Model):
    kind: Literal["board", "agm", "egm"]
    scheduled_date: date
    held: bool | None = None
    notice_date: date | None = None
    notice_served: bool | None = None
    attendance: list[Text] = []
    decisions: list[Text] = []
    votes: dict[str, Annotated[int, Field(ge=0, strict=True)]] = {}


class PriorFiling(Model):
    form: Text
    financial_year: Period
    srn: Text
    status: Text
    evidence_id: str
    observed_on: date


class Facts(Model):
    name: Text | None = None
    incorporation_date: date | None = None
    company_class: Literal["private", "public", "opc", "llp", "section8", "producer"] | None = None
    company_status: Literal["active", "dormant", "struck_off", "insolvency", "unknown"] | None = None
    registered_address: Address | None = None
    financial_year: Period | None = None
    domestic: bool | None = None
    listed: bool | None = None
    limited_by_shares: bool | None = None
    regulated: bool | None = None
    government_company: bool | None = None
    members: list[Member] | None = None
    share_classes: list[ShareClass] | None = None
    shareholdings: list[Holding] | None = None
    beneficial_ownership_flag: bool | None = None
    holding_company: bool | None = None
    subsidiary: bool | None = None
    group_relationships: list[Text] | None = None
    foreign_ownership: bool | None = None
    directors: list[Director] | None = None
    auditor: Auditor | None = None
    signatories: list[Signatory] | None = None
    paid_up_capital_inr: Amount | None = None
    turnover_inr: Amount | None = None
    turnover_period: Period | None = None
    loans_flag: bool | None = None
    deposits_flag: bool | None = None
    related_party_flag: bool | None = None
    xbrl_required: bool | None = None
    ind_as_required: bool | None = None
    complex_securities: bool | None = None
    meetings: list[Meeting] | None = None
    agm_date: date | None = None
    agm_held: bool | None = None
    first_agm: bool | None = None
    adjourned_agm: bool | None = None
    statements_adopted: bool | None = None
    approvals: list[Text] | None = None
    extension_evidence_ids: list[str] | None = None
    business_activities: list[Text] | None = None
    operating_states: list[Text] | None = None
    employee_count: Annotated[int, Field(ge=0)] | None = None
    tax_registrations: list[Text] | None = None
    labour_registrations: list[Text] | None = None
    sector_licences: list[Text] | None = None
    prior_filings: list[PriorFiling] | None = None
    outstanding_notices: list[Text] | None = None
    coi_evidence_id: str | None = None
    moa_evidence_id: str | None = None
    aoa_evidence_id: str | None = None
    audited_statements_evidence_id: str | None = None
    board_report_evidence_id: str | None = None
    auditor_report_evidence_id: str | None = None
    auditor_appointment_kind: Literal["first", "subsequent", "casual_vacancy"] | None = None
    commencement_applicable: bool | None = None
    subscription_paid: bool | None = None
    director_change_kind: Literal["appointment", "resignation", "other_cessation"] | None = None
    director_change_date: date | None = None
    director_consent_evidence_id: str | None = None
    director_cessation_evidence_id: str | None = None

    @field_validator("paid_up_capital_inr", "turnover_inr", mode="before")
    @classmethod
    def no_bool_money(cls, v):
        if isinstance(v, bool):
            raise ValueError("An amount cannot be boolean")
        return v


class CompanyCreate(Model):
    cin: CIN
    name: Text


class FactInput(Model):
    field: str
    value: Any
    evidence_id: str | None = None
    provenance: Literal["user_declaration", "document", "provider"] = "user_declaration"
    valid_from: date
    valid_to: date | None = None

    @model_validator(mode="after")
    def check(self):
        if self.field not in Facts.model_fields:
            raise ValueError("Unknown field")
        if self.valid_to and self.valid_to < self.valid_from:
            raise ValueError("Fact validity is reversed")
        parsed = Facts.model_validate({self.field: self.value})
        self.value = parsed.model_dump(mode="json")[self.field]
        if self.provenance != "user_declaration" and not self.evidence_id:
            raise ValueError("Document/provider candidates require evidence")
        return self


class FactConfirm(Model):
    fact_ids: Annotated[list[str], Field(min_length=1, max_length=100)]
    replace_conflicts: bool = False


class EvidenceInput(Model):
    filename: Annotated[str, Field(min_length=1, max_length=160, pattern=r"^[\w .-]+$")]
    media_type: Literal["application/pdf", "application/json", "text/plain", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
    content_base64: Annotated[str, Field(max_length=6_700_000)]
    purpose: Literal["company_record", "signed_document", "filing_receipt", "professional_certificate", "extension", "other"]
    observed_on: date


class Consent(Model):
    purpose: Text
    allowed: bool
    version: Text


class EvaluationRequest(Model):
    as_of: date


class Grant(Model):
    principal_id: str


class Review(Model):
    decision: Literal["approved", "changes_requested"]
    comments: Annotated[str, Field(min_length=1, max_length=5000)]
    certification_evidence_id: str | None = None


class PackRequest(Model):
    final: bool = False


class FilingCreate(Model):
    pack_id: str
    srn: Annotated[str, Field(pattern=r"^[A-Za-z0-9-]{5,40}$")]


class FilingObservation(Model):
    evidence_id: str
    cin: CIN
    form: str
    financial_year: Period
    srn: str
    status: Literal["submitted", "payment_pending", "resubmission", "rejected", "recorded", "approved"]
    observed_on: date
    signatory_confirmed: bool = False
    payment_confirmed: bool = False
    certification_confirmed: bool = False
    signed_document_evidence_id: str | None = None
    professional_certificate_evidence_id: str | None = None


class SourceSnapshot(Model):
    source_id: str
    title: Text
    url: str
    text: Annotated[str, Field(min_length=10, max_length=100000)]
    published_on: date
    effective_from: date
    locator: Text
    synthetic: bool = True


class SourceVerification(Model):
    notes: Text


class Clause(Model):
    field: str
    op: Literal["eq", "ne", "lt", "lte", "gt", "gte", "contains"]
    value: Any

    @field_validator("field")
    @classmethod
    def known(cls, value):
        if value not in Facts.model_fields:
            raise ValueError("Unknown fact in rule")
        return value


class RuleInput(Model):
    rule_key: Annotated[str, Field(pattern=r"^[a-z0-9_]{3,80}$")]
    workflow: Literal["board_agm", "aoc4", "mgt7", "mgt7a", "adt1", "inc20a", "dir12"]
    version: Annotated[int, Field(ge=1)]
    effective_from: date
    effective_to: date | None = None
    source_snapshot_ids: Annotated[list[str], Field(min_length=1)]
    required_fields: list[str]
    conditions: list[Clause] = []
    exclusions: list[Clause] = []
    trigger_field: str | None = None
    days_after: Annotated[int, Field(ge=0, le=730)] | None = None
    required_evidence_fields: list[str] = []
    professional_certification_required: bool = False
    synthetic: bool = True
    interpretation: Text

    @model_validator(mode="after")
    def validate_rule(self):
        if self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("Rule validity reversed")
        for name in self.required_fields + self.required_evidence_fields:
            if name not in Facts.model_fields:
                raise ValueError(f"Unknown fact: {name}")
        if bool(self.trigger_field) != (self.days_after is not None):
            raise ValueError("Deadline requires trigger and duration")
        if self.trigger_field and self.trigger_field not in {"agm_date", "director_change_date", "incorporation_date"}:
            raise ValueError("Deadline trigger must be a supported date")
        return self


class RuleFixture(Model):
    name: Text
    facts: Facts
    as_of: date
    expected_status: Literal["applicable", "not_applicable", "needs_information", "specialist_review"]
    expected_due_date: date | None = None


class RuleApproval(Model):
    reviewer_notes: Text
    fixtures: Annotated[list[RuleFixture], Field(min_length=2)]


class Lookup(Model):
    provider: Literal["mock", "sandbox", "apisetu", "ogd", "cashfree"]


class Ask(Model):
    question: Annotated[str, Field(min_length=1, max_length=2000)]
    use_ai: bool = False


class Retention(Model):
    legal_hold: bool
    retain_until: date | None = None
    reason: Text


class TemplateInput(Model):
    workflow: Literal["board_agm", "aoc4", "mgt7", "mgt7a", "adt1", "inc20a", "dir12"]
    version: Annotated[int, Field(ge=1)]
    source_snapshot_ids: Annotated[list[str], Field(min_length=1)]
    title: Text
    instructions: Annotated[list[Text], Field(min_length=1, max_length=30)]
    signatory_policy: Text
    synthetic: bool = True


class TemplateApproval(Model):
    notes: Text


class QuestionnaireAnswer(Model):
    answers: Annotated[list[FactInput], Field(min_length=1, max_length=100)]
