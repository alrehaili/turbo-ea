"""Managed database TLS must never silently fall back to plaintext."""

import ssl

import pytest

from app.core.database_tls import database_connect_args


@pytest.mark.parametrize("mode", ["disable", "allow", "prefer", "require"])
def test_asyncpg_receives_explicit_tls_mode(mode):
    assert database_connect_args(mode) == {"ssl": mode}


@pytest.mark.parametrize("mode,hostname", [("verify-ca", False), ("verify-full", True)])
def test_verified_tls_requires_a_trusted_certificate(mode, hostname):
    context = database_connect_args(mode)["ssl"]
    assert isinstance(context, ssl.SSLContext)
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is hostname


def test_custom_ca_load_errors_are_not_ignored(tmp_path):
    with pytest.raises(FileNotFoundError):
        database_connect_args("verify-full", str(tmp_path / "missing-ca.pem"))


@pytest.mark.parametrize("mode", ["", "typo", "VERIFY-FULL"])
def test_unknown_modes_fail_closed(mode):
    with pytest.raises(ValueError, match="POSTGRES_SSLMODE"):
        database_connect_args(mode)


def test_custom_ca_cannot_be_silently_ignored():
    with pytest.raises(ValueError, match="POSTGRES_SSLROOTCERT"):
        database_connect_args("require", "some-ca.pem")
