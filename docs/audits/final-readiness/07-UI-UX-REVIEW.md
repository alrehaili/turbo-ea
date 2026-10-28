# UI/UX operational review

Method: component/form/API source inspection and four executed frontend test files, **not a live visual or accessibility audit**. No browser workflow, Arabic user observation, screen-reader run or rendered export was available. This distinction prevents a page's existence from becoming a usability PASS.

## Positive implementation evidence

`frontend/src/api/client.ts:90–109` converts structured validation errors and fallback HTTP failures into user-facing errors. Backend 422 lists and structured messages have a consistent handling path. This does not prove every page catches and displays errors.

`frontend/src/App.tsx:437–462` updates document direction/language, theme and RTL Emotion cache. `main.tsx:2–5` bundles Arabic-capable Cairo rather than depending on a public font CDN; `i18n/index.ts:35–49` provides locale direction. NORA definition tests exercise Arabic field/option/section translations. These are functioning infrastructure checks, not proof that every grid, chart or export is correctly mirrored.

`features/nora/NoraProgramPage.tsx`, `NeaEvidencePanel.tsx`, `EaRequirementsPanel.tsx`, `EvidencePickerDialog.tsx` and `PlateausSegmentsPanel.tsx` implement program/evidence/requirements/landscape workflows. Card data entry follows configured metamodel fields. This is appropriate for an EA repository, but actual field grouping must be evaluated with the authority's configured metamodel.

`features/dashboard/executive/ExecutiveOverview.test.tsx`, `ExecutiveDecisions.test.tsx`, `executiveFormat.test.ts` and `executivePlurals.test.ts`: 28 tests passed. They cover a narrow mocked/component slice. Missing/stale/restricted indicators in the backend and explicit planned/reported/confirmed presentation in `ExecutiveBenefits.tsx:112–125,322–326` support cautious reporting. No end-to-end contract or rendered financial approval pass is claimed.

## Operational issues and targeted improvements

| Workflow | Assessment | Minimal action |
| --- | --- | --- |
| NORA approved deliverable editing | Confirmed integrity defect FR-04; live status can misrepresent review of changed evidence | Reset/reopen approval or freeze reviewed content; expose review-needed feedback. No interface redesign required. |
| ARB context and approvals | FR-02/FR-03 affect confidentiality/approval semantics | Redact restricted blocks with a clear access explanation; show who can decide and why self-approval is refused once enforced. |
| Local AI description suggestions | FR-01: configuring a local model may wrongly imply all processing stays local | Disable for pilot; if enabled later, explicit approved external-search control and meaningful indication. |
| Plateau time slices | FR-06: current-data projection can be interpreted as historical evidence | Label projection semantics and show data basis/date. Preserve approved baseline exports. |
| Forms and validation | Implemented validation, but task completion NOT VERIFIED | Trial one real-shaped synthetic card, relation attribute, evidence item and import error; correct only observed confusing fields/messages. |
| Navigation/discoverability | Major features have routes; drawer/lazy-loading work exists; actual user navigation NOT VERIFIED | Give the pilot a short task guide with inventory → card → relations → evidence → review. Observe any genuine dead ends before changing navigation. |
| Arabic/RTL | Infrastructure present; visual and linguistic quality NOT VERIFIED | Native Arabic reviewer checks mixed Arabic/Latin names, right-to-left tab order, numeric/currency/date readability, grid filters, dialogs and error text. |
| Accessibility | NOT VERIFIED | Keyboard-only completion, focus trapping/restoration, icon accessible names and contrast on the pilot's actual screens. Do not classify hypothetical problems as confirmed defects. |
| Excel/diagram/DOCX/PPT exports | Export code exists; rendered Arabic output NOT VERIFIED | Open one exported Arabic artifact in the authority's software, verify glyphs/order, links and data fidelity. |

No additional standalone cosmetic finding is justified by this source-only review. Terminology polish, sidebar rearrangement and broad visual redesign can wait. No observed browser defect preventing basic inventory completion is claimed; that workflow was not executed.

Pilot acceptance: two EA staff, including an Arabic-first user, complete the report 05 scenario without developer assistance, understand draft/approved/verified distinctions, and receive actionable feedback on one invalid field and one denied action. Record failures as specific follow-up defects rather than expanding the project speculatively.
