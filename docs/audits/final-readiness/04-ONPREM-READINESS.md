# On-premises readiness without Docker

Conclusion: the application has a viable native architecture; no Docker dependency is a blocker. A production service configuration and recovery exercise are **NOT VERIFIED**. Use FR-09 as the operational gate, and FR-01 for sensitive outbound behavior.

## Native deployment requirements traced to code

| Component | Requirement and evidence | Verification |
| --- | --- | --- |
| Backend | Python >=3.11 declared in `backend/pyproject.toml:8`; async FastAPI/Uvicorn/SQLAlchemy/asyncpg. Review used existing Windows Python 3.13.7 environment. Pin a tested production interpreter/dependency set; >=3.11 is a declaration, not certification of every version. | Unit checks executed; production runtime NOT VERIFIED |
| Database | PostgreSQL, JSONB/UUID, asyncpg. Packaged reference is PostgreSQL 18 (`Dockerfile:83`); no tested lower-version support matrix established. Some upgrade paths use `pgcrypto` (`alembic/versions/080_rehash_compliance_finding_key_sha256.py:59`, `083_compliance_finding_dedup.py:87`). Provision extension privileges through DBA policy. | Migration graph only |
| Configuration | `app/config.py:78–159` reads process environment; do not assume root `.env` is automatically loaded by plain Uvicorn. Use protected service environment or explicit `--env-file` with installed supporting runtime. Set `ENVIRONMENT=production`, strong unique SECRET_KEY, explicit DB credentials, approved origins and demo/reset flags off. | Static |
| Service | Supervise `uvicorn app.main:app`, bind to loopback/private interface; fixed working directory under backend; graceful termination and automatic restart. Start with one process because lifespan owns recurring jobs and in-memory caches. | NOT VERIFIED |
| Frontend | Build via lockfile with reviewed Node/npm on an approved build host; publish `frontend/dist` through internal static server with SPA fallback. Do not use the Vite development server as production hosting. | TypeScript passed; full production bundle NOT VERIFIED |
| DrawIO | Editor defaults to `/drawio/index.html` (`frontend/src/features/diagrams/DiagramEditor.tsx:180–182`). Supply internal assets; reference build clones DrawIO v31.5.3 (`Dockerfile:121`). A frontend-only build does not establish those separately hosted assets. | NOT VERIFIED |
| Proxy/TLS | Route `/api` to backend, `/drawio` to local assets and other paths to SPA. Preserve SSE streaming, upload limits, timeouts, security headers, TLS and trusted client-IP handling. `nginx/default.conf` contains generated block placeholders; it is not a ready native standalone proxy configuration. | NOT VERIFIED |
| Identity | Local authentication, OIDC and optional trusted proxy modes exist. Internal IdP needs internal token/JWKS reachability, approved claims/role mappings, callback URLs and trusted-header sanitization. Keep backend inaccessible around the authenticating proxy. `config.py:163–255` documents/configures the proxy boundary. | NOT VERIFIED with authority IdP |
| Storage | Attachments are DB binary (`models/file_attachment.py:14–27`). Migration uploads use relative `data/migration_snapshots` (`api/v1/migration.py:92`); transfer uploads use `data/workspace_transfers` (`workspace.py:49`). Preserve writable runtime data and extension/license state; inventory actual paths during installation. | Static |
| Monitoring | Structured application logs and error logging exist; configure service log collection, disk/DB capacity, restart alerts, TLS expiry, background-job success and backup freshness. No site-specific monitoring evidence supplied. | NOT VERIFIED |

Backend startup runs migrations/seeding (`app/main.py:759–839`) and fails on migration failure. `RESET_DB` is destructive; keep it disabled. Fresh schema creation/stamping and upgrading an existing schema follow different paths, so rehearse both as needed. One Alembic head (`1175`) is necessary but not proof of a successful upgrade. Do not roll back a database by just checking out older application code.

Recurring tasks live in the application lifespan (`main.py:1307–1349`): archived-card purge, batch/audit retention, KPI snapshots, recurring task promotion, license renewal, release/store checks, data-quality and operations maintenance. They are not supplied by a Docker-only scheduler. A native single-process service runs them. Multiple workers would each start these jobs; multi-worker/HA behavior was not tested. Keep one worker for the pilot and monitor job completion.

## Outbound connection inventory

| Connection | Trigger/data | Offline decision |
| --- | --- | --- |
| DuckDuckGo | Description suggestion: card name plus search suffix; hardcoded public search even with Ollama | Disable suggestions; FR-01 |
| Configured cloud AI/OpenAI-compatible/Azure/Anthropic/Bedrock/TurboLens | User-triggered inference; prompts can contain organization context | Disable, or explicitly approve internal endpoint and verify every call path |
| Ollama model pull | `AI_AUTO_CONFIGURE`, startup model availability; `main.py:705–753` | Keep auto-config off; pre-stage approved model artifacts if needed |
| GitHub release feed | Default-on update check; `services/update_check.py:53,99–104` | Set `updateCheckEnabled=false`; firewall also denies |
| Extension store | Default notices/catalog browsing, install/download; `config.py:43`, `services/extensions/store_catalog.py:43–94`, `extension_store_check.py:76` | Set `extensionNoticesEnabled=false`, avoid store actions; use approved offline bundles |
| License renewal | Installed renewable license; POST customer/key and optional instance ID to `/account/renew`, `extensions/license_refresh.py:199–210` | Block egress; arrange valid offline license/expiry handling for any required extension |
| Capability/principle catalogues | Version/catalogue refresh; PyPI URL in `services/catalogue_common.py:56` | Pre-stage bundled data; avoid online refresh |
| Technology EOL | Feature request to `endoflife.date`, `services/eol_service.py:40` | Avoid or approve cached/manual lifecycle data |
| ServiceNow | Configured external instance integration, `services/servicenow_service.py:80` | Disable absent explicit approval; validation favors hosted ServiceNow domains |
| SMTP/Graph/OAuth email and SSO | Configured notifications/identity; message content may include record titles/links | Use internal approved services or disable notifications |
| Documentation/API reference | External help links; Swagger assets from jsDelivr (`docs/admin/api.md:31–33`); FastAPI reference assets also need checking offline | Optional; mirror if needed. Core SPA need not depend on online help |
| Browser external resources | User-entered links/logos/content and overridden `VITE_DRAWIO_URL` | Review content and enforce browser/server egress policy; validate offline with network capture |

This inventory distinguishes actual requests from schema namespace URLs and input placeholders. No blanket telemetry-free guarantee is made: no full runtime traffic capture was available. Default update/catalogue requests expose network/version metadata; they are not evidence that inventory is sent. FR-01 is the concrete inventory-name transmission path. Core inventory can plausibly operate internally with optional connections disabled/blocked; **fully offline operation is NOT VERIFIED** until network-denied acceptance testing.

## FR-09 — Native deployment and recovery have no executed acceptance evidence

**Category:** operations/verification. **Severity:** P2 readiness gap. **Confidence:** Unverified deployment, confirmed acceptance gap in this review.

**Sources:** `backend/app/main.py:759–839,1307–1349`; `backend/app/database.py:8–25`; `scripts/backup-db.sh:27–65`; `frontend/src/features/diagrams/DiagramEditor.tsx:180–182`; `frontend/nginx.conf:10–11`.

**Actual/expected:** source supplies services, jobs and a native pg_dump script, but no supervised authority installation, TLS trace, restored backup or migration rehearsal was exercised. Expected before official data: repeatable startup, authorized access, no unapproved egress and demonstrated restoration. No claim is made that the actual site lacks these controls; evidence was unavailable.

**Impact/scope:** pilot prerequisite; larger rollout additionally needs approved capacity, availability, RPO/RTO and support ownership. Minimum action: execute report 09's small staging gate, retain the deployment configuration and results. Database backups plus runtime files/SECRET_KEY are needed; workspace export is not equivalent (FR-05). The backup script is native Bash/pg_dump and does not require Docker; use an equivalent approved native procedure on Windows if selected.

**Validation:** restore into an isolated disposable PostgreSQL instance, authenticate, retrieve an attachment and diagram, confirm successor/governance history, restart the service, rehearse upgrade from the intended source revision and verify the agreed recovery time. Never run tests using a production DB connection.
