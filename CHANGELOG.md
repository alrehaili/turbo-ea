# Changelog

All notable changes to Turbo EA are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [1.67.0] - 2026-07-11

### Added
- **Updated 7-phase NORA methodology tracker.** The NORA Program page can now track the updated Dec-2024 National EA Framework: seven phases with per-domain deliverables in the diagnosis and target-design phases (Business, Beneficiary Experience, Applications, Data, Technology, Security). Fresh NORA installs start on the new methodology; existing 10-stage programs keep running until an admin opts in via a one-click switch that preserves all history.
- **EA Requirements register.** The methodology's continuous element: register architecture requirements, approve them through governance, track them through development cycles via an assigned initiative, and assess change impact through their linked cards. New panel on the NORA Program page.
- **Technology Landscape report** (`/reports/technology-landscape`): IT components grouped by data-center containment (data center ⊃ host ⊃ VM ⊃ container engine) and by network segment, with a security-components-only toggle.
- **NEA viewpoint registry** in the View Library: all ~47 core viewpoints of the National EA Viewpoints Document (bilingual ar/en names, type, level, methodology linkage) mapped to the Turbo EA view that produces each one.
- **Practice operating-model pack**: nine new governed-document templates (EA Mandates, EA Services, Organizational Structure, Governance Model, EA Processes, Interaction Model, EA KPIs, EA Vocabulary, and an umbrella Operating Model) plus a ten-item practice-establishment checklist on the NORA Program page with one-click document creation.
- **Journey-improvement traceability** on Improvement Opportunities: link an opportunity to a beneficiary journey and phase, record feasibility, and use the new BX (Beneficiary Experience) and SEC (Security) domains.
- **Security-protection semantics**: the Application → IT Component relation gains a "usage role" attribute (uses / is protected by), the Security layer overview lists the security hardware/software/service components, and the NCA ECC compliance scan flags applications with no linked security component.
- **Strategic Pillar card type** (NORA profile v6): pillars are now first-class cards (code + display order) with an Objective → Pillar "supports" relation; the Strategic House and Strategy Cascade read them (the earlier Objective pillar-subtype keeps working).
- **Strategy demo data**: `SEED_NORA=true` now seeds a test strategy cascade — two pillars, linked objectives, a program ⊃ initiative ⊃ projects chain, one deliberately unaligned project (to demo the warning), and a demo vision/mission (never overwriting real ones).
- **Strategy Cascade report** (`/reports/strategy-cascade`): the full strategy chain on one screen — Strategic Pillars ⊃ Strategic Objectives → Programs ⊃ Initiatives ⊃ Projects — with summary tiles per level and a warning list of initiatives that aren't traceable to any strategic objective.
- **Three new NEA viewpoint renderers**: **Strategic House** (`/reports/strategic-house` — editable vision/mission, pillar columns with their objectives), **Business Value Chain** (`/reports/value-chain` — top-tier capabilities as a chevron ribbon with strategic/supporting bands), and **Application Modules** (`/reports/application-modules` — the application ⊃ modules hierarchy tree).
- **Promote TurboLens findings to improvement opportunities**: duplicate clusters and modernization assessments gain one-click promotion into the Improvement Opportunity registry (landing as proposed, with the affected cards linked).
- **Domain Owner and Data Steward stakeholder roles** seeded on Business Capability and Data Object when the NORA profile is active.

## [1.66.0] - 2026-07-08

### Added
- **Automated EA maturity assessment (advisory).** Each maturity dimension now gets repository-derived evidence indicators — coverage ratios (approved cards, apps mapped to capabilities, processes with flows, data ownership, lifecycle coverage, compliance posture, risk hygiene, initiative planning, catalogue alignment, …), adoption counts (principles, ADRs, ADM workspaces, NEA evidence packs) and layer data-quality averages — banded into a **suggested level** per dimension. New assessments pre-fill the suggestion and evidence snapshot, and opening a draft auto-refreshes them from the live repository; the assessor always confirms (accept per dimension, accept all, or override). Live view via `GET /maturity/indicators`.
- **Layers → Overview dashboard** (`/layers/overview`) — an executive view across all six EA layers: hero banner, KPI tiles (total cards, per-layer counts, risks/gaps), six layer cards with health pills and meta grids, the strategy-to-controls layer stack, a health-by-layer bar chart, a priority-attention list, and an inventory preview table. Clicking any card opens the component-details drawer.
- **Layers → Traceability view** (`/layers/traceability`) — pick any card and see its connections across all six EA layers: a selected-component summary, a direct-traceability diagram (one band per layer with relation verbs), direct connections grouped by layer, and the two-hop extended-impact grid. Every node opens the component-details drawer.

### Changed
- **Layers section themed with the EA visual-explorer palette** — light blue-grey canvas, white panels with soft shadows and large radii, blue eyebrow accents, a gradient hero, and pastel healthy/warning/risk surfaces and badges (with dark-mode-aware equivalents). Palette added as the `EXPLORER_COLORS` design-token group.
- **Layer overview pages revamped in the EA visual-explorer style.** Each layer page now opens with a per-layer description and a layer health score card, followed by a mini-KPI strip (cards, types, avg quality, healthy / warning / risk), a **portfolio** grid of status-coloured cards, a lifecycle view with per-phase lanes, per-target-layer **mapping panels** ("Application to Business", "Application to Data", …) with relation verbs on hover, an **integration map** of relations within the layer, a clickable architecture-layer stack showing live cross-layer link counts, a priority-attention list of at-risk cards, and a full catalog table with status, lifecycle, and data-quality health pills. Clicking any card opens a **component-details side drawer** (badges, health, metamodel-driven fields, stakeholders, connected components) with a jump-through to the full card page.

## [1.65.0] - 2026-07-08

### Changed
- **EA Maturity moved under the Governance menu** — it sits with the other governance workflow tools instead of occupying its own top-level tab (still NORA-profile-gated).
- **EA layers restructured to the NORA 2.0 six-layer model.** Card-type categories move from the four legacy layers to **Business, Beneficiary Experience, Application, Data, Technology, Security**: Strategy & Transformation folds into Business, Application & Data splits into Application and a standalone Data layer, and Technical Architecture becomes Technology. Every layer gets its own swim-lane overview and summary under the Layers tab (old links redirect). A guarded migration moves only categories still at their old defaults — admin-customised categories are preserved.

### Added
- **Beneficiary Experience layer** with new Beneficiary Journey and Channel card types (via the NORA profile), joining Government Service.
- **Security layer** as a real metamodel layer with a new Security Control card type; the Security layer page now shows the layer's cards alongside the GRC risk & compliance posture.

## [1.64.0] - 2026-07-04

### Added
- **"Portfolio Decisions" section on the Application card detail.** Users landing on an Application card (say Tableau) now see every rationalization board verdict recorded against that card — with the strategic rationale front and centre, the successor as a clickable chip, risk + execution notes in a two-column split, cost / savings / progress footer, and a direct link back to the assessment on the board. The verdict is colour-accented by TIME decision (invest = green, migrate = amber, eliminate = red, tolerate = blue), so the answer to "what happened to this app and why" is visible without leaving the card. Rows without a recorded rationale surface a warning indicator so missing evidence is called out instead of silently absent. New `GET /rationalization/cards/{card_id}/decisions` endpoint powers the section — one query returns every assessment/decision pair for a card, most recent first.

## [1.63.2] - 2026-07-04

### Changed
- **Rationalization decision rationales rewritten with concrete reasoning.** The initial NexaTech seed had every migrate/eliminate decision carry a rationale that essentially restated the verdict ("Consolidate analytics onto the Power BI standard" for Tableau → Power BI), rather than answering *why this app specifically*. The five migrate/eliminate rationales are now 4-6 sentence business cases citing licence economics (Tableau vs Power BI Pro through M365 E5), platform gravity (repos already on GitHub Enterprise), FTE cost (Jenkins masters + agents), incident history (Opcenter APS/Execution schedule divergence at the Coventry line) and contract-renewal dates that anchor the deadlines. Risk notes and execution notes were also expanded so each decision reads like an ARB-ready record. Idempotent upgrade path: existing seeded installs whose rationale still exactly matches the prior weak text is auto-upgraded on next boot; admin-edited rationales are left alone.

## [1.63.1] - 2026-07-04

### Fixed
- **Application Portfolio Review decisions now show their rationale** — the seed authored a strategic "why" for every TIME decision (e.g. "Consolidate analytics onto the Power BI standard" for Tableau → Power BI migrate), but the field was silently dropped when the assessment was seeded and had no home in the schema, so users saw a `migrate` verdict with no supporting reasoning. Added a nullable `rationale` column to `assessment_decisions`, wired it through the API, exposed a `Rationale (why)` field in the decision edit dialog alongside a proper Risk-note / Execution-notes split (previously only "Description" was editable), and the board now renders the rationale directly under each application name — with an inline "Add rationale" affordance on rows that don't have one yet. Existing seeded installs get their rationale backfilled from the seed on next boot (only where the field is still `NULL`).

## [1.63.0] - 2026-07-04

### Added
- **Application Layer Overview** (`/reports/application-layer`) — Essential Viewer–inspired landing view that stacks the four EA layers (Business Capabilities → Applications → Technology → Data) with metric tiles, portfolio and health donuts, a critical-apps watchlist, and shortcuts to the Portfolio and Dependencies reports. Rendered from existing cards, subtypes, stakeholders, lifecycle and data-quality signals — no additional data collection.
- **EA View Library navigation** — New top-level "View Library" landing page at `/view-library` linking every EA view by domain and analysis depth, so users can find the right view without hunting the reports menu.
- **NORA reference-models explorer** — Browse Business, Application, Data and Technology Reference Models (BRM / ARM / DRM / TRM) inline.

### Changed
- **NORA demo dataset now populates every band of the Application Layer view** — added 5 more Business Capabilities, 4 more Applications, 6 Interfaces (from zero, spanning REST/SOAP/event/SFTP/batch/GraphQL), 3 more Data Objects, 3 more IT Components, plus 33 relations wiring the layered flow (Apps → Interfaces → Data → Storage). Some new cards carry lifecycle dates so the health donut shows real variety (healthy / at-risk / retired) rather than all-unknown.
- NORA is now the default framework profile on this fork.

### Fork operations
- **`RESET_NORA_DEMO=true` env flag** — one-shot upgrade path for installs whose NORA demo landscape was seeded by an older version of the seed. On boot, before re-seeding, clears every card, relation, improvement opportunity, draft SoAW and program-tracker progress row created by the previous seed run — matched by natural key, so customer-created data with unrelated names is untouched. Requires `SEED_NORA=true` to be meaningful; safe to leave on across restarts (the seed then skips on subsequent boots via its marker check).

## [1.62.4] - 2026-07-01

### Security
- **Bumped the nginx base image to `1.30.3-alpine`** for the frontend and edge-nginx images, clearing the `libexpat` < 2.8.2 CVEs (CVE-2026-50219, CVE-2026-56131/56132, and the CVE-2026-56403–56412 series) surfaced by the daily Trivy image scan. The `db` (`postgres:18-alpine`) and build-stage bases track moving tags and pick up Alpine package fixes on the next no-cache rebuild.

## [1.62.3] - 2026-06-30

### Fixed
- **Custom card and relation types now show their name, not their internal key** (#731). A custom Card Type or Relation Type created in the metamodel (with a key like `itAsset` and a name like "IT Asset") was displayed by its key across the Inventory type list and grid, the Create-Card type picker, diagrams, reports, dashboards, and more. It now shows the configured name everywhere, in every language. Label resolution was made structural so the issue cannot recur.

## [1.62.2] - 2026-06-30

### Fixed
- **Enabling "Supports Lineage" on a card type now shows the lineage section** (#729). Turning on Supports Lineage in the Metamodel for any card type (e.g. Business Context, Objective) previously had no visible effect on the card detail page. The Predecessors/Successors lineage section now appears automatically, and existing installs are backfilled.

## [1.62.1] - 2026-06-30

### Fixed
- **Select-field option colors now save reliably.** The color shown in the option color picker is the default for a new or untouched option, but it was only displayed — not stored — so its color dot never appeared in the card editor or Inventory until the picker was explicitly clicked. Every option now persists the color the picker shows on Save, and upgrading backfills the color on options that were previously saved without one (only where other options in the same field already have colors, so intentionally color-less built-ins are left untouched).
- **Metamodel keys no longer lock when they match an existing key.** When adding a new select-field option (or relation-attribute dimension/value), typing a key that matched an existing one used to lock the new field so it couldn't be edited — and silently hid the collision. New keys now stay editable, and a key that duplicates another in the same list is flagged in red and blocks saving until it's made unique.

## [1.62.0] - 2026-06-30

### Added
- **Saved views now remember column layout and sorting.** A saved Inventory view restores not just which columns are shown and your filters, but also the columns' left-to-right order, widths, pinning, and the sort order — so a view shared with stakeholders reopens exactly as it was arranged. Your personal grid arrangement is also remembered between visits.
- **The Inventory remembers the active view and side-panel tab across refreshes.** After applying a saved view, reloading the page re-renders that same view (still highlighted as active) and keeps the same filter/columns/views tab open.
- **"Export current view" from the Inventory.** The Export button is now a menu with two choices: **Export all fields** (the existing full, re-importable workbook) and **Export current view** — a flat, single-sheet snapshot that mirrors what's on screen (only the visible columns, in their current order, for the filtered rows). The current-view export is meant for sharing and is not suitable for re-import.

### Fixed
- **Inventory column filter on the Tags column now works** (#728). Typing a tag name in the Tags column's header filter returned no rows because the column holds a list of tag objects; it now matches against the tag names as shown.

## [1.61.0] - 2026-06-30

### Added
- **Admins can hide the Sponsor button from the user menu.** A new toggle in **Settings → General → Modules** controls whether the Sponsor button appears in the profile (avatar) menu for all users. The Sponsor button itself is shown in that settings panel too, so sponsorship stays reachable from Settings even when it is hidden from the menu. The panel also notes how sponsoring companies can have their logo featured on turbo-ea.org (contact `sponsorship@turbo-ea.org`).

## [1.60.0] - 2026-06-30

### Added
- **Sponsor Turbo EA from the profile menu.** A purple-to-pink **Sponsor** button now sits next to the version number in the profile menu. Clicking it opens a dialog explaining why sponsorship matters, with a link to the "Why I built Turbo EA" blog post and one-time or monthly options via GitHub Sponsors. The version label is also slightly larger and easier to read.

## [1.59.1] - 2026-06-30

### Fixed
- **Select field options added later now keep their color.** When an admin added a new option to an existing single-select or multi-select field, the new option could be saved without a color even though the picker showed a default — so its color dot was missing in the card editor and Inventory filter. New options now adopt the displayed default color, matching what the picker shows.
- **Select field options now require a key.** The field editor let an option be saved with only a label and no key; on a card such an option appeared in the dropdown but could not be selected, displayed, or saved. The editor now keeps Save disabled until every option has a valid key.

### Changed
- **Empty mandatory fields are highlighted in red across the Metamodel editor.** Required inputs — card-type key/name, field key/label, select-option keys, subtype key/label, relation key/verb, relation-value dimensions and options, and stakeholder-role key/name — now show a red border when left empty, so it's clear what still needs filling in before Save is enabled. A key field turns red once you start filling in its row (i.e. type the matching label/name) while the key is still empty, so a not-yet-started row is never flagged.

## [1.59.0] - 2026-06-30

### Added
- **Edit a compliance finding.** Open any finding and use the new **Edit** button to change its compliance status (e.g. Compliant → Partial), severity, requirement, gap, evidence, remediation, article, or linked card after it was created — previously these could only be set at creation time.

### Fixed
- **Accepting a compliance finding from a card now asks for a rationale.** On a card's Compliance tab, choosing **Accepted** in the lifecycle opens the review-note dialog (the same as in the GRC Compliance module) instead of failing with "review_note is required".
- **The bulk "Update decision" dropdown shows readable labels** (e.g. "In Review") instead of raw keys like `compliance.lifecycle.in_review`.
- **Risk detail page on mobile.** The status-workflow stepper now scrolls within its card instead of stretching the page, so every section renders at the same width; the risk matrix and header also adapt to narrow screens.
- **Card subtype now shows its label, not its key.** The card side panel header displayed the raw subtype key (e.g. `aiModel`) instead of the translated label (e.g. "AI Model").
- **Compliance tab is readable on mobile.** A card's Compliance tab now renders findings as a stacked, tappable list on small screens instead of a cramped six-column table.

## [1.58.0] - 2026-06-29

### Added
- **Admin-configurable link types & file categories.** A new **Resources** tab under **Admin → Metamodel** lets admins curate the two lists shown on every card's Resources tab: the **link types** for document links and the **categories** for file attachments. Add your own entries, rename or reorder the built-ins, pick an icon for link types, translate labels per language, or disable entries you don't use. Built-in entries can be disabled but not deleted; the defaults now include a new **Contract** link type. The lists travel with **Workspace Transfer** between instances.

## [1.57.0] - 2026-06-27

### Added
- **Redesigned Diagrams gallery.** Diagram cards are now more compact, and a left **filter sidebar** narrows the gallery to *All diagrams*, *Created by me*, or your *Favorites*. A **search box** matches a diagram's name, its author, and the names of the cards drawn inside it. Diagrams can be organized into **groups** — shared, workspace-wide labels that a diagram can belong to several of at once — shown as collapsible headings with anything unassigned under *Ungrouped*. Each card has a **favorite** star (per user), and a *Sort* control orders by recently updated, recently created, or name. Diagram groups, their membership, and favorites are included in **Workspace Transfer**, so they clone between instances along with the diagrams.

### Removed
- **Removed the unused Data Flow / Free Draw diagram type.** The distinction was never used by any feature; diagrams are now a single kind.
- **Removed the Diagrams list/table view.** The gallery is now card-only, with grouping, search, and filters.

### Fixed
- **The diagram editor's "Save & Exit" button now works.** Clicking *Save & Exit* in the DrawIO toolbar saves the diagram and returns to the viewer; previously it neither saved nor exited.
- **The Diagrams filter sidebar matches the inventory sidebar and is collapsible.** Same colours and styling; it collapses to a slim rail via a chevron on desktop (width and state remembered, drag-to-resize) and opens as a slide-in panel on mobile.
- **Adding a diagram to a group now updates the gallery instantly** instead of requiring a page refresh.

## [1.56.0] - 2026-06-27

### Added
- **Reveal a card's parent or children on the dependency diagram.** The Layered Dependency View (Dependencies report and the card-detail dependency section) has two new tools in the left toolbar beside Highlight and Expand: **Reveal parent** and **Reveal children**. Turn one on, then click any card to add its hierarchy parent or its direct children to the diagram — a targeted alternative to Expand, which pulls in every neighbour at once. Revealed cards stay on the diagram so you can layer parents and children together in one view; re-centering or **Reset view** clears them.

### Changed
- **The dependency diagram's "Show parent hierarchy" toggle is now "Show hierarchy markers".** Instead of pulling every card's ancestors into the view at once, the **Card display** menu now adds a minimalistic chevron to any card that has a parent or children not currently shown — a subtle hint to use the new Reveal tools — keeping the diagram uncluttered. Bringing parents/children into view is now done deliberately with the Reveal parent / Reveal children tools.
- **The dependency diagram's left toolbar is reorganised into two groups.** View controls (**Fullscreen** at the top, then zoom, re-center, **Reset view**) are separated by a divider line from the exploration tools (Highlight, Expand, Reveal parent, Reveal children). Reset and Fullscreen moved here from the top bar. The re-center button now uses a map-pin icon so it's no longer confused with Fullscreen.
- **"Reset view" now fully resets the diagram.** Besides undoing manual node drags, it clears any parent/children/expand exploration and returns to the starting card — a true clean slate.

## [1.55.0] - 2026-06-27

### Added
- **Turn a dependency diagram into an editable diagram.** The Layered Dependency View (Dependencies report and the card-detail dependency section) has a new **Create diagram** button in its toolbar. It recreates the on-screen graph — cards, relationships, and the four architecture layer lanes — as a new diagram in the Diagram module, where you can keep editing it. Every shape stays linked to its inventory card. You're prompted for a name, then taken straight to the new diagram. The button only appears for users who can create diagrams.

## [1.54.0] - 2026-06-27

### Changed
- **Card pickers now let you browse, not just search.** Every dropdown that links a card — relations (card detail and the inventory grid), parent/child hierarchy, predecessors/successors, the Create card parent, vendor/Provider linking, ADR card links, BPM element linking, and compliance findings — now shows cards immediately when you open it, sorted alphabetically, and loads more as you scroll. The list narrows from the very first character you type. No more guessing an exact name before anything appears.

## [1.53.0] - 2026-06-27

### Added
- **Relationship values now appear in dependency diagrams.** When a relation is qualified with a value (e.g. an application *supports* a capability as *Leading*), the Layered Dependency View (Dependencies report, the card-detail dependency section) shows it in brackets next to the label — *supports [Leading]*. Relations without a value render exactly as before. A new **Show relationship values** toggle in the **Card display** menu (on by default) can hide them.

### Fixed
- **Dependency-diagram image export no longer breaks on direction arrows.** The flow-direction indicators (→ ↔ ←) are now drawn as vector graphics instead of font glyphs, and exports are downloaded as a binary blob. Previously, a diagram containing these arrows would export a blank/invalid image that the browser saved with a `.txt` extension; PNG and SVG exports now save correctly (with the arrows and relationship-value labels visible).
- **Dependency-diagram export now works on iPhone/iPad and stops logging console errors.** Image export no longer attempts to fetch remote web fonts (which the Content Security Policy blocked, spamming the console), and the rendered image is now scaled to stay within WebKit's canvas size/area limit — fixing export on iOS, where it previously failed with a "Load failed" error or produced nothing. Desktop export quality is unchanged.

## [1.52.0] - 2026-06-27

### Changed
- **Dependency view hides end-of-life cards by default.** The Layered Dependency View (Dependencies report, the card-detail dependency section, and TurboLens Architect) no longer shows related cards whose lifecycle has reached End of Life — keeping the graph focused on what still matters. A new **Show end-of-life cards** toggle in the **Card display** menu brings them back. The card you are centered on is always shown, even if it is itself end-of-life.

## [1.51.0] - 2026-06-26

### Added
- **Tags can have a description.** Admin → Metamodel → Tags: each tag now has an optional description (tag groups already had one), shown as a tooltip in the admin and carried through workspace export/import.

## [1.50.1] - 2026-06-26

### Fixed
- **Arabic right-to-left layout now extends to data grids and charts.** With Arabic selected, the Inventory grid and the other data tables (Risk Register, Compliance, ADRs, Users, Audit Log) mirror to right-to-left — column order, header and cell alignment, and horizontal scrolling all follow RTL. Charts across the Dashboard, the Data Quality and Cost reports, and the BPM dashboard/assessment views also flip: axes move to the right and read right-to-left, category labels and axis numbers sit outside the plot, and legends and tooltips are RTL-aligned and spaced.
- **Currency selector is now translated, and Saudi Riyal shows its own symbol.** The currency picker in **Admin → Settings** lists currencies by their localized name in the active language instead of fixed English text. Saudi Riyal now displays the dedicated ⃁ symbol (falling back to "SAR" on platforms whose fonts don't yet include it).

## [1.50.0] - 2026-06-26

### Added
- **Stakeholder roles count toward data quality.** Admin → Metamodel → a card type's **Data quality** panel has a new **Stakeholder roles** contributor alongside Description, Lifecycle, Relations and Tags. Each stakeholder role defined for the type is a completeness slot that's satisfied once someone is assigned to it. Like the other built-in factors it counts at *Normal* weight by default (only for types that actually define roles); set it to *Ignore* to exclude it.

## [1.49.0] - 2026-06-26

### Added
- **Layered Dependency View is now interactive.** The dependency diagram (Dependencies report, the card-detail dependency section, and TurboLens Architect) gained a toolbar: drag cards to rearrange them within their layer — and drag a whole **layer box** to move it with all its cards — with **Reset layout** to restore the automatic arrangement, plus **Fullscreen**, **Export** to PNG or SVG, and a canvas **background** that cycles between grid, dots, and none.
- **Configurable card appearance in the dependency view.** A new **Card display** menu lets you toggle the type label and a lifecycle-status dot, and pick extra attribute fields to show directly on each card — the first two render on the card and the full set appears in the hover tooltip. Choices are remembered between visits.
- **Show parent hierarchy in the dependency view.** A new toggle adds each card's parent card to the diagram and draws the *contains / part of* containment link, so hierarchical context (e.g. a parent Organization) is visible alongside the relationship graph.
- **Card-type icons in the dependency view.** Each card in the Layered Dependency View now shows its metamodel icon in the top-left corner, making card types recognisable at a glance.

## [1.48.0] - 2026-06-26

### Added
- **Surveys can now ask respondents to maintain relationships, not just attributes.** When building a survey, the Fields step has a new **Relations** section listing every relationship the target card type can have (in both directions). Pick any to have respondents review the linked cards — set each to **Maintain** (edit the linked set: add or remove cards via a search picker) or **Confirm** (acknowledge the current links are correct). Applying a response syncs the relations on the card, recorded in its history like a normal relation change.

## [1.47.3] - 2026-06-26

### Fixed
- **Metamodel: custom self-relations are no longer blocked by the built-in "succeeds" relation.** Creating a self-referential relation type (e.g. Data Object → Data Object) failed with "a relation type already exists" for card types that ship a built-in successor relation — most types, including Application, IT Component and Data Object. The hidden successor relation is no longer counted toward the one-relation-per-pair rule, so you can add your own self-relation alongside it.
