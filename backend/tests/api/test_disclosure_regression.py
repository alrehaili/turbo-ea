"""Disclosure regression suite for the security remediation track (SEC-1..SEC-3).

The sentinel sweep (``test_read_scope_sentinel_sweep.py``) proves that no GET
route returns a hidden card's name or id. This file pins what that sweep
cannot express:

* **Counts and charts** (D-01) — a dashboard total is the sum of its own
  breakdown and leaves out both cards the reader may not see and hidden card
  types, for every reader, admin included.
* **Money** — ``costs.view`` (or a stakeholder role on the card) gates every
  cost figure; portfolio totals need ``costs.view`` itself.
* **Record-specific redact / omit** (D-30) — a record that stays meaningful
  keeps its row with the hidden link redacted, a record about exactly one
  hidden card is omitted, writes keep the hidden links the caller never saw,
  and nothing is ever deleted.
* **Write paths** — a write naming a hidden card is a 404, never a 403, so
  the answer never confirms the card exists.
* **Whole-landscape analytics** — maturity indicators refuse a restricted
  reader rather than computing over a partial landscape.
* **Traversals** — impact and service traceability never route *through* a
  hidden card to the cards beyond it.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.core.permissions import ALL_APP_PERMISSION_KEYS
from app.models.card_type import CardType
from app.models.stakeholder import Stakeholder
from app.services.permission_service import PermissionService
from tests.conftest import (
    auth_headers,
    create_card,
    create_card_type,
    create_relation,
    create_relation_type,
    create_role,
    create_stakeholder_role_def,
    create_user,
)

SECRET = "ZZDISCLOSURESECRET"

NON_ADMIN = {k: True for k in ALL_APP_PERMISSION_KEYS if not k.startswith("admin.")}


@pytest.fixture
async def world(db, client):
    await create_role(db, key="admin", label="Admin", permissions={"*": True})
    await create_role(db, key="full", label="Full", permissions=NON_ADMIN)
    await create_role(db, key="restricted", label="Restricted", permissions=NON_ADMIN)
    await create_role(
        db, key="nocost", label="No cost", permissions={**NON_ADMIN, "costs.view": False}
    )
    for key in ("Application", "Objective", "Secret"):
        await create_card_type(db, key=key, label=key)
    await create_card_type(
        db,
        key="Initiative",
        label="Initiative",
        fields_schema=[
            {
                "section": "Costs",
                "fields": [
                    {"key": "costBudget", "label": "Budget", "type": "cost"},
                    {"key": "costActual", "label": "Actual", "type": "cost"},
                ],
            }
        ],
    )
    # A metamodel type an admin has hidden: excluded from every dashboard (D-01).
    await create_card_type(db, key="Retired", label="Retired", is_hidden=True)
    for key, src, tgt in (
        ("relAppToSecret", "Application", "Secret"),
        ("relSecretToApp", "Secret", "Application"),
        ("relInitiativeToObjective", "Initiative", "Objective"),
    ):
        await create_relation_type(
            db, key=key, label="uses", source_type_key=src, target_type_key=tgt
        )
    await create_stakeholder_role_def(
        db, card_type_key="Initiative", key="responsible", permissions={"card.view": True}
    )

    users = {
        role: await create_user(db, email=f"{role}@disclosure.test", role=role)
        for role in ("admin", "full", "restricted", "nocost")
    }

    anchor = await create_card(
        db, card_type="Application", name="Anchor", approval_status="APPROVED"
    )
    secret = await create_card(db, card_type="Secret", name=SECRET)
    beyond = await create_card(db, card_type="Application", name="Beyond")
    await create_card(db, card_type="Retired", name="Hidden type card")
    # anchor -> secret -> beyond: the only path from anchor to beyond runs
    # through the hidden card.
    await create_relation(db, type_key="relAppToSecret", source_id=anchor.id, target_id=secret.id)
    await create_relation(db, type_key="relSecretToApp", source_id=secret.id, target_id=beyond.id)

    objective = await create_card(db, card_type="Objective", name="Objective")
    initiative = await create_card(
        db,
        card_type="Initiative",
        name="Initiative",
        attributes={"costBudget": 1000, "costActual": 400},
    )
    await create_relation(
        db, type_key="relInitiativeToObjective", source_id=initiative.id, target_id=objective.id
    )

    # The restricted role may not View the Secret type.
    ct = (await db.execute(select(CardType).where(CardType.key == "Secret"))).scalar_one()
    ct.role_permissions = {"restricted": {"inventory.view": False}}
    await db.commit()
    PermissionService.invalidate_type_permission_cache()

    # Plain ids: a request that rolls the session back (NORA's `_safe`
    # subsections) expires ORM instances, and touching one then is IO.
    return {
        "users": {role: {"id": u.id, "headers": auth_headers(u)} for role, u in users.items()},
        "anchor": str(anchor.id),
        "secret": str(secret.id),
        "beyond": str(beyond.id),
        "objective": str(objective.id),
        "initiative": initiative.id,
    }


def _h(world, role):
    return world["users"][role]["headers"]


async def _ok(resp):
    assert resp.status_code < 400, f"{resp.status_code} {resp.text}"
    return resp.json()


# ── D-01: counts and charts ──────────────────────────────────────────────


async def test_dashboard_counts_exclude_hidden_cards_and_hidden_types(client, world):
    admin = await _ok(await client.get("/api/v1/reports/dashboard", headers=_h(world, "admin")))
    reader = await _ok(
        await client.get("/api/v1/reports/dashboard", headers=_h(world, "restricted"))
    )

    # A hidden metamodel type is out for everyone, admin included.
    assert "Retired" not in admin["by_type"]
    assert "Retired" not in reader["by_type"]
    # The restricted reader sees no trace of the type it may not View.
    assert admin["by_type"].get("Secret") == 1
    assert "Secret" not in reader["by_type"]
    # Every aggregate agrees with its own breakdown — no hidden remainder.
    for body in (admin, reader):
        assert body["total_cards"] == sum(body["by_type"].values())
        assert body["total_cards"] == sum(body["approval_statuses"].values())
        assert body["total_cards"] == sum(body["data_quality_distribution"].values())
        assert body["total_cards"] == sum(body["lifecycle_distribution"].values())
    assert admin["total_cards"] - reader["total_cards"] == 1
    # A landscape-wide trend compared against partial totals would expose the
    # hidden cards as a delta.
    assert reader["trends"] is None


async def test_kpi_snapshot_counts_exclude_hidden_types(db, world):
    from app.services.kpi_snapshot_service import compute_current_kpis

    kpis = await compute_current_kpis(db)
    # Anchor, Secret, Beyond, Objective, Initiative — never the Retired card.
    assert kpis["total_cards"] == 5


async def test_nora_dashboard_is_scoped(client, world):
    admin = await client.get("/api/v1/nora-program/dashboard", headers=_h(world, "admin"))
    reader = await client.get("/api/v1/nora-program/dashboard", headers=_h(world, "restricted"))
    assert admin.status_code == reader.status_code == 200
    assert SECRET not in reader.text
    assert world["secret"] not in reader.text


# ── Money ────────────────────────────────────────────────────────────────


async def test_strategy_map_hides_money_without_costs_view(client, world):
    full = await _ok(await client.get("/api/v1/reports/strategy-map", headers=_h(world, "full")))
    nocost = await _ok(
        await client.get("/api/v1/reports/strategy-map", headers=_h(world, "nocost"))
    )
    assert full["summary"]["total_budget"] == 1000
    assert full["summary"]["costs_restricted"] is False
    assert nocost["summary"]["total_budget"] is None
    assert nocost["summary"]["total_actual"] is None
    assert nocost["summary"]["costs_restricted"] is True
    row = nocost["objectives"][0]["initiatives"][0]
    assert row["budget"] is None and row["actual"] is None
    # The structure itself is unchanged.
    assert nocost["summary"]["initiative_count"] == full["summary"]["initiative_count"]


async def test_strategy_map_stakeholder_sees_own_initiative_costs(db, client, world):
    db.add(
        Stakeholder(
            card_id=world["initiative"],
            user_id=world["users"]["nocost"]["id"],
            role="responsible",
        )
    )
    await db.commit()
    body = await _ok(await client.get("/api/v1/reports/strategy-map", headers=_h(world, "nocost")))
    row = body["objectives"][0]["initiatives"][0]
    assert row["budget"] == 1000
    # A portfolio total sums many cards: the per-card bypass does not unlock it.
    assert body["summary"]["total_budget"] is None


async def test_gantt_redacts_card_cost_fields_without_costs_view(db, client, world):
    full = await _ok(await client.get("/api/v1/reports/ppm/gantt", headers=_h(world, "full")))
    nocost = await _ok(await client.get("/api/v1/reports/ppm/gantt", headers=_h(world, "nocost")))
    assert full[0]["cost_budget"] == 1000
    assert nocost[0]["cost_budget"] is None and nocost[0]["cost_actual"] is None

    db.add(
        Stakeholder(
            card_id=world["initiative"],
            user_id=world["users"]["nocost"]["id"],
            role="responsible",
        )
    )
    await db.commit()
    bypass = await _ok(await client.get("/api/v1/reports/ppm/gantt", headers=_h(world, "nocost")))
    assert bypass[0]["cost_budget"] == 1000


async def test_rationalization_money_and_hidden_decisions(client, world):
    ah = _h(world, "admin")
    assessment = await _ok(
        await client.post(
            "/api/v1/rationalization/assessments",
            json={"name": "R", "status": "active", "target_savings": 500},
            headers=ah,
        )
    )
    aid = assessment["id"]
    for body in (
        {"card_id": world["secret"], "time_decision": "eliminate", "planned_savings": 50},
        {
            "card_id": world["anchor"],
            "time_decision": "migrate",
            "successor_id": world["secret"],
            "planned_savings": 70,
            "annual_cost": 90,
        },
    ):
        await _ok(
            await client.post(
                f"/api/v1/rationalization/assessments/{aid}/decisions", json=body, headers=ah
            )
        )

    admin = await _ok(await client.get(f"/api/v1/rationalization/assessments/{aid}", headers=ah))
    assert admin["summary"]["decision_count"] == 2
    assert admin["summary"]["planned_savings_total"] == 120

    reader = await _ok(
        await client.get(
            f"/api/v1/rationalization/assessments/{aid}", headers=_h(world, "restricted")
        )
    )
    # D-30: the decision about the hidden card is omitted; the decision that
    # only names it as successor stays, with the successor redacted.
    assert reader["summary"]["decision_count"] == 1
    assert reader["decisions"][0]["card"]["id"] == world["anchor"]
    assert reader["decisions"][0]["successor"] is None
    # Totals cover only what the reader was shown.
    assert reader["summary"]["planned_savings_total"] == 70

    nocost = await _ok(
        await client.get(f"/api/v1/rationalization/assessments/{aid}", headers=_h(world, "nocost"))
    )
    assert nocost["target_savings"] is None
    assert nocost["summary"]["planned_savings_total"] is None
    assert all(
        d["annual_cost"] is None and d["planned_savings"] is None for d in nocost["decisions"]
    )


async def test_card_exports_redact_money_and_hidden_cards(client, world):
    params = {"types": "Initiative,Secret"}
    full = await _ok(
        await client.get("/api/v1/cards/export/json", params=params, headers=_h(world, "full"))
    )
    nocost = await _ok(
        await client.get("/api/v1/cards/export/json", params=params, headers=_h(world, "nocost"))
    )
    by_type = {c["type"]: c for c in full}
    assert by_type["Initiative"]["attributes"]["costBudget"] == 1000
    initiative = next(c for c in nocost if c["type"] == "Initiative")
    assert "costBudget" not in initiative["attributes"]
    assert "costActual" not in initiative["attributes"]

    csv_nocost = await client.get(
        "/api/v1/cards/export/csv", params={"type": "Initiative"}, headers=_h(world, "nocost")
    )
    assert csv_nocost.status_code == 200 and "1000" not in csv_nocost.text

    for path, qp in (
        ("/api/v1/cards/export/json", params),
        ("/api/v1/cards/export/csv", {"type": "Secret"}),
    ):
        resp = await client.get(path, params=qp, headers=_h(world, "restricted"))
        assert SECRET not in resp.text and world["secret"] not in resp.text


# ── D-30: redact / omit / keep hidden on write ───────────────────────────


async def test_arb_review_of_hidden_subject_is_omitted_not_deleted(client, world):
    ah = _h(world, "admin")
    review = await _ok(
        await client.post(
            "/api/v1/arb",
            json={"title": "Review", "subject_card_id": world["secret"]},
            headers=ah,
        )
    )
    rh = _h(world, "restricted")
    listing = await _ok(await client.get("/api/v1/arb", headers=rh))
    rows = listing if isinstance(listing, list) else listing.get("items", [])
    assert review["id"] not in {r["id"] for r in rows}
    assert (await client.get(f"/api/v1/arb/{review['id']}", headers=rh)).status_code == 404
    # Still there for a reader who may see the subject.
    assert (await client.get(f"/api/v1/arb/{review['id']}", headers=ah)).status_code == 200


async def test_write_naming_a_hidden_card_is_404(client, world):
    rh = _h(world, "restricted")
    sid = world["secret"]
    resp = await client.post("/api/v1/arb", json={"title": "R", "subject_card_id": sid}, headers=rh)
    assert resp.status_code == 404

    standard = await _ok(
        await client.post("/api/v1/tech-standards", json={"name": "S"}, headers=_h(world, "admin"))
    )
    resp = await client.post(
        f"/api/v1/tech-standards/{standard['id']}/exceptions",
        json={"card_id": sid, "justification": "x"},
        headers=rh,
    )
    assert resp.status_code == 404

    scenario = await _ok(await client.post("/api/v1/scenarios", json={"name": "S"}, headers=rh))
    resp = await client.post(
        f"/api/v1/scenarios/{scenario['id']}/changes",
        json={"op": "retire", "target_card_id": sid},
        headers=rh,
    )
    assert resp.status_code == 404


async def test_roadmap_milestone_keeps_a_hidden_initiative_on_update(client, world):
    ah, rh = _h(world, "admin"), _h(world, "restricted")
    roadmap = await _ok(
        await client.post(
            "/api/v1/roadmaps",
            json={"name": "R", "config": {"type": "Application"}},
            headers=ah,
        )
    )
    sid = world["secret"]
    milestone = await _ok(
        await client.post(
            f"/api/v1/roadmaps/{roadmap['id']}/milestones",
            json={"label": "M", "target_date": "2027-01-01", "initiative_id": sid},
            headers=ah,
        )
    )
    shown = await _ok(await client.get(f"/api/v1/roadmaps/{roadmap['id']}", headers=rh))
    assert sid not in str(shown)  # redacted, not omitted
    assert milestone["id"] in str(shown)

    # The reader saw `initiative_id: null` and sends it back with an edit.
    await _ok(
        await client.patch(
            f"/api/v1/roadmaps/milestones/{milestone['id']}",
            json={"label": "M2", "target_date": "2027-01-01", "initiative_id": None},
            headers=rh,
        )
    )
    again = await _ok(await client.get(f"/api/v1/roadmaps/{roadmap['id']}", headers=ah))
    assert sid in str(again)
    assert "M2" in str(again)


async def test_improvement_opportunity_keeps_hidden_cards_on_update(client, world):
    ah, rh = _h(world, "admin"), _h(world, "restricted")
    aid, sid = world["anchor"], world["secret"]
    opp = await _ok(
        await client.post(
            "/api/v1/improvement-opportunities",
            json={"title": "O", "card_ids": [aid, sid]},
            headers=ah,
        )
    )
    shown = await _ok(await client.get("/api/v1/improvement-opportunities", headers=rh))
    rows = shown if isinstance(shown, list) else shown.get("items", [])
    mine = next(r for r in rows if r["id"] == opp["id"])
    assert [c["id"] for c in mine["cards"]] == [aid]

    # Replacing the set with what the reader saw must not drop the hidden card.
    await _ok(
        await client.patch(
            f"/api/v1/improvement-opportunities/{opp['id']}",
            json={"card_ids": [aid]},
            headers=rh,
        )
    )
    after = await _ok(await client.get("/api/v1/improvement-opportunities", headers=ah))
    rows = after if isinstance(after, list) else after.get("items", [])
    mine = next(r for r in rows if r["id"] == opp["id"])
    assert {c["id"] for c in mine["cards"]} == {aid, sid}


# ── Whole-landscape analytics ────────────────────────────────────────────


async def test_maturity_indicators_refuse_a_restricted_reader(client, world):
    assert (
        await client.get("/api/v1/maturity/indicators", headers=_h(world, "full"))
    ).status_code == 200
    assert (
        await client.get("/api/v1/maturity/indicators", headers=_h(world, "restricted"))
    ).status_code == 403


async def test_opportunity_ai_suggest_refuses_a_restricted_reader(client, world):
    """The prompt is built from every card: a restricted reader is refused
    before any landscape read (403), while an unrestricted one gets past the
    scope gate (here to "AI is not configured", 400)."""
    path = "/api/v1/improvement-opportunities/ai-suggest"
    assert (await client.post(path, json={}, headers=_h(world, "restricted"))).status_code == 403
    assert (await client.post(path, json={}, headers=_h(world, "full"))).status_code == 400


# ── Traversals ───────────────────────────────────────────────────────────


async def test_impact_of_a_hidden_card_is_404(client, world):
    resp = await client.get(
        "/api/v1/reports/impact",
        params={"card_id": world["secret"]},
        headers=_h(world, "restricted"),
    )
    assert resp.status_code == 404


async def test_impact_does_not_route_through_a_hidden_card(client, world):
    params = {"card_id": world["anchor"], "depth": 2}
    admin = await client.get("/api/v1/reports/impact", params=params, headers=_h(world, "admin"))
    reader = await client.get(
        "/api/v1/reports/impact", params=params, headers=_h(world, "restricted")
    )
    assert admin.status_code == reader.status_code == 200
    assert "Beyond" in admin.text  # reachable via the hidden card
    assert "Beyond" not in reader.text and SECRET not in reader.text


async def test_service_traceability_does_not_route_through_a_hidden_card(client, world):
    params = {"card_id": world["anchor"], "depth": 2}
    admin = await client.get(
        "/api/v1/reports/service-traceability", params=params, headers=_h(world, "admin")
    )
    reader = await client.get(
        "/api/v1/reports/service-traceability", params=params, headers=_h(world, "restricted")
    )
    assert admin.status_code == reader.status_code == 200
    assert "Beyond" in admin.text
    assert "Beyond" not in reader.text and SECRET not in reader.text
    hidden_root = await client.get(
        "/api/v1/reports/service-traceability",
        params={"card_id": world["secret"]},
        headers=_h(world, "restricted"),
    )
    assert hidden_root.status_code == 404


async def test_unknown_card_and_hidden_card_answer_alike(client, world):
    rh = _h(world, "restricted")
    hidden = await client.get(
        "/api/v1/reports/impact", params={"card_id": world["secret"]}, headers=rh
    )
    missing = await client.get(
        "/api/v1/reports/impact", params={"card_id": str(uuid.uuid4())}, headers=rh
    )
    assert hidden.status_code == missing.status_code == 404
