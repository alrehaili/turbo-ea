# iServer → Turbo-EA Migration Toolkit

Validated end-to-end on the demo repository (2,656 cards + 2,198 relations imported
with **0 failures**). Use it on real offline iServer repositories.

## What Turbo-EA actually expects

The **Workspace Transfer** import (`/admin/settings?tab=migration`) takes **one `.zip`**
containing exactly:

```
manifest.json     # declares format_version "1" + a row count per sheet
workspace.xlsx    # ALL data, as named sheets (Cards, Relations, CardTypes, ...)
assets/           # optional binary files (diagrams) — not used here
```

Loose JSON files are **not** a valid bundle. All inventory lives inside
`workspace.xlsx`: the `Cards` sheet (objects) and `Relations` sheet, validated
against the built-in metamodel sheets (`CardTypes`, `RelationTypes`).

## Files in this folder

| File | Purpose |
|------|---------|
| `export_iserver_json.py`   | Stage 2 — dump iServer SQL tables to **UTF-8** JSON (fixes mojibake) |
| `iserver_to_turboea.py`    | Stage 3 — transform JSON → Turbo-EA `.zip` bundle |
| `template-workspace.xlsx`  | A Turbo-EA workspace used as the metamodel template |

## The pipeline (3 stages if the DB is already live)

### 1. (Only if starting from a `.bak`) Restore the backup
Restore `iServerDB.bak` into SQL Server. **Skip this** if your iServer database
is already running in MSSQL — point stage 2 straight at that server.

### 2. Export tables to UTF-8 JSON
Point `--server`/`--db`/`--user`/`--password` at your live iServer MSSQL instance:
```powershell
pip install pyodbc openpyxl
python export_iserver_json.py --server "YOUR_SQL_HOST,1433" --db "YourISERVERDb" `
    --user "youruser" --password "***" --out "F:\Iserver\Exports"
```
Windows/AD auth instead of a SQL login? Use `--trusted` and drop `--user`/`--password`:
```powershell
python export_iserver_json.py --server "YOUR_SQL_HOST,1433" --db "YourISERVERDb" `
    --trusted --out "F:\Iserver\Exports"
```
This reads NVARCHAR as Unicode, so Arabic/other names are preserved.
(The demo's earlier export mangled them — this is the fix.)

**ODBC driver.** The script defaults to `ODBC Driver 18 for SQL Server` (best
Unicode handling — install free from Microsoft). If only the legacy driver is
present (check with `python -c "import pyodbc;print(pyodbc.drivers())"`), add
`--driver "SQL Server"`; the script omits the incompatible `TrustServerCertificate`
keyword automatically for it.

### 3. Build the bundle
```powershell
# minimal (cards + relations only)
python iserver_to_turboea.py --out "F:\Iserver\Exports\iserver-real-workspace.zip"

# recommended for real data (also carries attributes + real users)
python iserver_to_turboea.py --attributes --users `
    --out "F:\Iserver\Exports\iserver-real-workspace.zip"
```
Outputs the `.zip` plus `unmapped_types.txt`.

### 4. Import into Turbo-EA
`/admin/settings?tab=migration` → **Workspace Transfer** → upload the `.zip` →
**Preview** → **Import**.
➡ **Import into a FRESH/empty workspace** for a zero-conflict result.
(Merging into a populated workspace flags existing items as *Conflicts* — not errors.)

## Tuning for your real repository

- **`TYPE_MAP`** (top of `iserver_to_turboea.py`) maps iServer object types →
  Turbo-EA's 13 card types. After a run, open **`unmapped_types.txt`**: it lists
  every skipped type with a count. Add the ones you want and re-run. Turbo-EA has
  no card type for *Measure* (KPIs) or *Location* — decide per repo.
- **`--attributes`** carries iServer attribute values into each card's
  `attributes` JSON. Turbo-EA renders only keys defined in that card type's field
  schema; unknown keys are carried but may not display.
- **`--users`** maps iServer users that have an email; all get role `member`
  (promote admins in Turbo-EA after import). SSO/AD users are marked `auth_provider=sso`.

## Known limitations / next steps

- **Flat hierarchy.** Cards import without parent/child nesting. The APQC
  numbering (`13.1.4.3` under `13.1.4`) and iServer "contains" relations could be
  turned into `parent_path` — not yet implemented.
- **Relations are type-collapsed.** iServer's 143 relationship types map to
  Turbo-EA's ~15 valid card-type pairs; relations with no valid target pair
  (e.g. Org→Org) are skipped. See the skip reasons printed at the end of a run.
- **Secrets** (SMTP/SSO/AI) are never in the bundle — re-enter them in Turbo-EA.
