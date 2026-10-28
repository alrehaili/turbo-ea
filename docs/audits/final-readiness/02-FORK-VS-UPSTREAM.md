# Fork versus upstream

Baseline fetched read-only on 28 October 2026 using `git fetch https://github.com/vincentmakes/turbo-ea.git main`. This updated Git fetch metadata only; no checkout, merge or application change.

| Baseline | Value |
| --- | --- |
| Fork HEAD | `3287b83fdbf56b419edce0256f35d0fb5bc03d02` — VERSION 2.43.0 |
| Accessible upstream main | `f1b951c8e0716294da46e9c3900506cbd7cc8f0b` — VERSION 2.179.0 |
| Common ancestor | `e69ba711c60fd715c02b3864ee601684557b57f6` |
| `git rev-list --left-right --count HEAD...FETCH_HEAD` | 156 fork-side / 1 upstream-side commits |
| Direct tree diff | 788 files, 203,499 insertions, 22,038 deletions; includes tests, documentation and tooling |

The fork is not 136 functional releases behind: the histories have different version sequences. Upstream history through the common ancestor is incorporated. Claims of missing upstream fixes must be based on commits outside that ancestry.

## Concrete missing change

`f1b951c8` — **MCP: accept extra Host names behind proxies (MCP_ALLOWED_HOSTS), #1324**. Upstream changes `mcp-server/turbo_ea_mcp/config.py` and `server.py`, corresponding tests, environment examples, documentation and Compose forwarding. The implementation adds extra exact Host names to the DNS-rebinding guard; it does not disable the guard or turn those names into allowed origins. Invalid scheme/path entries are warned about.

Impact: MCP connections through a proxy presenting another hostname can receive HTTP 421. Minimum action: selectively backport if the intended MCP proxy needs it, or keep the proxy Host aligned with configured public URLs. **P2 deployment-dependent compatibility concern**, not a blocker when MCP is unused. Validate an approved host succeeds and an arbitrary host remains rejected. The Compose forwarding portion is not a native-deployment blocker; set process environment variables explicitly in native service configuration.

No other upstream-only commits, bug fixes or security corrections exist in this fetched branch comparison. This does not constitute a vulnerability scan of the dependencies or proof that upstream itself has no vulnerabilities.

## Material fork additions, traced to code

| Area | Concrete history and implementation |
| --- | --- |
| NORA profile/program/reference work | `backend/app/services/nora_profile.py`, `nora_program.py`; `api/v1/nora_program.py`, `nora_landscape.py`, `reference_models.py`; six-domain taxonomy and program methodology definitions |
| Current/target and card approval chain | `models/card.py:68`, `services/governance_service.py:37`, `api/v1/cards.py:3130`; tests in `test_governance_approval.py` |
| Cross-surface visibility/cost corrections | `b5f30666` and `backend/app/services/card_read_scope.py`; retained upstream scope implementation and fork integrations |
| Executive reporting | `e7e4848d`, `0ce8920b`, `d12996fa`, `19ac6114`, `481f1238`, `5f52fc81`, `5ff1eb10`, `d9c57d88`; `services/executive/` and executive API modules |
| Benefits register and outcome reporting | `d217f14b`; `models/benefit.py`, `api/v1/benefits.py`, `services/executive/benefits.py` |
| Native developer launcher | `548e2e0b`, `tools/control-panel/ControlPanel.java`; useful tooling, not proof of a supervised production service |
| Arabic/startup performance | `76baf8a3`, `3287b83f`; `main.tsx`, `App.tsx`, lazy inventory import/preview loading |

Dependency declaration differences against fetched upstream: frontend adds `@fontsource/cairo`; backend changes pytest options to block a problematic optional external pytest plugin. Runtime backend dependency declarations otherwise match this upstream baseline. Installed versions were not inventoried or security-scanned. Do not infer dependency safety from matching declarations; freeze a reviewed deployment set.

## Merge and migration considerations

`git diff e69ba711 HEAD --stat -- mcp-server/turbo_ea_mcp/config.py mcp-server/turbo_ea_mcp/server.py` is empty: the two core files touched by the missing fix have no fork changes since the ancestor. A selective backport therefore looks low-conflict in those files; no trial merge was performed. VERSION, CHANGELOG and shared instructions/docs may need deliberate reconciliation. Never replace the fork's VERSION with upstream just to equalize numbers.

Local `alembic heads` reports a single `1175` head. History includes `7ead9e07` merging earlier migration heads. This verifies graph convergence only, not upgrade execution, downgrade safety or compatibility of an upstream database with the fork. Rehearse upgrade against a disposable restored database, including NORA-profile settings, transfer references and executive/benefit records. No database migration was executed in this audit.

Recommendation: retain the fork; backport #1324 only when needed. There is no evidence for a broad upstream merge as a pre-pilot requirement.
