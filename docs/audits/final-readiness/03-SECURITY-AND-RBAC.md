# Security and RBAC

Scope: static execution-path review plus JWT/encryption unit checks. No live authenticated service, penetration test, production identities or production database were used. Database-backed permission behavior is **NOT VERIFIED**.

## Controls present and supported by evidence

* `backend/app/core/security.py:31–65`: signed HS256 tokens, expiry, issuer and audience validation. Portal tokens use a distinct issuer/audience (`:18–19`, `:69–115`). Token/encryption tests: 49 passed; two timezone fixture errors on Windows, not authentication bypasses.
* `backend/app/api/deps.py:14–40`: resolves the user from the database on each authenticated request; rejects absent/inactive/expired accounts. A token role alone does not establish the current account's access.
* `backend/app/api/v1/auth.py:61–76` and `frontend/src/api/client.ts:42–89`: current UI uses an HttpOnly, SameSite=Lax cookie and same-origin requests. Cookie Secure depends on detected HTTPS. Repository instructions claiming JWT storage in sessionStorage are stale; this report follows implementation.
* `backend/app/services/permission_service.py:204–260`: app/card stakeholder permissions and archived-role exclusion; `services/card_read_scope.py:115–210`: role/type allow/deny plus stakeholder exceptions and SQL scope. Module scope deliberately differs from inventory scope. This is an implemented policy, not missing RBAC.
* Executive API `api/v1/executive_dashboard.py:55–65` requires `reports.executive_dashboard` and independently checks `costs.view`; overview record lists check module read permissions (`executive_overview.py:88–127`). Aggregates and record access are deliberately distinct.
* Card chain approval checks current step, approver permission and submitter independence (`api/v1/cards.py:3181–3208`, bulk counterpart `:3347–3415`). Governance mode/SoD are settings; confirm their deployed values.
* Financial-benefit actual confirmation/rejection/reversal explicitly checks independence (`services/benefits.py:737–750,886,929,961`). The gaps in FR-03 do not mean that independence is absent throughout the application; these benefit checks were inspected but not executed with database-backed records.
* Attachments enforce read/manage permissions, card readability and validated size/content (`api/v1/file_attachments.py:59–112`, `:121–155`, `:301`); bytes are stored in PostgreSQL (`models/file_attachment.py:14–27`). This is positive source evidence, not an executed upload-security test.
* `services/audit_log.py:145–208` redacts sensitive keys and credentials in URLs; security/admin audit and mutation history exist. Retention is implemented, so configure it rather than assuming indefinite evidence preservation.

## FR-01 — Local LLM suggestions still transmit card names to public search

**Category:** isolation/data disclosure. **Severity:** P1 when enabled for sensitive data with public egress; otherwise configuration-dependent risk. **Confidence:** Confirmed execution path; active disclosure NOT VERIFIED.

**Sources:** `backend/app/api/v1/ai_suggest.py:75–98,106–122`; `backend/app/services/ai_service.py:94–101,185–202,1136–1152`; `backend/app/services/turbolens_ai.py:191–235` for separate configured remote model paths.

**Evidence/path:** enabled, authorized suggestion request passes `body.name` to `suggest_metadata`; it constructs a name-based query and explicitly invokes `web_search(query, "duckduckgo")`; the search client GETs public DuckDuckGo with that query. Choosing Ollama does not change this search path. Expected for local-only deployment: no card name leaves approved infrastructure. Actual: a public query is attempted before model inference.

**Impact/scope:** sensitive system names can leave the authority; affects pilot if suggestions are enabled. Cloud model/TurboLens configuration can separately transmit richer prompts. Not evidence that the feature is enabled here.

**Minimum correction:** pilot: disable description suggestions, cloud AI and portfolio/TurboLens AI, remove unneeded grants and deny outbound traffic at the network boundary. If local suggestions are required later, make external search explicitly opt-in and support no-search/internal-search inference.

**Validation:** enabled local-model request with a synthetic name and mocked HTTP must make no public call in the intended offline mode; capture outbound traffic during pilot smoke tests. No external suggestion was executed during review.

## FR-02 — ARB detail bypasses linked-module read gates

**Category:** authorization. **Severity:** P2; elevate operationally if linked titles themselves are classified. **Confidence:** Confirmed statically; live role replay NOT VERIFIED.

**Sources:** `backend/app/api/v1/arb.py:149–249` (detail handler; `arb.view` at `:155`), contrasted with `api/v1/executive_overview.py:88–127`.

**Evidence/path:** an `arb.view` caller with a readable subject receives linked risks (reference/title/level/status), ADR titles/status and standard exception details via direct queries. There are no `risks.view`, `adr.view` or `tech_standards.view` checks on these context blocks. Readability of the subject does not establish those module rights or readability of all other linked cards. Expected: linked details honor their own module boundaries or an explicit approved alternative policy. Actual: ARB read access implicitly reveals them.

**Impact/scope:** pilot affected only when ARB readers are intentionally denied linked modules. Minimum workaround: restrict ARB to the same trusted group allowed those details; otherwise disable that workflow. Before wider grants, gate/redact each context block and reuse scoped module loaders.

**Validation:** create a readable subject, a linked risk/ADR/exception and a custom role with only `arb.view`; direct API response must omit restricted records while an authorized reader still sees them. Add denied-secondary-card cases. Existing executive gates do not cover this endpoint.

## FR-03 — Approval independence is not uniform across governance instruments

**Category:** segregation of duties. **Severity:** P2. **Confidence:** Confirmed code policy gap; exploit replay NOT VERIFIED.

**Sources:** `backend/app/api/v1/tech_standards.py:583–603`; `services/governance_transitions.py:215–260`; `api/v1/arb.py:276–327`; `api/v1/nora_program.py:571–595`.

**Evidence/path:** exception decisions check `approve_exception` but not requester inequality; ARB update with `arb.manage` can stamp the creator as reviewer; NORA deliverable approval requires `nora.manage` and `governance.approve_step` but does not reject its owner. By contrast card chain approval checks submitter inequality. A user holding both capabilities can approve their own work in these paths. Permission to approve is present; actor independence is incomplete.

**Expected/impact:** official independently approved governance records should reject self-approval. Actual semantics are permission-only in these paths. Not a blocker for working inventory; unsuitable as sole independent approval evidence. Admin wildcard remains privileged and should be operationally controlled.

**Minimum correction:** pilot: separate people/grants and keep affected records provisional/manual committee evidence; do not treat these paths as enforcing independence. Wider rollout or formal digital approvals: add actor/owner/requester checks per instrument and tests, preserving existing RBAC.

**Validation:** same person with both grants gets refusal; distinct eligible reviewer succeeds; exceptions remediation verification continues to reject requester/submitter; card-chain regression tests remain green.

## FR-08 — Card-type visibility is not department/workspace isolation

**Category:** access-model boundary. **Severity:** P2, wider-rollout requirement dependent. **Confidence:** Confirmed inspected model/scope; authority policy requirement Unverified.

**Sources:** `backend/app/services/card_read_scope.py:94–210`; `backend/app/models/card.py:19–90`; `backend/app/models/user.py:136–144` (identity/role model); `services/permission_service.py:204–260`.

**Evidence/path:** scope derives role, type overrides and stakeholder card IDs. It does not add a department or workspace predicate. Cards do not carry a mandatory authorization tenant key in the inspected model. Organization relationships and segment report filters are not enforcement boundaries. Expected, if departments must be isolated: every relevant read/export/report must enforce an approved boundary. Actual: global permissions intentionally span the shared repository unless explicit narrower controls apply.

**Impact:** trusted single EA-team pilot can share that boundary; do not onboard departments assuming their cards are private. **No redesign recommendation is justified without an actual isolation requirement.** Minimum action: document one shared workspace, approve role/type/stakeholder grants and prohibit sensitive departmental segregation use until tested/specified.

**Validation:** agreed access matrix covering two departments, search, reports, attachments, exports and direct IDs. If policy demands department-private data of the same type, existing type filters alone cannot satisfy it.

## Remaining security assumptions

Logout clears the cookie (`auth.py:1193–1209`); a copied bearer token has no per-session revocation check in `deps.py:14–40` and remains valid to expiry unless the account becomes inactive/expired. Set an approved lifetime; do not promise immediate individual-token revocation. Default token duration is 1440 minutes (`config.py:141`). This is a known session model, not proof of account-deactivation failure.

HTTPS/proxy trust, password/SSO settings, local registration closure (default registration remains enabled after bootstrap unless configured, `auth.py:384–405`), public portal/diagram publishing, ops access, CORS, rate limiting under the real proxy, XSS/CSRF resistance and secret rotation were not exercised. Configure before sensitive use. Internal employee access reduces exposure but does not replace backend authorization.
