# Changelog (Fork)

Changes specific to this fork. For upstream changes, see [CHANGELOG.md](CHANGELOG.md).

## [Unreleased]

### Added
- **Architecture Standards, linked to Principles.** A new managed entity captures the concrete standards that implement your architecture principles (e.g. "Approved RDBMS is PostgreSQL"). Manage them under **Admin → Metamodel → Standards** — each standard can be linked to one or more EA principles — and browse the active set under **GRC → Governance → Standards**. Standards (and their principle links) are included in the workspace export/import bundle.
- **Manage principles and standards inline from GRC → Governance.** Users with the *Metamodel* admin permission now get the full create / edit / activate / delete controls directly on the **GRC → Governance → Principles** and **Standards** sub-tabs — the same management UI as Admin → Metamodel — so governance authors no longer have to switch pages. Users without that permission continue to see the read-only list.
