"""Shared asyncpg TLS configuration for the application and Alembic."""

from __future__ import annotations

import ssl


def database_connect_args(mode: str, root_cert: str = "") -> dict:
    """Configure TLS without silently downgrading a managed connection."""
    if mode not in {"disable", "allow", "prefer", "require", "verify-ca", "verify-full"}:
        raise ValueError("Invalid POSTGRES_SSLMODE")
    if mode in {"verify-ca", "verify-full"}:
        context = ssl.create_default_context(cafile=root_cert or None)
        context.check_hostname = mode == "verify-full"
        return {"ssl": context}
    if root_cert:
        raise ValueError("POSTGRES_SSLROOTCERT requires verify-ca or verify-full")
    return {"ssl": mode}
