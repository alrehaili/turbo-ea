# NORA Readiness Tracker

Readiness of Turbo EA for a Saudi government entity that follows the Digital Government Authority (DGA) and implements the National Enterprise Architecture (NORA).

- **Assessed:** 15 Nov 2026, on the live instance (v2.48.2, NORA demo data) and the `main` branch.
- **How to use:** each row is one piece of work. Update **% Done** and **Status** as you go. The section and overall scores are the average of their rows' % Done.
- **Status values:** `Open` · `In progress` · `Done` · `Verify` (needs a manual check before it can be scored) · `Won't fix` · `Deferred` (set aside for now).
- **Scoring:** rows marked `Won't fix` or `Deferred` are left out of the in-scope score.

## Official baselines

Every alignment finding is measured against these documents.

| Ref | Document | Issue / date | Where it is |
|---|---|---|---|
| B1 | الدليل الاسترشادي لتطوير النموذج العام لمكونات البنية المؤسسية (EA Content Meta Model guideline), **current baseline** for building blocks, attributes and relationships | Issue 1.0, June 2025 (Arabic) | `C:\Users\user\Downloads\Documents\` (not yet in the repo; see D1) |
| B2 | The EA Viewpoints Document | v2.0, Dec 2024 | `الحقيبة التوعوية - البنية المؤسسية الوطنية/الدليل الإسترشادي لتطبيق مناظير البنية المؤسسية/` |
| B3 | Training kit for the updated National EA methodology (7 phases, 6 domains) | Nov 2024 | `الحقيبة التوعوية - البنية المؤسسية الوطنية/الحقيبة التدريبية - المنهجية المحدثة/` |
| B4 | Guideline for National Overall Reference Architecture (NORA), DGA-1-2-1-212 (10 stages, PRM/BRM/ARM/DRM/TRM) | Issue 1.0, 2 Jan 2024 | [dga.gov.sa PDF](https://dga.gov.sa/sites/default/files/2024-03/Guideline%20for%20National%20Overall%20Reference%20Architecture%20(NORA)%20-%20V1.0.pdf) |
| B5 | Enterprise Architecture Establishment for Government Entities, DGA-1-2-1-211 (EA Office, **8-domain maturity model**, levels 0–5, accreditation at level 3+) | Issue 1.0, 28 Feb 2022 | [dga.gov.sa PDF](https://dga.gov.sa/sites/default/files/2022-11/Enterprise%20Architecture%20Establishment%20for%20Government%20Entities%20-%20V1.0.pdf) |
| B6 | Data collection templates (حصر البيانات), one per domain | — | `الحقيبة التوعوية - البنية المؤسسية الوطنية/قوالب استرشادية/` |

## Scorecard

| Section | In scope | Readiness |
|---|---:|---:|
| A. Methodology & viewpoints | 5 of 5 | 94% |
| B. Metamodel alignment (B1) | 10 of 10 | 66% |
| C. Maturity model (B5) | 3 of 3 | 87% |
| D. Live instance defects | 8 of 8 | 58% |
| E. Localisation (Saudi context) | 3 of 4 | 93% |
| F. Security & compliance | 0 of 7 | Deferred |
| G. Operations & scale | 0 of 3 | Deferred |
| H. Procurement & source documents | 1 of 5 | 100% |
| **Overall (in scope)** | **30 of 45** | **74%** |
| Overall (all 45 rows) | 45 | 57% |

> Update the section figures whenever a row's % Done changes. In-scope overall = average of the rows not marked `Won't fix` or `Deferred`.

---

## A. Methodology & viewpoints

| ID | Finding | Evidence | Fix | Priority | Effort | % Done | Status |
|---|---|---|---|---|---|---:|---|
| A1 | The 10-stage NORA method (B4) is implemented: the stages, continuous governance and their deliverables | `backend/app/services/nora_program.py` (v1 catalogue) | None. Keep it for entities still on the 2024 method | — | — | 100% | Done |
| A2 | The updated 7-phase / 6-domain method (B3) is implemented: 44 deliverables, with phases 2 and 4 run per domain | `nora_program.py` (v2 catalogue); live `/nora-program` | Check the phase and deliverable names against B3 line by line. If DGA publishes the newer methodology guideline (reported as DGA-1-2-5-230, Mar 2026), reconcile with it | Medium | S | 90% | Verify |
| A3 | View Library has all 67 core viewpoints of B2 | live `/view-library` shows 67/67 | None | — | — | 100% | Done |
| A4 | The NEA Viewpoints Dashboard contradicts B2. Its text says "47", a tile says "92" and the library says 67. It shows "0 methodology phases", domain chips use raw keys (`beneficiaryExperience`), and the page stays on "Loading viewpoints…" | live `/reports/nea-viewpoints`; `frontend/src/i18n/locales/en/reports.json:1463,1851,1870` | **v2.49.0:** the old address now redirects to the View Library (`/view-library`, 67 core viewpoints); the broken page and its strings were removed | **High** | S | 100% | Done |
| A5 | DGA data collection templates (B6) can be imported per domain | live: "Import DGA templates" on Phase 2 deliverables | Import each of the six B6 templates into a test workspace and confirm every column lands on a field | Medium | S | 80% | Verify |

## B. Metamodel alignment with the June 2025 guideline (B1)

B1 defines **45 building blocks in 7 domains**: Strategic Alignment 7, Business 12, Beneficiary Experience 5, Data 3, Applications 4, Technology 11, Security 3. Each block is defined **once, in exactly one domain**, and fixed values are predefined lists.

| ID | Finding | Evidence | Fix | Priority | Effort | % Done | Status |
|---|---|---|---|---|---|---:|---|
| B-1 | All 45 B1 building blocks exist as card types, including the new **Activity (نشاط)** | `backend/app/services/seed.py` `TYPES`; NORA profile v16 | None | — | — | 100% | Done |
| B-2 | **Service sits in the wrong domain.** B1 puts Service (خدمة) in Business, and its Beneficiary Experience relationship table says "Beneficiary benefits from Service (Business)". The app files Government Service under Beneficiary Experience | `nora_profile.py` (`GovService` category); live layers overview | **v2.49.0:** NORA profile v17 moves Government Service to Business (once, only while it is still in Beneficiary Experience); fresh installs start there. Verify on the live instance after upgrade | **High** | M | 90% | Verify |
| B-3 | **Policy** has no attributes. B1 requires code, name, description, owner, type (internal / external-government), status (active / suspended / cancelled), effective date and document link | `seed.py` Policy has `fields_schema: []`; B1 §5.3.3.2.11 | **v2.49.0:** profile v17 adds policyCode, policyType, policyStatus, policyEffectiveDate, policyLink (EN + AR). The owner is the Responsible stakeholder role. Verify on the live instance | **High** | S | 90% | Verify |
| B-4 | **Beneficiary** type list differs. B1 lists internal, government entity, business sector and individuals. The app's subtypes are citizen / business / government, so **internal** is missing | `seed.py` Beneficiary subtypes; B1 §5.3.4.2.1 | Add an `internal` subtype and rename labels to match B1 (EN + AR) | Medium | S | 60% | Open |
| B-5 | **Data Vault** type list differs. B1 lists electronic database, digital archive and **paper archive**, plus a *structure* attribute. The app offers database / data lake / warehouse and has no fields | `seed.py` DataVault; B1 §5.3.6.2.2 | Add the B1 types (keep data lake and warehouse as extensions). Add code and structure fields | Medium | S | 20% | Open |
| B-6 | The other blocks have few or no attributes compared with B1: Vision, Mission, Pillar, Model/Template, Application Module, Application Function, Phase, Position, Data Attribute, Security Service (at least) | `seed.py` field counts; B1 §5.3.x.2 tables | **v2.49.0:** reviewed against B1 and the six DGA templates (Appendix B-6). Added the missing attributes for the security types, physical host, server, model/template, policy, data attribute, infrastructure service and integration point; landed 15 fields that were defined but never reached an install (service, pillar, persona, policy); the template importer writes technology/security rows to the NORA types and now also imports the policy, model/template and data-attribute sheets. **Open:** the journey-improvement sheet (no visible NORA type), the strategic and other types not yet compared with B1, and a TRM code on the native technology types | **High** | L | 80% | In progress |
| B-7 | Relationships have not been compared with B1's relationship table for each domain | B1 §5.3.x.3 (one table per domain); app has 206 relation types | Build a crosswalk of B1 relationship → app relation type key (direction and verb). Add missing relations through a migration. Respect `.claude/rules/relations.md` | **High** | L | 0% | Open |
| B-8 | **"Defined once" is broken in the live data.** "Commission Enterprise" exists as both an Organizational Unit and an Organization. Hidden legacy types (`Organization`, `BeneficiaryPersona`) still hold cards and show under "Uncategorized" | live card relations panel; `NORA_HIDDEN_TYPE_KEYS` | **v2.49.0:** the CST kit and the `SEED_NORA` demo use Organizational Units and Personas (the demo's 6 organizations, the fill seeders' 5 personas; their relations moved to native types). The Org Chart, strategy-cascade owner and portfolio org filter read Organizational Units; the NORA presets were retargeted (existing untouched ones too). Guard: `tests/services/test_nora_seed_building_blocks.py`. **Left:** reset the live database (the NORA demo reseeds with Units/Personas); import the CSTD kit again only if wanted. The demo's IT Component cards stay until the native tech types carry TRM fields (see B-6) | **High** | M | 90% | Verify |
| B-9 | B1 asks for fixed values (currency, date/time format, priorities) as predefined lists | B1 §5.2 | Audit free-text fields that should be lists. Currency is already a setting (see E2). Add a date-format setting (see E3) | Low | M | 50% | Open |
| B-10 | Extra types beyond B1 (Channel, Data Exchange, Security Control) | `nora_profile.py` | B1 allows entity-specific blocks. Label them "extension" in the metamodel admin and docs so reviewers can tell them from B1 blocks | Low | S | 80% | Open |

## C. EA maturity model (B5)

| ID | Finding | Evidence | Fix | Priority | Effort | % Done | Status |
|---|---|---|---|---|---|---:|---|
| C1 | The app's seeded maturity dimensions are its own 10 "Qiyas-style" ones, **not DGA's 8 domains**. B5's domains: Strategic Alignment · Corporate Management Support · EA Framework & Deliverables · EA Governance & Management · EA Capability · Architecture Content · EA Role in Digital Transformation · Value Realization (each with its own criteria) | `backend/app/services/maturity.py:27`; B5 §4.5 Table 4 | **v2.49.0:** the 8 DGA domains are the built-in dimensions, with criteria as descriptions and evidence-based suggestions; the 10 legacy dimensions are switched off once (history kept). Verify on the live instance | **High** | M | 90% | Verify |
| C2 | Level labels and accreditation threshold. B5 uses levels 0–5: Initial, Under Development, Functioning, Managed, Optimized. **Level 3 or above earns DGA accreditation** | B5 Figure 8; `backend/app/models/maturity.py` (1–5, 0 = not assessed) | **v2.49.0:** DGA level names (EN + AR) and an accreditation reading (average level, reached at ≥ 3) on the Overall score tile. Have an Arabic speaker confirm the official Arabic level and domain names | Medium | S | 90% | Verify |
| C3 | The live maturity page shows **0** on the Dimensions tile. That tile counts the dimensions in the latest assessment, and there is none yet — so the catalogue itself may not be empty | live `/maturity` | **v2.49.0:** profile v17 seeds the DGA domains on upgrade. After deploying, open Manage dimensions to confirm the 8 domains, then run a first assessment | **High** | S | 80% | Verify |

## D. Live instance defects

| ID | Finding | Evidence | Fix | Priority | Effort | % Done | Status |
|---|---|---|---|---|---|---:|---|
| D1 | Viewpoint dashboard counts are wrong | live `/reports/nea-viewpoints` | Same as A4 (done in v2.49.0) | **High** | — | 100% | Done |
| D2 | Maturity page is empty | live `/maturity` | Same as C3 | **High** | — | 80% | Verify |
| D3 | Costs display in USD ("Service Fee $0") | live card; `settings.py` `DEFAULT_CURRENCY = "USD"` | **v2.49.0:** a NORA install with no currency chosen switches to SAR on upgrade. Verify on the live instance (or set it in Admin → Settings) | **High** | XS | 90% | Verify |
| D4 | Hidden types show under "Uncategorized" | live card relations panel | Same as B-8: reset the live database | **High** | — | 90% | Verify |
| D5 | The governance workflow isn't exercised in the demo data: every card is Draft, approvals are at 0%, and KPIs and initiatives have no targets, owners or status reports. Executive and NORA dashboards are almost empty | live Executive dashboard and `/nora-program` | Extend the NORA demo seed with one completed approval cycle: approved cards, ratified KPI targets with measurements, initiative status reports, a signed ARB decision and at least one Phase 2 deliverable marked done | Medium | M | 0% | Open |
| D6 | After switching the UI to Arabic, the browser tab stopped responding to navigation, and a new tab kept redirecting off-domain | Chrome session, 15 Nov 2026 | Reproduce by hand (could be the browser extension rather than the app). If it reproduces, check the locale-switch reload and the auth redirect | Medium | S | 0% | Verify |
| D7 | Clicking an item in the Governance menu once failed to navigate | Chrome session | Reproduce by hand. If it reproduces, fix and add a test | Low | XS | 0% | Verify |
| D8 | Arabic RTL works, including translated card content | live card in Arabic | None | — | — | 100% | Done |

## E. Localisation (Saudi context)

| ID | Finding | Evidence | Fix | Priority | Effort | % Done | Status |
|---|---|---|---|---|---|---:|---|
| E1 | UI and card content are in Arabic and English, with RTL | live; `frontend/src/i18n/index.ts` | Keep `check_locales.py` clean on every change | — | — | 100% | Done |
| E2 | Currency defaults to USD | `settings.py:103` | Same as D3 (done in v2.49.0) | **High** | XS | 90% | Verify |
| E3 | No Hijri date display | no Hijri / Umm al-Qura code in frontend | Not needed: the entity does not use Hijri dates (owner decision, 15 Nov 2026) | Medium | M | 0% | Won't fix |
| E4 | Some NORA screens still show raw keys (e.g. viewpoint domain chips) | live `/reports/nea-viewpoints` | Sweep NORA pages for untranslated keys. Fix through `useTypeLabel` and the other label resolvers | Medium | S | 90% | Open |

## F. Security & compliance (NCA ECC, PDPL, NDMO)

| ID | Finding | Evidence | Fix | Priority | Effort | % Done | Status |
|---|---|---|---|---|---|---:|---|
| F1 | Local login has no MFA. NCA ECC requires MFA for privileged and remote access | no MFA/TOTP code in `backend/app/api/v1/auth.py` | Option 1: enforce SSO-only (Entra ID / ADFS over OIDC) with MFA at the identity provider, and disable local login. Option 2: add TOTP for local admins | **High** | M | 30% | Deferred |
| F2 | SSO supports Microsoft, Google, Okta and generic OIDC, but not SAML | `settings.py:2033` | ADFS 2016+ supports OIDC, so document an ADFS/OIDC setup. Add SAML only if a customer requires it | Low | M | 80% | Deferred |
| F3 | The EA repository is effectively a map of the entity's attack surface | — | Classify the instance at NDMO "Restricted" or higher. Restrict who can export. Document this in a deployment guide | **High** | S | 20% | Deferred |
| F4 | No security evidence pack for procurement: no penetration test report, SBOM or SDLC evidence | — | Commission a third-party pen test. Generate an SBOM (CycloneDX) per release. Write an SDLC/secure-coding summary | **High** | L | 0% | Deferred |
| F5 | GitHub Actions is disabled on the fork, so there are no automated test or mutation results | project memory; `.github/workflows/` | Re-enable CI (or a self-hosted runner) so every release has test evidence | **High** | M | 0% | Deferred |
| F6 | PDPL: user personal data handling and the retention policy aren't documented | — | Write a short data-protection statement: what PII is held, retention, and where data is hosted | Medium | S | 10% | Deferred |
| F7 | Audit log, field encryption, RBAC and per-card read scope are in place | `audit_log`, `encryption.py`, `CardReadScope` | Map these controls to NCA ECC clauses in the evidence pack | Medium | S | 70% | Deferred |

## G. Operations & scale

| ID | Finding | Evidence | Fix | Priority | Effort | % Done | Status |
|---|---|---|---|---|---|---:|---|
| G1 | Hosting must be on a CST-licensed cloud or a government data centre (DGA cloud-first policy, NCA CCC) | — | Write a reference deployment for a government cloud / on-prem (Helm or compose) with network diagram | **High** | M | 20% | Deferred |
| G2 | No documented backup, restore or disaster-recovery procedure, RPO or RTO | — | Write the backup/restore runbook (Postgres dumps, attachments), set RPO/RTO, and test one restore | **High** | M | 10% | Deferred |
| G3 | Backend runs as a single process with a 30-connection pool; capacity is unverified | `CLAUDE.md` (DB sessions rule) | Load-test with realistic concurrency (e.g. 100 users). Document sizing guidance | Medium | M | 30% | Deferred |

## H. Procurement & source documents

| ID | Finding | Evidence | Fix | Priority | Effort | % Done | Status |
|---|---|---|---|---|---|---:|---|
| H1 | The June 2025 meta model guideline (B1) isn't stored in the repo | file in `Downloads\Documents` | Copy it into `الحقيبة التوعوية - البنية المؤسسية الوطنية/الدليل الإسترشادي لبناء النموذج العام/` | Medium | XS | 0% | Deferred |
| H2 | B1, B2 and the Practice guideline carry "مسودة / Draft" in their filenames | filenames | Confirm with DGA (or the Raqmi platform) that these are the final issues, and record the confirmation here | Medium | S | 50% | Deferred |
| H3 | Licence is the Functional Source License 1.1 (converts to MIT later) | `LICENSE` | Owner decision (15 Nov 2026): FSL 1.1 permits use that does not compete commercially with the licensor, so an entity using it internally, not selling it, is covered; it converts to MIT after two years | **High** | S | 100% | Done |
| H4 | It's a fork of an open-source product: who supports it and who is accountable? | — | Define a support model (SLA, owner, upgrade path from upstream) for the Etimad procurement file | **High** | M | 0% | Deferred |
| H5 | Local-content (LCGPA) requirements may apply to the supplier | — | Check whether LCGPA local-content rules apply to the contract, and prepare the evidence | Medium | S | 0% | Deferred |

---

## Change log

| Date | Change |
|---|---|
| 15 Nov 2026 | First assessment: live walk-through, code review, and comparison with B1–B6 |
| 15 Nov 2026 | v2.49.0 (not yet deployed): A4/D1 done; B-2, B-3, C1, C2, C3/D2, D3/E2 implemented, awaiting a check on the live instance |
| 15 Nov 2026 | B-8/D4: CST sample re-typed to NORA building blocks; live re-import and the SEED_NORA demo remain |
| 15 Nov 2026 | B-8: org views read Organizational Units; SEED_NORA demo, fill seeders and presets use the NORA types; guard test added |
| 15 Nov 2026 | Owner decisions: no Hijri dates (E3 won't fix); F, G, H deferred; licence settled (H3); the live database will be reset instead of re-importing |
| 15 Nov 2026 | B-6: attribute review (appendix), missing fields added, lost fields landed, template importer moved to the NORA types |
| 15 Nov 2026 | B-6: Data Attribute fields; policy, model/template and data-attribute sheets imported |

## Appendix B-6 — building-block attributes vs B1 and the DGA templates

Reviewed 15 Nov 2026 against B1 (June 2025 Content Meta Model guideline) and the six data-collection templates in `NORA/`. "Template sheet" names the sheet that collects the block. Status is after v2.49.0.

| Block (app type) | Template sheet | Status | Notes |
|---|---|---|---|
| Service (`GovService`) | دليل الخدمات | ✅ Match | 7 fields that never reached installs now land (beneficiary type, channels, maturity, fee model, SLA, monthly volume, shared services). Owning department and related KPIs are relations, not imported yet |
| Business Process (`BusinessProcess`) | دليل الإجراءات | ✅ Match | Owning department and related processes are relations, not imported yet |
| Model/Template (`ModelTemplate`) | دليل النماذج | ✅ Match | Code, type, link; the sheet is imported with its service and procedure links |
| Policy (`Policy`) | دليل السياسات | ✅ Match | Code, type, status, effective date, link, scope, clauses; the sheet is imported with its service and procedure links. Owning department and related capability are not linked |
| Stakeholders | دليل أصحاب المصلحة | ⚪ Not imported | No emails in the template, so no user can be matched (documented descope) |
| Application (`Application`) | سجل التطبيقات | ✅ Match | |
| Technical Integration Interface (`Interface`) | نقاط الربط التقني | ✅ Match | Integration point number added |
| Data Entity (`DataObject`) | دليل قاموس البيانات | ✅ Match | |
| Data Attribute (`DataAttribute`) | سمات البيانات / فهرس الأعمال | ✅ Match | 16 fields added (B1 type, quality rules and classification + both sheets); both sheets are imported and merged per attribute, linked to their data entity. CRUD owners and owner e-mails are not kept |
| Data Vault (`DataVault`) | — | 🟡 Partial | See B-5 |
| Physical Host (`PhysicalHost`) | أجهزة المضيف المادي | ✅ Match | Hypervisor type and version added |
| Server (`Server`, subtype virtual) | دليل الخوادم الافتراضية | ✅ Match | Backup and DR cover added; the power-state column is not kept |
| Network Device (`NetworkDevice`) | دليل الأجهزة الشبكية | ✅ Match | |
| Storage (`Storage`) | دليل التخزين | ✅ Match | |
| Infrastructure Management Tool | أدوات التقنية التحتية | ✅ Match | |
| Infrastructure Service | خدمات التقنية التحتية | ✅ Match | Service code added |
| Security Hardware | أجهزة الأمن | ✅ Fields added | Code, firmware, contract status, type of operation, costs |
| Security Software | برمجيات الأمن | ✅ Fields added | Code, version, contract status, type of operation, costs |
| Security Service | خدمات الأمن | ✅ Fields added | Code, function, contract status, type of operation, costs |
| Beneficiary Journey | — | ✅ Match | Code and objective were already present (v4) |
| Journey improvement (`JourneyImprovement`, hidden) | التحسينات على رحلات المستفيدين | ❌ Hidden type | The sheet's rows have no visible NORA home; decide between a visible type or fields on the journey (B-7) |
| Persona | — | ✅ Match | Code landed |
| Beneficiary | — | 🟡 Partial | See B-4 |
| Pillar | — | ✅ Match | Code and order landed |
| Vision, Mission, Objective, Initiative, Project, KPI | — | ⚪ Not compared | No template; compare with B1 §5.3.2 |
| Capability, Org Unit, Service Provider, Activity, Product, Position, Role | — | ⚪ Not compared | Compare with B1 §5.3.3 |
| Application Module, Application Function | — | ⚪ Not compared | Compare with B1 §5.3.7 |
| Data Center, Network Link, Containerization Engine, License, Peripheral Device | — | ⚪ Not compared | No template sheet; compare with B1 §5.3.8 |

Guard: `test_every_template_field_exists_on_its_target_type` fails when a template column writes a field its NORA type does not have.
