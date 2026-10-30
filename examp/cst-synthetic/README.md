# CST-inspired organization — Turbo-EA import kit

This is a fictional enterprise architecture inspired by the public service remit of Saudi Arabia's Communications, Space & Technology Commission (CST). It is **not an official CST inventory, organization chart, strategy, compliance statement or disclosure of internal systems**. Departments, applications, architecture, suppliers, infrastructure, budgets, personnel roles, measurements and targets are synthetic. No real personal data or credentials are included.

Prepared against the local Turbo-EA 2.43.0 NORA metamodel on 30 October 2026.

## Files and which one to upload

- **CSTD-full-import.zip** — the ready-to-import sample. Upload this file to **Workspace transfer**, not Platform migration. It contains only the native `manifest.json` and `workspace.xlsx`.
- **CSTD-full-organization.xlsx** — readable, editable example with one sheet per card type, plus relations, lifecycle dates, card metadata, field guidance, valid options and sources. This is a collection workbook, not a platform snapshot.
- **CSTD-blank-collection-template.xlsx** — matching blank workbook for collecting another organization's real data.
- **prepare_import.py** and **collection-schema.json** — offline converter and the exact schema it validates against. Keep these files together. The converter does not access a database or the network.
- **import-validation.json** — actual local native-import preview result; the preview was rolled back.
- **coverage.json** — all card types and record/field counts.

The outer **CSTD-complete-kit.zip** is a download container. Do not upload the outer kit ZIP to Turbo-EA; extract it and upload `CSTD-full-import.zip`.

## Sample coverage

| Content | Count |
|---|---:|
| Card types | 64 |
| Types visible in NORA | 48 |
| Types hidden in NORA | 16 |
| Cards | 456 |
| Configured field entries across types | 384 |
| Populated attribute values | 3,389 |
| Relationships | 2,805 |
| Distinct existing relation types used | 222 |
| Stakeholder assignments | 456 |
| Public-context document links | 456 |
| Inactive fictional stakeholder accounts | 6 |

Every card participates in at least one relationship. Names start with `CSTD |`, external IDs start with `CSTD-`, and every sample card carries the `CSTD Dataset / Synthetic test data` tag. All sample cards are drafts. Costs are illustrative SAR amounts.

All 384 configured field definitions are represented. System-derived hierarchy fields use sample hierarchy values. `metricKey` is intentionally empty on the eight manually measured KPIs: assigning an executive metric would make the application calculate a different measure. Empty parent paths on roots and absent subtypes where the type defines none are intentional. Unknown real-world values should remain blank in your real collection rather than being invented.

This covers the card inventory and its supporting relations, tags, stakeholder assignments and source links. It does **not** claim to seed every independent module: GRC risk registers, ADRs, BPMN diagrams, PPM task plans, surveys and other module tables are outside this kit.

## Import the sample into a live test workspace

1. Use an administrator account in the intended test workspace. Keep the current NORA metamodel active and use a compatible Turbo-EA code version.
2. Open **Admin → Settings → Migration → Workspace transfer**.
3. Upload **CSTD-full-import.zip**.
4. Read the preview before applying. On a workspace that does not already contain the sample IDs, the core counts should be 456 new cards and 2,805 new relationships. Supporting rows bring the total to 4,722 created rows.
5. Apply the preview when the rows and workspace are correct. No deployment or import was performed on your live system during preparation of this kit.
6. Browse the visible inventory using the `CSTD Dataset` tag. Start with the cloud registration service and follow its process, application, data, owning unit and capability links.
7. Hidden-type records remain hidden under NORA. Use the workbook's Overview and Type Guide to inspect coverage. Unhide a type through the metamodel UI only if you intentionally want to expose it; the import does not change type visibility.

No metamodel, permissions, branding, feature settings, passwords, SSO configuration, SMTP settings or active accounts are imported. The six fictional member accounts exist only for stakeholder references, are inactive, and have no passwords. Your administrator login is not replaced.

## Reuse the blank workbook for real data

1. Work on a copy of the blank collection workbook. Keep the schema and converter beside it.
2. Each type sheet has human labels in row 3, exact field keys in row 4, and records from row 5. Add rows as needed without moving the key header.
3. Supply a stable, unique `external_id`, an unambiguous name, a useful description and an existing user's `owner_email`. Use your own IDs and names instead of the sample's CSTD identities.
4. Use exact stored subtype and option keys from **Type Guide** and **Options**. Numbers/costs must be numeric. Use actual Excel dates or ISO `YYYY-MM-DD`. Boolean values may be TRUE/FALSE. Multiple-select fields use a JSON array of option keys.
5. Put hierarchy parents in `parent_path`; a child's parent must be included in the same workbook and have the same type. Paths use ` / ` between ancestor names. Avoid backslashes and ` / ` inside individual card names.
6. Use **Lifecycle** for lifecycle phase dates and **Card Details** for status, approval status, alias, change type and source metadata; link those rows by `external_id`. Architecture state belongs on the type sheet.
7. Complete **Relations** with existing relation type keys from **Relation Guide**. Endpoint references are the exact full hierarchy path plus the card's name. Both endpoint cards must be in the collection workbook. Relation `attributes` must be a JSON object using declared attribute keys and valid option values.
8. Gray fields are system-derived. The converter recomputes hierarchy depth from parent paths. Do not repurpose gray fields as manual business measurements.
9. Install Python with `openpyxl` if not already available; the backend Python environment already includes it. From the extracted kit directory, run:

   ```powershell
   python prepare_import.py "My-organization.xlsx" "My-organization-import.zip" --check-only
   python prepare_import.py "My-organization.xlsx" "My-organization-import.zip"
   ```

10. Upload the resulting ZIP through **Workspace transfer**, inspect its preview, then apply. The converter emits cards, relations and owner references only; it does not create users. Owner emails must identify accounts already created by an administrator on the target.

For direct testing of the supplied sample, use its ready-made import ZIP. Converting the filled example separately assumes its six fictional owner accounts already exist, for example after importing the supplied sample.

Native workspace transfer creates or skips existing cards matched by external ID or type/path/name. Re-importing the same pack is not a bulk-update mechanism. Use new stable IDs for a separate organization; use normal inventory editing or the appropriate update/import workflow for changes to existing cards.

## Local validation result and limitation

The actual native bundle was parsed by Turbo-EA and passed its real workspace-transfer preview engine with **0 failed rows and 0 conflicts**. The preview reported 4,722 rows created and was rolled back. Card, relationship and user table counts were checked before and after and were unchanged.

The local configuration already contains calculation expressions that the calculation engine cannot evaluate. The preview logged unresolved names for `Capability Coverage` (`related_applications`), `Application Total Annual Cost` (`attributes`) and `Risk Exposure Score` (`related_risks`). No calculation definitions are shipped in the kit. Imported source attributes are present in the workbook, but calculated outputs on a target with these same expressions may remain unavailable. This is an existing local calculation-configuration limitation, not a row-import failure. Those definitions were not changed.

## Public sources

Public information is used only to choose realistic regulatory service themes. The spreadsheet and source-link records distinguish that public context from invented internal detail.

- [CST — Who we are](https://www.cst.gov.sa/en/about/who-we-are)
- [CST — Service level agreement](https://www.cst.gov.sa/en/about/service-level-agreement)
- [CST — Cloud computing registration](https://www.cst.gov.sa/en/business/services/Cloud-Computing-Registration)
- [CST — Submit an interference complaint](https://www.cst.gov.sa/en/business/services/Submit-an-interference-complaint)

## Cleanup

Locate the sample through its CSTD prefix and dataset tag, then use normal archive controls if you want to remove the test inventory from everyday views. Retain any records you intentionally used as references. Do not delete unrelated users, metamodel definitions or existing organizational data.
