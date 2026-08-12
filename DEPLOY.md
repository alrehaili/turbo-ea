# Deploying the fork to ea.rahimsapp.com

Native install on the VPS — no Docker stack. Backend runs under systemd as user
`turboea` from `/opt/turbo-ea`; PostgreSQL listens on **5433**; the built frontend
is rsynced to the web root. Deploys are manual by choice — there is no CI/CD.

The backend **auto-runs Alembic on startup**, so `systemctl restart turbo-ea`
is what applies pending migrations. There is no separate migrate step in the
normal path.

---

## Before you start — only when the release contains migrations

Check the release notes / `CHANGELOG.md`. If new files landed in
`backend/alembic/versions/`, do these two things first.

**1. Back up.** Some migrations are not reversible by re-running — e.g. `131`
merges duplicate relation rows, `133` rewrites stakeholder role keys.

```bash
sudo -u turboea pg_dump -h localhost -p 5433 -U turboea turboea > ~/turboea-backup-$(date +%F).sql
```

**2. Check the stamped revision matches the chain.** The fork's migrations were
renumbered to the `1125`–`1161` band to reserve `125`+ for upstream. A database
stamped with a pre-renumber id will fail to upgrade on startup.

```bash
cd /opt/turbo-ea/backend && sudo -u turboea /opt/turbo-ea/venv/bin/alembic current
```

If it prints a bare fork-era id that no longer exists under
`backend/alembic/versions/` (e.g. `161`), re-stamp to its renumbered twin
**before restarting the service**:

```bash
cd /opt/turbo-ea/backend && sudo -u turboea /opt/turbo-ea/venv/bin/alembic stamp 1161
```

If it prints an id that does exist in `versions/`, nothing to do — the restart
will upgrade from there.

---

## Backend

```bash
cd /opt/turbo-ea
sudo -u turboea git pull
sudo -u turboea /opt/turbo-ea/venv/bin/pip install -e /opt/turbo-ea/backend
systemctl restart turbo-ea
systemctl status turbo-ea --no-pager
```

Migrations run during that restart. If the service fails to come up after a
migration-bearing release, the traceback is in `journalctl -u turbo-ea -n 100`.

## Frontend

```bash
chown -R turboea:turboea /opt/turbo-ea/frontend/node_modules /opt/turbo-ea/.npm
cd /opt/turbo-ea/frontend
sudo -u turboea npm ci
chown turboea:turboea /opt/turbo-ea/frontend/tsconfig.tsbuildinfo
chown -R turboea:turboea /opt/turbo-ea/frontend/dist
sudo -u turboea npm run build
```

## Publish

```bash
rsync -av --delete /opt/turbo-ea/frontend/dist/ /home/u1102573/domains/ea.rahimsapp.com/public_html/
```

## Verify

```bash
curl -s localhost:8000/api/health
```

The reported version should match `/VERSION` on the deployed commit. Then load
the site and hard-refresh once — `--delete` on the rsync means stale hashed
assets are gone, so a cached `index.html` would 404 on its chunks.

---

## This release (2.27.0) — upstream v2.37.0 → v2.51.0

Migration-bearing: adds `131`–`136` (relation dedupe, diagram publishing,
stakeholder role key camelCasing, relation label sync, process-flow withdrawal,
todo external refs). Run the **Before you start** section.
