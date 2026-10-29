# Source-built production containers

This deployment-specific directory builds this checkout, including fork changes.
It does **not** extend or replace the root `docker-compose.yml` (which pulls upstream
application images). No application source, authentication, RBAC, routes, database
models, or migrations are changed by this arrangement.

## Existing components and routing

The root Dockerfile remains the single build definition. Its runtime targets are
`backend`, `frontend`, `nginx`, `db`, and optional `mcp-server`; intermediate stages
are `backend-build`, `frontend-build`, and `drawio`. BuildKit selects only the
dependencies of the requested target. The frontend uses `npm ci`, TypeScript/Vite,
the committed npm lockfile and vendored xlsx package, and the existing DrawIO build.
Python dependencies are installed from `backend/pyproject.toml`.

```text
Browser -- HTTPS --> TLS ingress (Coolify proxy or existing reverse proxy)
                         |
                         +-- HTTP --> gateway:8080
                                         |-- /api/* --> backend:8000 --> PostgreSQL
                                         +-- SPA / DrawIO --> frontend:8080
```

Only the gateway receives public traffic. The frontend is an internal static
server; pointing a public domain straight to it loses `/api` routing and the edge
security policies. Keep the existing gateway: it implements per-route CSP and
security headers, iframe restrictions and embedding exceptions, upload limits,
SSE buffering/timeouts, OAuth discovery routing, and trusted client-IP forwarding.
Rate limiting remains in the backend (`slowapi`); this setup adds no competing
limiter. The outer ingress handles certificates, HTTP-to-HTTPS redirects and HSTS;
the gateway handles application-specific routing/security. These are the two
existing responsibilities, with no additional proxy introduced.

All three images run as the non-root users defined upstream (UID/GID 1000), with
all Linux capabilities dropped and privilege escalation disabled by Compose.
Only the gateway publishes a host port, bound to loopback at
`127.0.0.1:${TURBO_EA_HOST_PORT}` (default `18920`), forwarding to its unchanged
internal port `8080`. An external Apache reverse proxy on the Docker host can
forward HTTPS requests to `http://127.0.0.1:18920` (or the configured port).
HTTPS termination remains the external reverse proxy's responsibility.
Set `TURBO_EA_HOST_PORT` as a normal deployment environment variable; it is
non-sensitive and does not need secret storage. Backend, frontend and PostgreSQL
ports must not be publicly published. `expose` is descriptive,
not a firewall: use dedicated Docker networks and do not attach untrusted containers.
Backend outbound access remains available for existing integrations.

The public origin **must use HTTPS**, without a path or trailing slash. The
gateway writes `X-Forwarded-Proto: https` rather than trusting the incoming value,
preserving Secure cookies behind TLS termination. It always overwrites
`X-Real-IP`; the backend trusts that header only on its private network. Set
`NGINX_TRUSTED_PROXIES` to the actual ingress IP(s) or a narrow dedicated proxy
subnet. Nginx accepts `X-Forwarded-For` only from those hops, with recursive real-IP
resolution. Never trust every private/Docker range or `0.0.0.0/0`. An empty value
is safe against spoofing but audit/rate-limit addresses become the ingress IP.
The ingress must sanitize forwarding headers and accept no public bypass route
to the backend. Configure multiple proxy hops explicitly if applicable.

Password and existing OIDC/SSO flows are unchanged. Identity-header authentication
remains off unless `TURBO_EA_PROXY_AUTH_ENABLED` is explicitly configured with the
existing verification/shared-secret controls. Coolify alone is not an identity
provider; do not enable platform-header trust merely because it is a reverse proxy.

## Configuration and secrets

Run commands below from the **repository root**, using Docker Compose v2.20+ and
BuildKit. Copy `deploy/docker/.env.example` to an operator-owned file **outside
the checkout**, for example `/secure/turbo-ea/.env.production`, and restrict its
permissions (`chmod 600` on Linux). Paths here are examples, not deployed addresses.
In Coolify, enter the same variables in the resource environment editor instead.

Required variables (blank values fail Compose validation):

| Variable | Meaning |
| --- | --- |
| `DEPLOY_TAG` | Exact source revision being built; use the same tag for related images |
| `TURBO_EA_PUBLIC_URL` | Public HTTPS origin; also supplies backend `ALLOWED_ORIGINS` |
| `POSTGRES_HOST` | Private database DNS alias, never `localhost`; use `db` for the dedicated service |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Application database and credentials |
| `SECRET_KEY` | Persistent random signing/encryption key; generate with `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `POSTGRES_NETWORK` | Existing private database network, required only by the external-network overlay |

Keep `SECRET_KEY` stable: replacing it invalidates sessions and prevents decryption
of existing encrypted settings. Back it up securely with the database. Do not put
secrets in Docker build arguments, frontend variables, committed Compose content,
or image tags. Build arguments receive no runtime settings. `.dockerignore`
excludes nested `.env*`, private key/certificate files, and runtime data so Vite
cannot accidentally bundle a local production env file. This does not detect a
secret manually hardcoded in source code. Do not print a fully rendered Compose
configuration in CI: it contains interpolated secrets; use `config --quiet`.

Optional settings include `POSTGRES_PORT` (5432), `DB_POOL_SIZE` (20),
`DB_MAX_OVERFLOW` (10), `DB_POOL_TIMEOUT` (30), `ACCESS_TOKEN_EXPIRE_MINUTES` (1440),
the three memory limits, `SMTP_*`, `TURBO_EA_EMBED_ALLOWED_ORIGINS`, and
`NGINX_TRUSTED_PROXIES`. The existing `TURBO_EA_PROXY_AUTH_*` controls are passed
through unchanged. Additional backend environment settings can be supplied in a
local Compose override or directly in an independently managed backend resource;
setting an unreferenced variable in a Compose `.env` file alone does not pass it
into a container. Never pass backend settings into the frontend build.

`RESET_DB`, `RESET_NORA_DEMO`, all sample-data `SEED_*` flags, and
`AI_AUTO_CONFIGURE` are fixed false in this production Compose file. This does
**not** suppress normal built-in configuration initialization: upstream startup
still installs missing metamodel/roles/presets and this fork's NORA profile
(`SEED_PROFILE=nora`, or explicitly `togaf` to opt out). It creates no demo
inventory. Existing persisted AI configuration is retained; no AI, Ollama, or MCP
container is included or automatically enabled by this stack.

## Build and run with an existing PostgreSQL container

The database must already have the application database/user, a compatible schema
history, and persistent storage. It must be reachable by its DNS alias on a
private Docker network. The operator owns its readiness, backups, and network
membership. Connect only the backend to that network using the overlay:

```sh
docker compose --env-file /secure/turbo-ea/.env.production -p turboea \
  -f deploy/docker/compose.yml -f deploy/docker/compose.external-db.yml config --quiet
docker compose --env-file /secure/turbo-ea/.env.production -p turboea \
  -f deploy/docker/compose.yml -f deploy/docker/compose.external-db.yml build backend frontend gateway
docker compose --env-file /secure/turbo-ea/.env.production -p turboea \
  -f deploy/docker/compose.yml -f deploy/docker/compose.external-db.yml up -d
```

`pull_policy: build` ensures these services build from this checkout rather than
pull similarly named application images. Keep the project name stable to preserve
network and volume identities. Do not combine the two database overlays.

## Dedicated PostgreSQL service instead

Use `POSTGRES_HOST=db`, set the database credentials, and replace the external
overlay with `deploy/docker/compose.database.yml` in each command above. Build
`db` as well, or run `build` without service arguments. This reuses the root
Dockerfile's non-root `db` target based on PostgreSQL 18. Backend startup waits
for database readiness. PostgreSQL has a named `postgres_data` volume and no
published ports. Password env changes do not rotate an existing initialized
Postgres user's password; plan credential rotation separately.

Do not mount a data directory from a different PostgreSQL major version. An
existing database container may use another supported PostgreSQL version; follow
the application's database compatibility requirements and test upgrades against
a restored copy. The supplied dedicated service uses the repository's current
PostgreSQL major, not an implicit conversion of an existing cluster.

## Independent builds and deployments

No extra Dockerfiles or copied nginx configuration are needed. From the root:

```sh
docker build --target backend -t turbo-ea-local/backend:SOURCE_REVISION .
docker build --target frontend -t turbo-ea-local/frontend:SOURCE_REVISION .
docker build --target nginx -t turbo-ea-local/gateway:SOURCE_REVISION .
```

With Compose, `build backend` or `build frontend` builds just that component.
To replace a component after configuring the stack, keep the same env/project/
Compose-file arguments and run `up -d --build --no-deps backend` (or `frontend`).
The gateway's existing request-time DNS resolution picks up replacement container
IPs without a gateway restart. Match frontend/backend API-compatible revisions;
do not run concurrent backend upgrades against one database.

For individually managed containers, create a dedicated application network and
named backend-data volume first. Example backend and frontend commands (operator
actions, not performed by this change):

```sh
docker network create turboea-app
docker volume create turboea-backend-data
docker run -d --name backend --network turboea-app --restart unless-stopped \
  --cap-drop ALL --security-opt no-new-privileges:true \
  --env-file /secure/turbo-ea/.env.backend \
  --mount type=volume,src=turboea-backend-data,dst=/app/data \
  turbo-ea-local/backend:SOURCE_REVISION
docker run -d --name frontend --network turboea-app --restart unless-stopped \
  --cap-drop ALL --security-opt no-new-privileges:true \
  turbo-ea-local/frontend:SOURCE_REVISION
```

The standalone `.env.backend` must supply the required DB/key variables,
`ENVIRONMENT=production`, `ALLOWED_ORIGINS` matching the HTTPS origin,
`TRUST_PROXY_HEADERS=true`, and the false reset/demo flags from `compose.yml`.
Attach the backend to the existing database network (`docker network connect
NETWORK backend`) **before starting it**; for a fresh container use `docker create`,
connect the second network, then `docker start`. The `docker run` example assumes
the database is already reachable from `turboea-app`.

Run the gateway on `turboea-app` with the same hardening and environment shown in
`compose.yml`, and connect **only it** to the ingress network. Supply
`NGINX_BACKEND_UPSTREAM=http://backend:8000` and
`NGINX_FRONTEND_UPSTREAM=http://frontend:8080`, or the actual private DNS aliases
if the orchestrator renames containers. Do not add host mappings for frontend,
backend or DB. For example, put just the gateway's environment mapping from
`compose.yml` in an operator-owned `.env.gateway` file and run:

```sh
docker run -d --name gateway --network turboea-app --restart unless-stopped \
  --cap-drop ALL --security-opt no-new-privileges:true \
  --env-file /secure/turbo-ea/.env.gateway \
  --health-cmd 'wget -q -T 4 -O /dev/null http://127.0.0.1:8080/api/health && wget -q -T 4 -O /dev/null http://127.0.0.1:8080/' \
  --health-interval 30s --health-timeout 10s --health-start-period 60s \
  turbo-ea-local/gateway:SOURCE_REVISION
docker network connect INGRESS_NETWORK gateway
```

The gateway env file must explicitly set `TURBO_EA_TLS_ENABLED=false`,
`NGINX_FORWARDED_PROTO=https`, the HTTPS `TURBO_EA_PUBLIC_URL`, the two upstream
URLs, and the appropriate `NGINX_TRUSTED_PROXIES`; do not include database secrets.
Compose already publishes the gateway on
`127.0.0.1:${TURBO_EA_HOST_PORT:-18920}:8080` for a host-based reverse proxy.
For the standalone `docker run` example, add
`-p "127.0.0.1:${TURBO_EA_HOST_PORT:-18920}:8080"` when using that same arrangement;
proxy HTTPS traffic to this local HTTP endpoint.

Backend and frontend images include health checks; gateway health in Compose
checks both `/api/health` and the frontend through the gateway. When running the
gateway independently, configure the same check in the orchestrator. BusyBox wget
and Python urllib are already present, so no health-check dependency is added.
`/api/health` reports process readiness/version after startup; it is not an
ongoing database query or a comprehensive integration check.

## Coolify

Use a Git-based Docker Compose resource with base directory `/` and Compose file
`/deploy/docker/compose.yml`. Include exactly one DB overlay using a Compose
command/file configuration supported by your installed Coolify version. If the UI
only accepts one file, prepare a combined definition outside source control or
use its supported custom Compose commands; verify the final networks and mounts.
Do not paste a secret-expanded `docker compose config` output into a repository.

Assign the HTTPS domain **only to `gateway`, internal port 8080**. In Coolify's
domain field that can be written `https://YOUR_HOST:8080`; public clients still use
normal HTTPS port 443. Keep backend, frontend and database domains empty. Verify
Coolify's generated configuration does not add public routes or attach the backend
to a broadly shared ingress network. For separate Dockerfile resources, select
the root build context `/`, root `/Dockerfile`, and the respective build targets
`backend`, `frontend`, `nginx`; use persistent `/app/data` on backend and private
networks/aliases as described above. If the installed UI lacks target selection,
use the Compose build definitions instead of deploying the Dockerfile's final
`mcp-server` stage by accident. Apply the same capability/privilege restrictions.

## Startup, storage, verification, and limitations

Starting a backend **does write to its configured database**: the existing lifespan
creates/stamps a fresh schema or upgrades an existing one with Alembic, then
initializes built-in configuration. No separate migration entrypoint is needed.
Back up and rehearse against an isolated restored database before a production
upgrade. This change never invokes startup or migrations as validation.

All application files under `/app/data` (uploads, extensions, workspace transfers,
migration snapshots and other runtime artifacts) persist in `backend_data`.
Fresh named volumes inherit UID 1000 ownership from the image. For existing volumes
or bind mounts, arrange that ownership before starting; do not solve permissions
by running the application as root. Back up this volume with PostgreSQL and the
encryption key. Never use `down -v` as an upgrade step.

Before enabling traffic, verify on the deployment host: successful source builds;
all health states; HTTPS redirect/HSTS at ingress; security headers on SPA, API,
DrawIO and embed paths; login's HttpOnly/SameSite/Secure cookie; SSE; uploads;
client-IP attribution and spoofed forwarding headers; no host ports on backend/DB;
and persistence after replacing a container. Initial registration still grants
the first account admin privileges; secure that bootstrap before opening access.

Image tags track the root Dockerfile's existing version policy (Python 3.12,
Node 24, PostgreSQL 18, nginx 1.30.6, DrawIO v31.5.3), and frontend dependencies use
the committed lockfile. **Remaining supply-chain limitation:** upstream Python
dependencies are ranges with no lockfile, base tags can move, and Dockerfile
`apk upgrade` resolves current packages. Source-revision tags identify the source
but do not make rebuilds byte-reproducible. For controlled releases build once,
scan/test, publish to your registry, record and deploy immutable image digests;
do not silently replace the dependency policy with an unverified generated lock.
Full image builds and live routing tests must pass before production use.

Local preparation validation (2026-10-29): all three Compose configurations parsed
successfully (base, external DB, dedicated DB); source targets, absence of public
port bindings/build arguments, runtime hardening, required-variable rejection, network
membership and persistence declarations were checked. Buildx parsed the independent
build definitions, and the existing gateway shell passed `sh -n`. The existing
`test_nginx_headers.py` and `test_nginx_real_ip.py` suites passed **64 tests** using
`--noconftest` and plugin autoload disabled so no application/database fixtures ran
(one harmless warning about the unloaded asyncio plugin's config option).
Docker's Linux daemon was unavailable, so no image was built or started and
nginx runtime syntax/routing was not exercised. No database was contacted.

## Upstream merge boundary

Deployment-specific files are only those in `deploy/docker/`. Shared changes are
small: backend/frontend image health checks in `Dockerfile`, and secret/runtime
exclusions in `.dockerignore`. Root Compose and nginx policy/entrypoint remain
unchanged. Future merges should check stage names, ports, health URLs, required
COPY inputs, `/app/data` ownership, backend env settings, and gateway policies.
New mandatory settings must also be forwarded here; this runtime environment
mapping intentionally does not inherit upstream Compose's image references or
optional services. Do not resolve a merge by copying the upstream application
images into this source-built arrangement.
