# Changelog

All notable changes to Turbo EA are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [fork-feature] - 2026-06-26

### Added
- **Architecture Standards, linked to Principles.** A new managed entity captures the concrete standards that implement your architecture principles (e.g. "Approved RDBMS is PostgreSQL"). Manage them under **Admin → Metamodel → Standards** — each standard can be linked to one or more EA principles — and browse the active set under **GRC → Governance → Standards**. Standards (and their principle links) are included in the workspace export/import bundle.
- **Manage principles and standards inline from GRC → Governance.** Users with the *Metamodel* admin permission now get the full create / edit / activate / delete controls directly on the **GRC → Governance → Principles** and **Standards** sub-tabs — the same management UI as Admin → Metamodel — so governance authors no longer have to switch pages. Users without that permission continue to see the read-only list.

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
