# Technical readiness

## 1. Frontend structure [Confirmed]

- React 19, MUI 6, Recharts (code-split), React Router; Dashboard tabs in `features/dashboard/`; route permission table in `lib/routePermissions.ts` (`/` is deliberately ungated; tabs gate themselves via `hasPermission`).
- Data loading: `useApiQuery` (race-safe), singleton boot hooks; formatting via `useCurrency`, `useDateFormat`, `fiscalYearLabel`.
- i18n: 10 locales, flat dotted keys in `common.json`; RTL via `isRtlLocale`, Emotion RTL cache and `lib/rechartsRtl.tsx`.
- Phase-one Executive tab: a single ~780-line component (`executive/ExecutiveTab.tsx`) with local building blocks. **Readiness**: good base. [Recommendation] Split it into `executive/components/*` and one page per section before adding the eight pages.

## 2. Backend and dashboard APIs [Confirmed]

| Endpoint | Purpose | Gate | Read scope | Notes |
|---|---|---|---|---|
| `GET /reports/dashboard` | Overview | `reports.ea_dashboard` | ✅ module | Includes hidden types |
| `GET /reports/executive` | Executive | `reports.executive_dashboard` + `costs.view` for money | ✅ module | Composes `executive_dashboard.py` builders, `ppm_portfolio_service`, `bpm_dashboard_service`, `load_filtered_risks` |
| `GET /reports/my-workspace` | Workspace | user | ✅ | Excludes hidden types |
| `GET /reports/admin-dashboard` | Admin | `admin.users` | ✅ module | Excludes hidden types |
| `GET /reports/bpm/dashboard` | BPM KPIs | `reports.bpm_dashboard` | ✅ | Now delegates to `bpm_dashboard_service.build_bpm_dashboard` |
| `GET /reports/ppm/dashboard` | PPM KPIs | `ppm.view` | ✅ | **Returns budget and actual without `costs.view`** (inconsistent with the cost-report rule) |
| `GET /risks/metrics` | Risk KPIs | `risks.view` | ✅ | |
| `GET /nora-program/dashboard` | NORA committee view | `nora.view` | ❌ **no `CardReadScope`** | Reuse requires the scope first |
| `GET /maturity/overview`, `/indicators` | Maturity | `maturity.view` | ❌ | as above |
| `GET /improvement-opportunities/realized-value` | Realised count per quarter | `grc.view` | ❌ | Realisation date = `updated_at` |

**Aggregation pattern** [Confirmed]: the phase-one service keeps the loaders (SQL) separate from the pure builders. The builders are mutation-testable (mutmut skips decorated route handlers, per CLAUDE.md). This is the pattern to extend.

**KPI calculation services** [Confirmed]: no generic KPI engine exists. `calculation_engine.py` (simpleeval) computes **card-level calculated fields** on save. It is not suited to portfolio aggregates. [Recommendation] Do not build a generic formula-driven KPI engine in phase two. Write each executive KPI as a named, versioned, tested builder function, and store the definition text, owner and target on a `KPI` card.

## 3. Database schema and history [Confirmed]

- Card model: `attributes` JSONB (metamodel-driven), `lifecycle` JSONB, `architecture_state`, `change_type`, `successor_id`, `approval_status`, `data_quality`.
- History sources: `events` (every write path must publish with `db=`, carrying whole old/new `attributes` and `lifecycle`, per CLAUDE.md); `kpi_snapshots` (daily, unique on `snapshot_date`, **4 fixed columns**: total_cards, avg_data_quality, approved_count, broken_count) captured by `_kpi_snapshot_loop` in `app/main.py:357`; `ppm_status_reports` (dated); `maturity_assessments` (dated); `audit_log`.
- **Historical measurement requirement**: executive trends need period values that **do not change when the current data changes**. Reconstructing them from events on every request is expensive and fragile. [Recommendation]
  1. Extend the snapshot loop to a **key/value fact table** (`metric_key`, `period`, `scope`, `value`, `calculation_version`), or replace `kpi_snapshots` with it, migrating the 4 columns.
  2. Add `kpi_measurements` for manually or externally measured KPIs (DATA_AND_FUNCTIONAL_GAP_ANALYSIS.md G1).
  3. **Scope caveat**: landscape-wide snapshots must not be shown to restricted readers. The existing rule at `reports.py:255` (trends only when `read_scope.is_unrestricted`) must carry over.

## 4. Access control and confidentiality [Confirmed]

- Permission keys live in `core/permissions.py`. Phase one added `reports.executive_dashboard`, held only by admin (wildcard) by default.
- Every aggregate must apply `CardReadScope` (CLAUDE.md: "omit entirely"). A total that includes hidden cards leaks their existence by arithmetic.
- Money requires `costs.view`. The phase-one endpoint enforces this; **`/reports/ppm/dashboard` does not** (finding to fix separately).
- **Small-number disclosure** [Recommendation]: aggregates filtered to a small segment can reveal individual values (e.g. one application's cost). Apply a minimum-group rule (suppress values with n < 3) for restricted readers on segment filters.
- Fork modules without the read scope (G13) must not feed executive aggregates until fixed.

## 5. Auditability [Recommendation]

- Each KPI response carries `calculation_version`, `as_of`, `sources[]` and `period`.
- Manual entries (benefits, KPI measurements) are written through `event_bus.publish(..., db=db)` and the security audit log contract (`audit_log.record` with `items`), so changes are reviewable.
- Benefit status transitions record approver and timestamp; "realised" requires an evidence link (document or attachment, reusing `documents` / `file_attachments`).

## 6. Performance and scalability [Confirmed + Recommendation]

- Phase one runs about 12 queries per request, including a full load of BusinessProcess cards and all risks, computed live. This is fine at demo scale (391 cards).
- At enterprise scale (tens of thousands of cards, eight pages): [Recommendation] compute heavy aggregates from the daily fact table; keep the live path for "today" tiles only; cache per (user scope hash, period) for 5-15 minutes. Never hold a DB session across slow work (CLAUDE.md rule).
- Single uvicorn process and a 30-connection pool (CLAUDE.md): page loads must not fan out into N parallel endpoint calls per tile. One endpoint per page.

## 7. Security considerations [Recommendation]

- No raw SQL; parameterised ORM only (project rule).
- PII: executive payloads carry aggregates and decision titles only, never user emails (use `_user_response_lite` shapes for owners).
- Export (PPTX / XLSX) must apply the same scope and `costs.view` rules as the screen; exports are recorded in the audit log (CLAUDE.md data-export auditing).
- AI-generated insights (optional, later) must only receive the caller-scoped aggregate payload, never raw cards (mirror `_require_whole_landscape` in TurboLens).

## 8. Extend the Dashboard module, or add modules? [Recommendation]

**Extend the existing Dashboard → Executive tab** for presentation, and add **two small supporting capabilities**:

1. **KPI history** (`kpi_measurements` + snapshot fact table): extends the existing KPI card and snapshot loop.
2. **Benefits register** (`benefits` linked to existing decision records): a new, narrow module, because no existing entity can hold a status-bearing financial value.

Decision actions reuse **todos**; escalations reuse a **tag group**; milestones derive from **PPM WBS**. No parallel executive database, no separate frontend, and no duplicate project, decision or risk entity.
