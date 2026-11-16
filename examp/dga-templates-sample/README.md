# DGA data-collection templates — filled sample

Two of the official DGA data-collection templates (`NORA/`), filled with a small, made-up example entity, to try the importer in **Admin → Settings → Migration**. Pick the **NORA data-collection templates (DGA)** source and upload one workbook at a time. Apply the NORA framework profile before importing.

| File | Template | Sheets filled |
|---|---|---|
| `DGA-sample-business.xlsx` | بنية الأعمال | دليل الخدمات (3), دليل الإجراءات (4), دليل النماذج (4), دليل السياسات (3) |
| `DGA-sample-data.xlsx` | بنية البيانات | دليل قاموس البيانات (3), دليل فهرس الأعمال (7), دليل سمات البيانات (6) |

The layout of each sheet is unchanged: row 1 is the title, row 2 the headers, row 3 the explanations, and data starts on row 4. The template's own example row was replaced so every link in the sample resolves.

## What an import produces

**Business file:** 3 services, 4 business processes, 4 models/templates, 3 policies and 2 applications. The applications are named in the services' and processes' "applications used" columns, so they come in as placeholders. The links:
- service → process (4)
- service/process → application (6)
- service/process → model/template (5)
- policy → service (5)
- policy → process (3)

**Data file:** 3 data entities and 7 data attributes, each linked to its data entity.
- Attributes ATR1–ATR6 are in both attribute sheets and merge into one card each. The business catalogue's values are kept, and the attributes sheet adds table, schema, data type, length, format and primary key.
- ATR7 is in the catalogue only.

Not imported, as the importer notes on upload: the introduction sheet, the stakeholders sheet (no e-mails to match users) and the lookup lists.

## Notes

- Saving with `openpyxl` drops the templates' drop-down validation lists. The values used are the templates' own lookup values.
- The data is fictional, and identifiers such as the national ID are masked (`1xxxxxxxxx`).
- `build_sample.py` rebuilds both files from the templates in `NORA/`.
