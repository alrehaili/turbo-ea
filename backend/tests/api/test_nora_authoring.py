"""Tests for AI-assisted NORA authoring ([FORK] — noraPlan.md WP5.5).

The LLM call is mocked — these cover the endpoint wiring, RBAC, the
not-configured path, and the suggestion-cleaning logic.
"""

from __future__ import annotations

import pytest

import app.api.v1.improvement_opportunities as opp_api
from app.core.permissions import MEMBER_PERMISSIONS, VIEWER_PERMISSIONS
from app.services.nora_authoring import _clean
from tests.conftest import auth_headers, create_role, create_user


def test_clean_clamps_and_tags_source():
    raw = [
        {"title": "Fix data", "description": "d", "domain": "DA", "priority": "high"},
        {"title": "Bad domain", "domain": "ZZ", "priority": "urgent"},  # clamped
        {"description": "no title"},  # dropped
        "not a dict",  # dropped
    ]
    out = _clean(raw, "en")
    assert len(out) == 2
    assert out[0] == {
        "title": "Fix data",
        "description": "d",
        "domain": "DA",
        "priority": "high",
        "source": "ai",
    }
    # Invalid domain/priority fall back to defaults.
    assert out[1]["domain"] == "BA"
    assert out[1]["priority"] == "medium"


def test_clean_non_list_returns_empty():
    assert _clean({"not": "a list"}, "en") == []


@pytest.fixture
async def authoring_env(db):
    await create_role(db, key="admin", label="Admin", permissions={"*": True})
    await create_role(db, key="viewer", label="Viewer", permissions=VIEWER_PERMISSIONS)
    await create_role(db, key="member", label="Member", permissions=MEMBER_PERMISSIONS)
    admin = await create_user(db, email="admin@test.com", role="admin")
    viewer = await create_user(db, email="viewer@test.com", role="viewer")
    await db.flush()
    return {"admin": admin, "viewer": viewer}


class TestAiSuggest:
    async def test_suggest_returns_and_can_commit(self, client, db, authoring_env, monkeypatch):
        async def fake_suggest(_db, locale="en", focus=None):
            return [
                {
                    "title": "Consolidate ERP",
                    "description": "Merge duplicate ERPs",
                    "domain": "AA",
                    "priority": "high",
                    "source": "ai",
                }
            ]

        monkeypatch.setattr(opp_api, "suggest_opportunities", fake_suggest)

        resp = await client.post(
            "/api/v1/improvement-opportunities/ai-suggest",
            json={"locale": "ar"},
            headers=auth_headers(authoring_env["admin"]),
        )
        assert resp.status_code == 200
        sugg = resp.json()["suggestions"]
        assert sugg[0]["title"] == "Consolidate ERP"

        # Committing an accepted suggestion lands it as a proposed, ai-sourced record.
        created = await client.post(
            "/api/v1/improvement-opportunities",
            json={**sugg[0]},
            headers=auth_headers(authoring_env["admin"]),
        )
        assert created.status_code == 201
        assert created.json()["status"] == "proposed"
        assert created.json()["source"] == "ai"

    async def test_not_configured_returns_400(self, client, db, authoring_env, monkeypatch):
        async def fake_suggest(_db, locale="en", focus=None):
            raise ValueError("AI_NOT_CONFIGURED")

        monkeypatch.setattr(opp_api, "suggest_opportunities", fake_suggest)
        resp = await client.post(
            "/api/v1/improvement-opportunities/ai-suggest",
            json={},
            headers=auth_headers(authoring_env["admin"]),
        )
        assert resp.status_code == 400
        assert "not configured" in resp.json()["detail"].lower()

    async def test_viewer_without_grc_manage_forbidden(self, client, db, authoring_env):
        resp = await client.post(
            "/api/v1/improvement-opportunities/ai-suggest",
            json={},
            headers=auth_headers(authoring_env["viewer"]),
        )
        assert resp.status_code == 403
