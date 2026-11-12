# API operations

Base URL: http://127.0.0.1:8000. JSON request bodies use Content-Type: application/json. All /api operations require Authorization: Bearer YOUR_LOCAL_ROLE_TOKEN. Tenant and company access checks apply in addition to role checks.

| Method | Path | Request schema | Write-role restriction |
|---|---|---|---|
| GET | /api/me | No JSON model | Authenticated and authorized |
| GET | /api/catalog | No JSON model | Authenticated and authorized |
| GET | /api/integrations | No JSON model | Authenticated and authorized |
| POST | /api/companies | CompanyCreate | owner |
| GET | /api/companies | No JSON model | Authenticated and authorized |
| POST | /api/companies/{company_id}/grants | Grant | owner |
| DELETE | /api/companies/{company_id}/grants/{principal_id} | No JSON model | owner |
| GET | /api/companies/{company_id} | No JSON model | Authenticated and authorized |
| GET | /api/companies/{company_id}/structure | No JSON model | Authenticated and authorized |
| POST | /api/companies/{company_id}/facts | FactInput | owner, operator, professional |
| GET | /api/companies/{company_id}/facts | No JSON model | Authenticated and authorized |
| POST | /api/companies/{company_id}/facts/confirm | FactConfirm | owner, operator, professional |
| POST | /api/companies/{company_id}/evidence | EvidenceInput | owner, operator, professional |
| GET | /api/companies/{company_id}/evidence | No JSON model | Authenticated and authorized |
| GET | /api/evidence/{evidence_id}/download | No JSON model | Authenticated and authorized |
| PUT | /api/evidence/{evidence_id}/retention | Retention | owner |
| DELETE | /api/evidence/{evidence_id} | No JSON model | owner |
| POST | /api/companies/{company_id}/consents | Consent | owner |
| GET | /api/companies/{company_id}/questionnaire/{workflow} | No JSON model | Authenticated and authorized |
| POST | /api/companies/{company_id}/questionnaire/{workflow}/answers | QuestionnaireAnswer | owner, operator, professional |
| POST | /api/companies/{company_id}/evaluate | EvaluationRequest | owner, operator, professional |
| GET | /api/companies/{company_id}/obligations | No JSON model | Authenticated and authorized |
| POST | /api/companies/{company_id}/lookup | Lookup | owner, operator, professional |
| GET | /api/companies/{company_id}/audit | No JSON model | Authenticated and authorized |
| GET | /api/companies/{company_id}/export | No JSON model | Authenticated and authorized |
| GET | /api/sources | No JSON model | Authenticated and authorized |
| POST | /api/sources/snapshots | SourceSnapshot | owner, content_reviewer |
| POST | /api/sources/snapshots/{snapshot_id}/verify | SourceVerification | content_reviewer |
| GET | /api/sources/changes | No JSON model | Authenticated and authorized |
| POST | /api/sources/{source_id}/check | No JSON model | owner, content_reviewer |
| POST | /api/rules | RuleInput | owner, content_reviewer |
| GET | /api/rules | No JSON model | Authenticated and authorized |
| POST | /api/rule-releases/{rule_id}/approve | RuleApproval | content_reviewer |
| POST | /api/rule-releases/{rule_id}/retire | SourceVerification | content_reviewer |
| POST | /api/templates | TemplateInput | owner, content_reviewer |
| GET | /api/templates | No JSON model | Authenticated and authorized |
| POST | /api/templates/{template_id}/approve | TemplateApproval | content_reviewer |
| GET | /api/obligations/{obligation_id} | No JSON model | Authenticated and authorized |
| POST | /api/obligations/{obligation_id}/document-packs | PackRequest | owner, operator, professional |
| GET | /api/document-packs/{pack_id} | No JSON model | Authenticated and authorized |
| GET | /api/document-packs/{pack_id}/download | No JSON model | Authenticated and authorized |
| POST | /api/document-packs/{pack_id}/reviews | Review | professional |
| POST | /api/filing-attempts | FilingCreate | owner, operator, professional |
| GET | /api/filing-attempts/{filing_id} | No JSON model | Authenticated and authorized |
| POST | /api/filing-attempts/{filing_id}/evidence | FilingObservation | owner, operator, professional |
| POST | /api/filing-attempts/{filing_id}/submit | No JSON model | owner, operator, professional |
| GET | /api/filing-attempts/{filing_id}/handoff | No JSON model | Authenticated and authorized |
| POST | /api/obligations/{obligation_id}/explain | Ask | Authenticated and authorized |

Public routes: GET /health and GET /openapi.json.

Successful creates generally return 201; reads/evaluations return 200. Errors include 401 authentication, 403 role, 404 inaccessible/missing record, 409 state or confirmation conflict, 413 body limit, 415 media type, 422 validation, 429 local rate limit, 501 unimplemented provider/submission and 503 external provider unavailable.

Relevant company reads/questionnaires accept ?as_of=YYYY-MM-DD. Evaluation uses an explicit as_of request body. Use the same as_of date throughout a historical workflow. ISO dates are calendar dates, not filing-time-zone conversions.

OpenAPI includes request schemas, references and operation IDs. Responses are currently described rather than fully typed; consult tests and docs/http-smoke-results.json for exercised responses.
