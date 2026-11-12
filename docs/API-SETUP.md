# API keys and integration status

No external API key is included or has been created. Account registration, KYC, commercial entitlements and any charges belong to the provider and the account holder. The backend runs locally without an AI key or company-data provider.

The official Ministry of Corporate Affairs domain is https://www.mca.gov.in/. The original requested mca.org is a different organization. Treat the archived source register as research pointers, not proof of current filing entitlements.

## What works now

| Route | Implementation | Verification |
|---|---|---|
| Local backend API | Local bootstrap creates role tokens for this application | Real HTTP journey and authenticated API tests |
| Manual company facts / uploaded evidence | Available without an external provider | All 60 fields round-trip with provenance |
| Sandbox company lookup | Implemented vendor HTTP adapter, disabled until configured | Mocked HTTP contract/error tests; live test skipped |
| OpenRouter explanations | Optional provider adapter; company consent required | Mocked schema/citation/consent tests; live model not called |
| API Setu / OGD / Cashfree | Capability and onboarding entries only | No invented read or submit endpoints; unsupported lookup returns 501 |
| MCA submission | Authorized user/professional handoff | Submit API returns 501; receipts tracked locally |
| eSign / GST | Future integration requirements recorded | No active adapter |

## Sandbox company-data key

1. Use [Sandbox Console](https://console.sandbox.co.in) and follow its current organization onboarding and [key-generation guide](https://help.sandbox.co.in/portal/en/kb/articles/generate-your-api-keys).
2. Obtain a key and secret for the MCA company-data product and the intended test environment. A key alone does not prove product entitlement.
3. Set SANDBOX_API_KEY, SANDBOX_API_SECRET, SANDBOX_ENV=test and ENABLE_EXTERNAL_PROVIDERS=true in the server's environment. Never place these in the frontend, source archive or a chat message.
4. Restart the backend. POST /api/companies/{company_id}/lookup with {"provider":"sandbox"}.
5. Inspect returned provenance, environment, data_as_of and candidate IDs. Explicitly confirm accepted facts. Null data_as_of means the vendor response did not establish freshness.

Contract implemented from [Sandbox quickstart](https://developer.sandbox.co.in/guides/get-started/quickstart) and [Company Master Data](https://developer.sandbox.co.in/api-reference/kyc/mca/company_master_data):

~~~http
POST https://test-api.sandbox.co.in/authenticate
x-api-key: YOUR_KEY
x-api-secret: YOUR_SECRET
x-api-version: 1.0.0
~~~

Then:

~~~http
POST https://test-api.sandbox.co.in/kyc/mca/company/master-data
x-api-key: YOUR_KEY
Authorization: ACCESS_TOKEN
Content-Type: application/json
x-accept-cache: false

{"cin":"YOUR_AUTHORIZED_CIN"}
~~~

This vendor's documented token header uses the raw access token, without a Bearer prefix. The local backend and OpenRouter separately use Bearer authentication. Sandbox test and production hosts are distinct. A successful company lookup does not authorize filing.

The adapter accepts either one data object or a one-item list because the vendor documentation shows inconsistent envelopes. It verifies the returned CIN and imports only recognized fields; it does not assume director lookup still exists. Invalid mappings become explicit errors, never silently confirmed facts.

### Opt-in live check

After setting the provider credentials in your environment:

~~~powershell
$env:ENABLE_EXTERNAL_PROVIDERS = "true"
$env:SANDBOX_ENV = "test"
$env:ALLOW_LIVE_TESTS = "true"
$env:LIVE_TEST_CIN = "YOUR_AUTHORIZED_TEST_CIN"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
.\.venv\Scripts\python.exe -m pytest -q -m live
~~~

Use an identifier the vendor supports in its test environment. This can consume your account's quota; production may be billable. The test fails clearly if opted in without required settings. Passing it demonstrates that lookup contract only, not submission or whole-product readiness.

## Official government data options

| Service | How access is obtained | What remains before adding it |
|---|---|---|
| API Setu | Organization onboarding through [API Setu](https://partners.apisetu.gov.in/), followed by publisher approval for a particular API | Obtain actual endpoint/schema, credentials, purpose restrictions and sandbox access; add a dedicated adapter and live acceptance test |
| Open Government Data | Register and use the API-key facility described in [OGD help](https://data.gov.in/help); locate a current [Company Master Data](https://data.gov.in/catalog/company-master-data) resource | Verify resource ID, schema, refresh date, limits and current availability; reference data is not a live filing API |
| MCA portal | Use the authorized company's/professional's account and the current form instructions | No universal public submission API/key has been verified for this project; keep the portal handoff |

An official-domain source or API listing alone is not an entitlement. Do not copy an undocumented browser session endpoint into a server integration. The practical fallback implemented here is manual input plus uploaded records, reviewed worksheets, portal filing and receipt tracking.

## Optional AI key

Create an account-owned key at [OpenRouter keys](https://openrouter.ai/keys), choose an explicit model ID and review its current provider handling terms. Set OPENROUTER_API_KEY and OPENROUTER_MODEL on the server.

The application requires both external opt-in and a company consent record:

~~~json
{"purpose":"ai_explanation","allowed":true,"version":"your-policy-version"}
~~~

POST this to /api/companies/{company_id}/consents as owner. Then call /api/obligations/{obligation_id}/explain with use_ai=true.

The adapter uses [chat completions](https://openrouter.ai/docs/api-reference/chat-completion) and [provider routing](https://openrouter.ai/docs/features/provider-routing) with data_collection=deny. The model must support the requested response format and routing settings. This is a routing request, not independent proof of every downstream privacy obligation.

Only evaluated status, missing field names, rule interpretation, selected legal passages and the user's question are sent by the application. The question itself may contain personal information, so consent and careful input remain necessary. Private evidence blobs and the complete company profile are not automatically sent. AI output is labeled unverified_ai_explanation, has no execution tools and cannot publish rules, change facts, sign, pay or file. Citation membership validation does not prove every sentence is legally correct.

No AI is necessary for the questionnaire, deterministic evaluation, worksheets, review or filing ledger.
