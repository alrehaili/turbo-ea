# Minimum remediation and deployment acceptance

Goal: begin practical EA work safely, not complete every optional feature. Findings are defined once in reports 03/04/06/08. This plan references those IDs.

## Mandatory before the controlled EA pilot

| Gate | Minimum work | Acceptance criteria |
| --- | --- | --- |
| 1. Native staging service | Operations: run one supervised backend process, internal PostgreSQL, built SPA and local DrawIO through HTTPS; fixed working directory and protected process secrets. Disable reset/demo flags. FR-09. | Restart succeeds, intended schema at one head, login and deep-link refresh work, BPMN/DrawIO reopen; backend not directly reachable around proxy. No Docker requirement. |
| 2. Identity and least-privilege check | Administrator/EA owner: close unwanted registration after bootstrap, configure approved local/IdP accounts and token duration; set role/type/stakeholder rules. Enable governance mode/SoD/promotion approval where those claims are needed. FR-08/FR-09. | Author, independent reviewer and reader complete permitted work; reader direct mutation gets 403; inactive user rejected; hidden-card search/detail/export/attachment and costs-denied executive payload expose no forbidden content. Use disposable synthetic records. |
| 3. Internal isolation | Operations: deny all unapproved server/browser egress; disable description/cloud/portfolio/TurboLens AI, auto-model pull, update/store notices and unapproved integrations. FR-01. | Network-denied scenario finishes essential workflow; no public request carries card names/context; optional offline failures do not prevent inventory work. Local LLM setting alone is not acceptance. |
| 4. Recovery | DBA: schedule protected native PostgreSQL backups and required runtime files/secrets; restore once into an isolated instance. Set retention deliberately, including archive purge and audit/batch retention. FR-05/FR-09. | Restored cards, relations, successor link, review steps, attachment bytes and diagram reopen; restore duration and owner recorded. Workspace ZIP alone is explicitly not the recovery plan. |
| 5. Small functional/Arabic acceptance | Two EA staff run report 05 scenario with one Arabic-first user; reconcile one known executive example if dashboard is enabled. | Create/edit/link/find/export records, save/reopen process/diagram, evidence round-trip and independent card review work; invalid input has useful feedback; Arabic names/numbers/forms are usable. Mark untested optional workflows out of scope. |

These are acceptance/configuration tasks; successful results can allow pilot use without application changes. If a gate fails, correct that concrete defect before official data. No claim that a gate has already passed is made here.

Pilot restrictions replacing immediate code work:

* FR-02: ARB users must be the same trusted group allowed its linked risk/ADR/standards context. If that cannot be guaranteed, do not enable the ARB workflow until the context gates are corrected.
* FR-03/FR-04: affected exception/ARB/NORA approvals remain provisional working records, with independent committee signoff retained separately. Use the implemented card chain for digital card approval; do not represent every module as independently enforced.
* FR-05: do not use workspace transfer for official repository migration/recovery until successor/step fidelity is corrected. Native DB recovery is the workaround.
* FR-06: plateau output is a lifecycle projection from current data; preserve baseline exports for historical evidence.
* FR-07: reconcile the stale savings test before claiming clean validation or publishing savings as an accepted indicator. It need not delay inventory-only work.

If the pilot specifically requires restricted-module ARB readership or authoritative exception/NORA digital approvals, FR-02–FR-04 corrections become **mandatory before that pilot use**, not deferred tasks. Otherwise their documented exclusion is the smallest safe scope.

## Before authority-wide production

| Item | Required correction or decision | Acceptance |
| --- | --- | --- |
| Module confidentiality | Correct FR-02 context gates and test role combinations | Direct API denial/redaction matches intended module and card rights |
| Official digital governance | Correct FR-03 actor independence and FR-04 evidence invalidation | Same-person approval refused; independent eligible reviewer succeeds; substantive approved edits require re-review |
| Sharing policy | Resolve FR-08 against written authority confidentiality requirements | Explicit EA-shared repository accepted, or required department/object boundaries implemented and tested across every read/export surface |
| Transfer, if used | Correct FR-05 serialization/remapping | Two-instance successor/review-step round-trip and repeat-import no-op pass |
| Published reporting | Resolve FR-07 and known-data reconcile all adopted KPIs, fiscal periods/currency and approved/verified semantics; FR-06 labels accepted | EA/business owners sign off definitions and source drill-down; historical-unavailable stays unavailable, not zero/current substitution |
| Production operations | Complete FR-09 upgrade/restore, logs/job monitoring, load/capacity, retention and support ownership | Documented RPO/RTO, measured representative concurrency, successful supervised restart/upgrade/recovery; no unsupported multi-worker assumptions |
| Security and usability validation | Focused DB/API tests, browser/Arabic/accessibility checks and approved dependency inventory | No unresolved relevant P0/P1; real role matrix and offline traffic checks pass; material accessibility/task-completion failures corrected |

This list is adoption-dependent. Do not build department tenancy if the authority approves a shared EA repository; do not build historical snapshots if retained baseline evidence meets the need.

## Optional, postponable improvements

* Backport upstream `f1b951c8` (#1324) if MCP requires extra proxy Host names. Otherwise leave MCP disabled.
* Offline documentation/Swagger mirroring, better projection wording, task guides and targeted field grouping discovered during pilot.
* Advanced rationalization/benefits, broad executive publication, external integrations, AI and HA scaling after separate acceptance. None is necessary merely to register and govern architecture inventory.
* Make Unix-only timezone tests portable (or run them on the chosen Linux validation host). Do not weaken UTC handling because Windows lacks `time.tzset`.

## Release decision rule

EA owner + operations owner record the five pilot gates, exact build/config and excluded workflows. If they pass, **GO for the controlled EA pilot**. The current audit recommendation remains **CONDITIONAL GO** because those results are unavailable. Authority-wide use remains **NO-GO on present evidence**, not a demand for indefinite development.

Minimum confirmed P0/P1 position: no unconditional P0/P1 demonstrated; FR-01 is serious when sensitive suggestions can reach public search and is avoided by disabling the feature and denying unapproved egress. The remaining mandatory work is mainly acceptance and configuration, with narrow corrections only where affected optional boundaries are actually needed.
