# Implementation matrix — every original table row

All 81 original rows are preserved exactly in compliance/data/plan_tables.json and served by GET /api/catalog. Preserving and testing the data does not mean every future feature or legal obligation is implemented. This matrix distinguishes runnable mechanisms, preparation-only outputs and outstanding external work.

The complete original wording, acceptance criteria and references remain in original-plan.md. The table-preservation test compares every original Markdown table line, including headers and separators, to the API catalog.

## 2. What can actually be automated

| Row | Original item | Current status | Implementation / limit | Verification |
|---|---|---|---|---|
| table_1.1 | Explain applicable company law | Implemented mechanism; legal content pending | Versioned source/rule explanations; optional AI remains unverified | tests/test_rules.py; tests/test_release_boundaries.py; tests/test_providers.py |
| table_1.2 | Prefill company details | Implemented manual/mock; vendor contract tested | Candidates and evidence preserve provenance; no live vendor result | tests/test_profiles.py; tests/test_providers.py |
| table_1.3 | Organize ownership, directors and responsibilities | Implemented foundation | Membership, holdings and directors stored; share references/totals checked; no automatic restructuring advice | tests/test_profiles.py |
| table_1.4 | Generate resolutions, notices and supporting paperwork | Partial preparation output | DOCX/PDF worksheets and meeting drafts; full legal clauses/resolutions require template work | tests/test_documents_filings.py |
| table_1.5 | Prepare an MCA filing | Partial preparation output | Immutable worksheet and attachment index; no verified current portal field mapping | tests/test_documents_filings.py |
| table_1.6 | Sign supporting documents | Handoff only | Signature instructions and uploaded signed-document evidence; no eSign adapter | tests/test_documents_filings.py |
| table_1.7 | Sign an MCA form | Handoff only | DSC instructions; no signing or signature validation | tests/test_documents_filings.py |
| table_1.8 | Submit a government filing | Manual handoff | Submit returns 501; ledger tracks user/professional evidence | tests/test_documents_filings.py |
| table_1.9 | Update a company's official record | External action only | Local records never mutate government records | tests/test_documents_filings.py |

## 4. Initial customers and scope

| Row | Original item | Current status | Implementation / limit | Verification |
|---|---|---|---|---|
| table_2.1 | Profile and company structure | Implemented | 60 fields, candidate/confirmed provenance and conflicts | tests/test_profiles.py |
| table_2.2 | Applicability and calendar | Implemented mechanism; legal content pending | Rule/date/fact versions and evidence gaps; no enabled production rulebook | tests/test_rules.py; tests/test_release_boundaries.py |
| table_2.3 | Questionnaire | Implemented foundation | Missing/unknown conditional questions and saved candidates; no frontend | tests/test_profiles.py; tests/test_rules.py; tests/test_release_boundaries.py |
| table_2.4 | Meeting/document packs | Partial preparation output | Final-pack gates, actual-event minutes; generic worksheets need fuller reviewed legal templates | tests/test_documents_filings.py |
| table_2.5 | Annual filing preparation | Partial preparation output | AOC-4, MGT-7 and MGT-7A variants; live legal routing not seeded | tests/test_documents_filings.py; tests/test_rules.py; tests/test_release_boundaries.py |
| table_2.6 | Professional review | Implemented basic review | Separate professional approval or changes_requested; free-text comments, no structured field-comment UI | tests/test_documents_filings.py |
| table_2.7 | Filing handoff and evidence | Implemented manual ledger | SRN/download cannot complete filing; matching receipts and professional attestation required | tests/test_documents_filings.py |
| table_2.8 | Source-change review | Implemented on-demand mechanism | Snapshots/diffs/reviewer release gates; no periodic job or automated law extraction | tests/test_rules.py; tests/test_release_boundaries.py |
| table_2.9 | Routine event workflows | Partial event foundation | ADT-1, INC-20A and DIR-12 worksheets; current form-specific releases pending | tests/test_documents_filings.py; tests/test_rules.py; tests/test_release_boundaries.py |
| table_2.10 | Approved data provider | Contract implemented; live acceptance pending | Sandbox key/secret adapter and manual fallback | tests/test_providers.py |
| table_2.11 | Incorporation, OPC, LLP | Deferred | OPC/LLP/public/other out-of-scope routes return specialist review | tests/test_rules.py; tests/test_release_boundaries.py |
| table_2.12 | GST, tax, labour and state licences | Deferred | 60-field profile records related registrations; no tax/labour/licence rule packs | tests/test_profiles.py |

## Information to collect

| Row | Original item | Current status | Implementation / limit | Verification |
|---|---|---|---|---|
| table_3.1 | Company identity | Implemented and round-trip tested | Identity, dates, address, documents and classification | tests/test_profiles.py |
| table_3.2 | Ownership | Implemented and round-trip tested | Members, classes, holdings, ownership and group flags | tests/test_profiles.py |
| table_3.3 | Governance | Implemented and round-trip tested | DIN/director dates/residency, auditor and signatories | tests/test_profiles.py |
| table_3.4 | Financial context | Implemented and round-trip tested | Decimal INR amounts, periods, statements and transaction flags | tests/test_profiles.py; tests/test_rules.py; tests/test_release_boundaries.py |
| table_3.5 | Meeting history | Implemented and round-trip tested | Planned/held meetings, notice, votes, decisions, AGM/extension facts | tests/test_profiles.py; tests/test_documents_filings.py |
| table_3.6 | Other obligations | Collection implemented; domain modules deferred | Activities, states, employees and registration/licence lists | tests/test_profiles.py |
| table_3.7 | Filing history | Implemented and round-trip tested | Prior form/SRN/date/evidence and notices; manual completion semantics | tests/test_profiles.py; tests/test_documents_filings.py |

## 6. Workflow packs and document outputs

| Row | Original item | Current status | Implementation / limit | Verification |
|---|---|---|---|---|
| table_4.1 | Board/AGM documentation | Partial template family | Worksheet, notice/agenda and factual minutes; full SS-1/SS-2 legal templates pending | tests/test_documents_filings.py |
| table_4.2 | AOC-4 preparation | Partial template family | Financial statement worksheet and index; current kit/variant approval pending | tests/test_documents_filings.py |
| table_4.3 | MGT-7/7A preparation | Partial template family | Both annual-return variants render; current classification/certification rules pending | tests/test_documents_filings.py; tests/test_rules.py; tests/test_release_boundaries.py |
| table_4.4 | Auditor appointment / ADT-1 | Partial template family | Auditor facts worksheet; first-appointment review guard; appointment letter templates pending | tests/test_documents_filings.py; tests/test_rules.py; tests/test_release_boundaries.py |
| table_4.5 | Commencement / INC-20A | Partial template family | Commencement facts worksheet; approved applicability/attestation rules pending | tests/test_documents_filings.py |
| table_4.6 | Director changes / DIR-12 | Partial template family | Director event worksheet; conditional consent/cessation evidence enforced | tests/test_documents_filings.py; tests/test_rules.py; tests/test_release_boundaries.py |

## 7. Architecture

| Row | Original item | Current status | Implementation / limit | Verification |
|---|---|---|---|---|
| table_5.1 | Profile and evidence | Implemented foundation | SQLite versioned facts, original evidence and explicit confirmation | tests/test_profiles.py; tests/test_security.py |
| table_5.2 | Rules engine | Implemented | Deterministic applicability/date arithmetic and source-backed releases | tests/test_rules.py; tests/test_release_boundaries.py |
| table_5.3 | Questionnaire engine | Partial | Missing/unknown/candidate states and conflicts; no explicit field-level not-applicable/disputed answer enum | tests/test_profiles.py |
| table_5.4 | Knowledge retrieval | Bounded retrieval implemented | Fetch only snapshots attached to evaluated rule; no semantic/vector search | tests/test_providers.py; tests/test_security.py |
| table_5.5 | AI assistant | Explanation adapter implemented | No tools/actions; validated source IDs; OCR/extraction/question-generation remains deferred | tests/test_providers.py |
| table_5.6 | Template engine | Partial | Versioned preparation templates and binary exports; full official form mapping pending | tests/test_documents_filings.py |
| table_5.7 | Integration adapters | Implemented limited adapters | Sandbox, mock and OpenRouter contracts; other integrations capability-only | tests/test_providers.py |
| table_5.8 | Review and filing ledger | Implemented manual ledger | Review/state/receipt gates; signatures and portal status rely on attestation | tests/test_documents_filings.py |
| table_5.9 | Source monitor | Partial | On-demand allowlisted bounded fetch/hash plus manual snapshot diff; no scheduled ingestion | tests/test_rules.py; tests/test_release_boundaries.py |

## 10. Delivery plan

| Row | Original item | Current status | Implementation / limit | Verification |
|---|---|---|---|---|
| table_6.1 | Confirm customer segment, source register, professional reviewer, provider applications | Partly complete; business approvals outstanding | Source register/segment recorded; professional appointment/vendor applications not performed | Catalog preservation test only |
| table_6.2 | Authentication, isolation, profile, evidence, questionnaire, structure view | Backend foundation implemented | Local auth/isolation/profile/questionnaire/structure; no frontend | tests/test_profiles.py; tests/test_security.py |
| table_6.3 | Rules/calendar, meeting templates, annual preparation | Mechanisms implemented; legal acceptance outstanding | Synthetic fixture/calculation/pack checks; no production legal sign-off | tests/test_rules.py; tests/test_release_boundaries.py; tests/test_documents_filings.py |
| table_6.4 | AI explanations/extraction, review workspace, filing evidence | Partial | Explanation adapter, review APIs and evidence ledger; extraction/review UI deferred | tests/test_providers.py; tests/test_documents_filings.py |
| table_6.5 | Source monitoring, provider integration, pilot and hardening | Partial; pilot/hardening outstanding | Monitor/provider contracts available; customer pilot and deployment not performed | tests/test_rules.py; tests/test_release_boundaries.py; tests/test_providers.py |

## 13. Pre-launch decisions and tests

| Row | Original item | Current status | Implementation / limit | Verification |
|---|---|---|---|---|
| table_7.1 | Founder | Human decision outstanding | Account identity, domain and commercial applications not created | Catalog preservation test only |
| table_7.2 | CA/CS reviewer | Professional acceptance outstanding | No CA/CS legal certification is implied by software tests | Synthetic review gates tested |
| table_7.3 | Engineering | Contract tests complete; live check outstanding | Object/list envelopes, identity mismatch, missing keys, outage/quota covered | tests/test_providers.py |
| table_7.4 | Legal/privacy | Human review outstanding | Retention primitives exist; current privacy/processor obligations not certified | tests/test_security.py; catalog preservation |
| table_7.5 | Product | Human decision outstanding | No pilot users, pricing or service promises established | Catalog preservation test only |

## 14. Source register

| Row | Original item | Current status | Implementation / limit | Verification |
|---|---|---|---|---|
| table_8.1 | S1 — [Government of India MCA directory](https://igod.gov.in/organization/13) | Reference retained; not an approved legal release | Exact source ID, links and purpose retained. Register starts not_reviewed; live availability and current law not asserted. | tests/test_profiles.py; tests/test_rules.py; tests/test_release_boundaries.py |
| table_8.2 | S2 — [mca.org](https://www.mca.org/) | Reference retained; not an approved legal release | Exact source ID, links and purpose retained. Register starts not_reviewed; live availability and current law not asserted. | tests/test_profiles.py; tests/test_rules.py; tests/test_release_boundaries.py |
| table_8.3 | S3 — [MCA V3 consolidated FAQ](https://www.mca.gov.in/content/dam/mca/pdf/V3_Consolidated_FAQ_Dated_26042022.pdf) | Reference retained; not an approved legal release | Exact source ID, links and purpose retained. Register starts not_reviewed; live availability and current law not asserted. | tests/test_profiles.py; tests/test_rules.py; tests/test_release_boundaries.py |
| table_8.4 | S4 — [MCA incorporation and linked-filings FAQ](https://www.mca.gov.in/Ministry/pdf/SPICe%2Band_linked_filings_FAQs_V3_13%20Jan_2022_updated.pdf) | Reference retained; not an approved legal release | Exact source ID, links and purpose retained. Register starts not_reviewed; live availability and current law not asserted. | tests/test_profiles.py; tests/test_rules.py; tests/test_release_boundaries.py |
| table_8.5 | S5 — [API Setu onboarding SOP](https://cdn.apisetu.gov.in/portal/assets/SOP-APISETU.pdf) | Reference retained; not an approved legal release | Exact source ID, links and purpose retained. Register starts not_reviewed; live availability and current law not asserted. | tests/test_profiles.py; tests/test_rules.py; tests/test_release_boundaries.py |
| table_8.6 | S6 — [API Setu MCA verification description](https://blog.apisetu.gov.in/benefits-of-api-setu-over-financial-technology/) | Reference retained; not an approved legal release | Exact source ID, links and purpose retained. Register starts not_reviewed; live availability and current law not asserted. | tests/test_profiles.py; tests/test_rules.py; tests/test_release_boundaries.py |
| table_8.7 | S7 — [API Setu permitted access](https://docs.apisetu.gov.in/document-central/terms-of-use/Permitted%20Access.html) | Reference retained; not an approved legal release | Exact source ID, links and purpose retained. Register starts not_reviewed; live availability and current law not asserted. | tests/test_profiles.py; tests/test_rules.py; tests/test_release_boundaries.py |
| table_8.8 | S8 — [OGD help](https://data.gov.in/help) | Reference retained; not an approved legal release | Exact source ID, links and purpose retained. Register starts not_reviewed; live availability and current law not asserted. | tests/test_profiles.py; tests/test_rules.py; tests/test_release_boundaries.py |
| table_8.9 | S9 — [Company Master Data catalog](https://data.gov.in/catalog/company-master-data) | Reference retained; not an approved legal release | Exact source ID, links and purpose retained. Register starts not_reviewed; live availability and current law not asserted. | tests/test_profiles.py; tests/test_rules.py; tests/test_release_boundaries.py |
| table_8.10 | S10 — [Sandbox MCA overview](https://developer.sandbox.co.in/api-reference/kyc/mca/overview) | Reference retained; not an approved legal release | Exact source ID, links and purpose retained. Register starts not_reviewed; live availability and current law not asserted. | tests/test_profiles.py; tests/test_rules.py; tests/test_release_boundaries.py |
| table_8.11 | S11 — [Sandbox key creation](https://help.sandbox.co.in/portal/en/kb/articles/generate-your-api-keys) | Reference retained; not an approved legal release | Exact source ID, links and purpose retained. Register starts not_reviewed; live availability and current law not asserted. | tests/test_profiles.py; tests/test_rules.py; tests/test_release_boundaries.py |
| table_8.12 | S12 — [Sandbox quickstart](https://developer.sandbox.co.in/guides/get-started/quickstart) | Reference retained; not an approved legal release | Exact source ID, links and purpose retained. Register starts not_reviewed; live availability and current law not asserted. | tests/test_profiles.py; tests/test_rules.py; tests/test_release_boundaries.py |
| table_8.13 | S13 — [Sandbox Company Master Data](https://developer.sandbox.co.in/api-reference/kyc/mca/company_master_data) | Reference retained; not an approved legal release | Exact source ID, links and purpose retained. Register starts not_reviewed; live availability and current law not asserted. | tests/test_profiles.py; tests/test_rules.py; tests/test_release_boundaries.py |
| table_8.14 | S14 — [Cashfree KYB](https://www.cashfree.com/kyb-solutions) | Reference retained; not an approved legal release | Exact source ID, links and purpose retained. Register starts not_reviewed; live availability and current law not asserted. | tests/test_profiles.py; tests/test_rules.py; tests/test_release_boundaries.py |
| table_8.15 | S15 — [OpenRouter authentication](https://openrouter.ai/docs/api_reference/authentication) | Reference retained; not an approved legal release | Exact source ID, links and purpose retained. Register starts not_reviewed; live availability and current law not asserted. | tests/test_profiles.py; tests/test_rules.py; tests/test_release_boundaries.py |
| table_8.16 | S16 — [OpenRouter provider policies](https://openrouter.ai/docs/guides/privacy/provider-logging) | Reference retained; not an approved legal release | Exact source ID, links and purpose retained. Register starts not_reviewed; live availability and current law not asserted. | tests/test_profiles.py; tests/test_rules.py; tests/test_release_boundaries.py |
| table_8.17 | S17 — [CCA service access](https://www.cca.gov.in/avail_service.html) and [ASP onboarding](https://www.cca.gov.in/sites/files/pdf/esign/CCA-ASP.pdf) | Reference retained; not an approved legal release | Exact source ID, links and purpose retained. Register starts not_reviewed; live availability and current law not asserted. | tests/test_profiles.py; tests/test_rules.py; tests/test_release_boundaries.py |
| table_8.18 | S18 — [GSTN FAQs](https://www.gstn.org.in/faqs-category-details) | Reference retained; not an approved legal release | Exact source ID, links and purpose retained. Register starts not_reviewed; live availability and current law not asserted. | tests/test_profiles.py; tests/test_rules.py; tests/test_release_boundaries.py |
| table_8.19 | S19 — [NSWS FAQs](https://www.nsws.gov.in/faqs) | Reference retained; not an approved legal release | Exact source ID, links and purpose retained. Register starts not_reviewed; live availability and current law not asserted. | tests/test_profiles.py; tests/test_rules.py; tests/test_release_boundaries.py |
| table_8.20 | S20 — [Companies Act, India Code](https://www.indiacode.nic.in/bitstream/123456789/2114/5/A2013-18.pdf) | Reference retained; not an approved legal release | Exact source ID, links and purpose retained. Register starts not_reviewed; live availability and current law not asserted. | tests/test_profiles.py; tests/test_rules.py; tests/test_release_boundaries.py |
| table_8.21 | S21 — [ICSI revised SS-1/SS-2 announcement](https://www.icsi.edu/media/webmodules/Announcement_on_Revised_Secretarial_Standards_13022024.pdf) | Reference retained; not an approved legal release | Exact source ID, links and purpose retained. Register starts not_reviewed; live availability and current law not asserted. | tests/test_profiles.py; tests/test_rules.py; tests/test_release_boundaries.py |
| table_8.22 | S22 — [Companies Act section 137](https://www.indiacode.nic.in/bitstream/123456789/2114/5/A2013-18.pdf?v=20260519200129) | Reference retained; not an approved legal release | Exact source ID, links and purpose retained. Register starts not_reviewed; live availability and current law not asserted. | tests/test_profiles.py; tests/test_rules.py; tests/test_release_boundaries.py |
| table_8.23 | S23 — [MCA management and administration amendment](https://www.mca.gov.in/Ministry/pdf/CompaniesMgmtAdminAmndtRules_11032021.pdf) | Reference retained; not an approved legal release | Exact source ID, links and purpose retained. Register starts not_reviewed; live availability and current law not asserted. | tests/test_profiles.py; tests/test_rules.py; tests/test_release_boundaries.py |
| table_8.24 | S24 — [MCA audit/auditor rules amendment](https://www.mca.gov.in/Ministry/pdf/CompaniesAuditAuditorsAdmendmentRules2018_19022018.pdf) | Reference retained; not an approved legal release | Exact source ID, links and purpose retained. Register starts not_reviewed; live availability and current law not asserted. | tests/test_profiles.py; tests/test_rules.py; tests/test_release_boundaries.py |
| table_8.25 | S25 — [MCA INC-20A kit](https://www.mca.gov.in/content/dam/mca-aem-forms/instructionkits/Instruction%20Kit_INC-20A.pdf) | Reference retained; not an approved legal release | Exact source ID, links and purpose retained. Register starts not_reviewed; live availability and current law not asserted. | tests/test_profiles.py; tests/test_rules.py; tests/test_release_boundaries.py |
| table_8.26 | S26 — [MCA DIR-12 kit](https://www.mca.gov.in/content/dam/mca/mca-forms-instruction-kit/Instruction%20Kit_Form%20No%20DIR%2012.pdf) | Reference retained; not an approved legal release | Exact source ID, links and purpose retained. Register starts not_reviewed; live availability and current law not asserted. | tests/test_profiles.py; tests/test_rules.py; tests/test_release_boundaries.py |
| table_8.27 | S27 — [Gazette G.S.R. 880(E), 1 December 2025](https://egazette.gov.in/WriteReadData/2025/268124.pdf) | Reference retained; not an approved legal release | Exact source ID, links and purpose retained. Register starts not_reviewed; live availability and current law not asserted. | tests/test_profiles.py; tests/test_rules.py; tests/test_release_boundaries.py |
| table_8.28 | S28 — [MeitY DPDP Rules and enforcement documents](https://www.meity.gov.in/documents/act-and-policies/digital-personal-data-protection-rules-2025-gDOxUjMtQWa?pageTitle=Digital-Personal-Data-Protection-Rules-2025%3B) | Reference retained; not an approved legal release | Exact source ID, links and purpose retained. Register starts not_reviewed; live availability and current law not asserted. | tests/test_profiles.py; tests/test_rules.py; tests/test_release_boundaries.py |

## All 60 company fields

Every field below is schema-validated, stored with provenance, explicitly confirmed and round-trip tested by test_every_profile_field_roundtrips_with_evidence. Nested required members are defined in the catalog's facts_schema. Schema validation verifies structure, not the factual truth of a declaration.

| Group | Field |
|---|---|
| company_identity | name |
| company_identity | incorporation_date |
| company_identity | company_class |
| company_identity | company_status |
| company_identity | registered_address |
| company_identity | financial_year |
| company_identity | domestic |
| company_identity | listed |
| company_identity | limited_by_shares |
| company_identity | regulated |
| company_identity | government_company |
| company_identity | coi_evidence_id |
| company_identity | moa_evidence_id |
| company_identity | aoa_evidence_id |
| ownership | members |
| ownership | share_classes |
| ownership | shareholdings |
| ownership | beneficial_ownership_flag |
| ownership | holding_company |
| ownership | subsidiary |
| ownership | group_relationships |
| ownership | foreign_ownership |
| ownership | complex_securities |
| governance | directors |
| governance | auditor |
| governance | signatories |
| governance | auditor_appointment_kind |
| governance | director_change_kind |
| governance | director_change_date |
| governance | director_consent_evidence_id |
| governance | director_cessation_evidence_id |
| financial_context | paid_up_capital_inr |
| financial_context | turnover_inr |
| financial_context | turnover_period |
| financial_context | loans_flag |
| financial_context | deposits_flag |
| financial_context | related_party_flag |
| financial_context | xbrl_required |
| financial_context | ind_as_required |
| financial_context | audited_statements_evidence_id |
| financial_context | board_report_evidence_id |
| financial_context | auditor_report_evidence_id |
| financial_context | commencement_applicable |
| financial_context | subscription_paid |
| meeting_history | meetings |
| meeting_history | agm_date |
| meeting_history | agm_held |
| meeting_history | first_agm |
| meeting_history | adjourned_agm |
| meeting_history | statements_adopted |
| meeting_history | approvals |
| meeting_history | extension_evidence_ids |
| other_obligations | business_activities |
| other_obligations | operating_states |
| other_obligations | employee_count |
| other_obligations | tax_registrations |
| other_obligations | labour_registrations |
| other_obligations | sector_licences |
| filing_history | prior_filings |
| filing_history | outstanding_notices |
