"""Security preparation for Executive Dashboard Phase 1.

Covers the decisions and requirements recorded on 2026-10-24 on top of the
SEC-1..SEC-3 remediation (``test_disclosure_regression.py`` shares its world):

* **S-08** — PPM financial amounts need ``costs.view`` (or a stakeholder role
  on the initiative); the non-financial project indicators stay visible.
* **S-12** — only independently accessible improvement opportunities are
  listed and counted; one whose every linked card is hidden is omitted.
* **Scenario merge** — a merge never modifies a card hidden from the merger,
  nor one the merger has no write permission on.
* **Segment traversal** — segment membership is never derived through a
  hidden card, so its counts cannot disclose that card's neighbourhood.
"""

# ruff: noqa: F811  (`world` is a shared fixture, imported and then requested by name)
from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models.card import Card
from app.models.stakeholder import Stakeholder
from tests.api.test_disclosure_regression import (  # noqa: F401  (fixture)
    NON_ADMIN,
    SECRET,
    _h,
    _ok,
    world,
)
from tests.conftest import (
    auth_headers,
    create_card,
    create_relation_type,
    create_role,
    create_user,
)

# ── S-08: PPM financial amounts ──────────────────────────────────────────


async def _budget_line(client, world, amount=300):
    return await _ok(
        await client.post(
            f"/api/v1/ppm/initiatives/{world['initiative']}/budgets",
            json={"fiscal_year": 2026, "category": "capex", "amount": amount},
            headers=_h(world, "admin"),
        )
    )


async def test_ppm_dashboard_totals_need_costs_view(client, world):
    await _budget_line(client, world)
    full = await _ok(await client.get("/api/v1/reports/ppm/dashboard", headers=_h(world, "full")))
    nocost = await _ok(
        await client.get("/api/v1/reports/ppm/dashboard", headers=_h(world, "nocost"))
    )
    assert full["total_budget"] == 300 and full["costs_restricted"] is False
    assert nocost["total_budget"] is None and nocost["total_actual"] is None
    assert nocost["costs_restricted"] is True
    # Non-financial project indicators are unchanged.
    for key in ("total_initiatives", "by_status", "health_schedule", "health_cost"):
        assert nocost[key] == full[key]


async def test_ppm_budget_lines_redact_amounts_and_refuse_blind_writes(db, client, world):
    line = await _budget_line(client, world)
    path = f"/api/v1/ppm/initiatives/{world['initiative']}/budgets"
    rows = await _ok(await client.get(path, headers=_h(world, "nocost")))
    assert rows[0]["amount"] is None
    assert rows[0]["fiscal_year"] == 2026 and rows[0]["category"] == "capex"
    body = {"fiscal_year": 2027, "category": "opex", "amount": 1}
    assert (await client.post(path, json=body, headers=_h(world, "nocost"))).status_code == 403
    assert (
        await client.patch(
            f"/api/v1/ppm/budgets/{line['id']}", json={"amount": 5}, headers=_h(world, "nocost")
        )
    ).status_code == 403
    assert (
        await client.delete(f"/api/v1/ppm/budgets/{line['id']}", headers=_h(world, "nocost"))
    ).status_code == 403

    # A stakeholder on the initiative sees and edits its money (card cost rule).
    db.add(
        Stakeholder(
            card_id=world["initiative"], user_id=world["users"]["nocost"]["id"], role="responsible"
        )
    )
    await db.commit()
    rows = await _ok(await client.get(path, headers=_h(world, "nocost")))
    assert rows[0]["amount"] == 300


async def test_ppm_cost_lines_and_gantt_rollups_redact_amounts(client, world):
    await _ok(
        await client.post(
            f"/api/v1/ppm/initiatives/{world['initiative']}/costs",
            json={"description": "Licences", "category": "capex", "planned": 70, "actual": 40},
            headers=_h(world, "admin"),
        )
    )
    lines = await _ok(
        await client.get(
            f"/api/v1/ppm/initiatives/{world['initiative']}/costs", headers=_h(world, "nocost")
        )
    )
    assert lines[0]["planned"] is None and lines[0]["actual"] is None
    assert lines[0]["description"] == "Licences"

    full = await _ok(await client.get("/api/v1/reports/ppm/gantt", headers=_h(world, "full")))
    nocost = await _ok(await client.get("/api/v1/reports/ppm/gantt", headers=_h(world, "nocost")))
    assert full[0]["capex_actual"] == 40
    assert nocost[0]["capex_actual"] is None and nocost[0]["capex_planned"] is None


# ── S-12: independently accessible improvement opportunities ─────────────


async def test_opportunity_about_hidden_cards_only_is_omitted_and_uncounted(client, world):
    ah, rh = _h(world, "admin"), _h(world, "restricted")
    hidden_only = await _ok(
        await client.post(
            "/api/v1/improvement-opportunities",
            json={"title": "About the secret", "card_ids": [world["secret"]]},
            headers=ah,
        )
    )
    mixed = await _ok(
        await client.post(
            "/api/v1/improvement-opportunities",
            json={"title": "Mixed", "card_ids": [world["anchor"], world["secret"]]},
            headers=ah,
        )
    )
    unlinked = await _ok(
        await client.post(
            "/api/v1/improvement-opportunities", json={"title": "Unlinked"}, headers=ah
        )
    )
    for o in (hidden_only, mixed, unlinked):
        await _ok(
            await client.patch(
                f"/api/v1/improvement-opportunities/{o['id']}",
                json={"status": "realized"},
                headers=ah,
            )
        )

    listed = {
        o["id"]
        for o in await _ok(await client.get("/api/v1/improvement-opportunities", headers=rh))
    }
    assert hidden_only["id"] not in listed
    assert {mixed["id"], unlinked["id"]} <= listed

    admin_rv = await _ok(
        await client.get("/api/v1/improvement-opportunities/realized-value", headers=ah)
    )
    reader_rv = await _ok(
        await client.get("/api/v1/improvement-opportunities/realized-value", headers=rh)
    )
    assert admin_rv["total_realized"] == 3
    assert reader_rv["total_realized"] == 2

    nora_admin = await _ok(await client.get("/api/v1/nora-program/dashboard", headers=ah))
    nora_reader = await _ok(await client.get("/api/v1/nora-program/dashboard", headers=rh))
    assert str(nora_admin).count("realized") >= 1
    assert sum(nora_reader["opportunities"].values()) == 2
    assert sum(nora_admin["opportunities"].values()) == 3

    # Not there for the reader to edit either — and the row survives.
    resp = await client.patch(
        f"/api/v1/improvement-opportunities/{hidden_only['id']}", json={"title": "x"}, headers=rh
    )
    assert resp.status_code == 404
    admin_list = await _ok(await client.get("/api/v1/improvement-opportunities", headers=ah))
    assert hidden_only["id"] in {o["id"] for o in admin_list}


# ── Scenario merge authorization ─────────────────────────────────────────


async def _card_status(db, card_id) -> str:
    return (
        await db.execute(select(Card.status).where(Card.id == uuid.UUID(str(card_id))))
    ).scalar_one()


async def test_merge_never_modifies_a_hidden_card(db, client, world):
    ah, rh = _h(world, "admin"), _h(world, "restricted")
    scenario = await _ok(await client.post("/api/v1/scenarios", json={"name": "S"}, headers=ah))
    for target in (world["secret"], world["anchor"]):
        await _ok(
            await client.post(
                f"/api/v1/scenarios/{scenario['id']}/changes",
                json={"op": "retire", "target_card_id": target},
                headers=ah,
            )
        )
    result = await _ok(await client.post(f"/api/v1/scenarios/{scenario['id']}/merge", headers=rh))
    assert result["applied"] == 1 and result["conflicts"] == 0
    assert len(result["results"]) == 1
    assert SECRET not in str(result) and world["secret"] not in str(result)
    assert await _card_status(db, world["secret"]) == "ACTIVE"
    assert await _card_status(db, world["anchor"]) == "ARCHIVED"

    # The merge event reaches every reader's activity feed: it counts no
    # withheld change.
    feed = await _ok(await client.get("/api/v1/reports/dashboard", headers=rh))
    # A merge that withheld something is partial: the scenario stays open.
    merged = [e for e in feed["recent_events"] if e["event_type"] == "scenario.merge_partial"]
    assert merged and merged[0]["data"]["applied"] == 1
    assert "withheld" not in str(merged[0]["data"])


async def test_merge_skips_changes_the_merger_may_not_make(db, client, world):
    await create_role(
        db,
        key="noarchive",
        label="No archive",
        permissions={**NON_ADMIN, "inventory.archive": False},
    )
    merger = await create_user(db, email="noarchive@disclosure.test", role="noarchive")
    target = await create_card(db, card_type="Application", name="Keep me")
    target_id = str(target.id)
    await db.commit()
    ah = _h(world, "admin")
    scenario = await _ok(await client.post("/api/v1/scenarios", json={"name": "S"}, headers=ah))
    await _ok(
        await client.post(
            f"/api/v1/scenarios/{scenario['id']}/changes",
            json={"op": "retire", "target_card_id": target_id},
            headers=ah,
        )
    )
    result = await _ok(
        await client.post(f"/api/v1/scenarios/{scenario['id']}/merge", headers=auth_headers(merger))
    )
    assert result["applied"] == 0 and result["forbidden"] == 1
    assert result["results"][0]["outcome"] == "forbidden"
    assert await _card_status(db, target_id) == "ACTIVE"


# ── Segment traversal ────────────────────────────────────────────────────


async def _segment_cards(client, world, role, segment_id):
    body = await _ok(
        await client.get(f"/api/v1/nora-segments/{segment_id}/cards", headers=_h(world, role))
    )
    return {c["id"] for c in body["cards"]}


async def test_segment_rooted_at_a_hidden_card_is_empty_for_the_reader(client, world):
    segment = await _ok(
        await client.post(
            "/api/v1/nora-segments",
            json={"name": "Seg", "root_card_id": world["secret"], "include_related": True},
            headers=_h(world, "admin"),
        )
    )
    admin = await _segment_cards(client, world, "admin", segment["id"])
    reader = await _segment_cards(client, world, "restricted", segment["id"])
    # Admin: the secret and its neighbours. Reader: nothing at all — listing
    # the readable neighbours would reveal what the hidden card relates to.
    assert {world["anchor"], world["beyond"]} <= admin
    assert reader == set()


async def test_segment_descendants_do_not_pass_through_a_hidden_card(db, client, world):
    root = await create_card(db, card_type="Objective", name="Root objective")
    hidden_child = await create_card(
        db, card_type="Secret", name="Hidden middle", parent_id=root.id
    )
    grandchild = await create_card(
        db, card_type="Application", name="Below hidden", parent_id=hidden_child.id
    )
    root_id, grandchild_id = str(root.id), str(grandchild.id)
    await db.commit()
    segment = await _ok(
        await client.post(
            "/api/v1/nora-segments",
            json={"name": "Tree", "root_card_id": root_id, "include_descendants": True},
            headers=_h(world, "admin"),
        )
    )
    admin = await _segment_cards(client, world, "admin", segment["id"])
    reader = await _segment_cards(client, world, "restricted", segment["id"])
    assert grandchild_id in admin
    assert reader == {root_id}


# ── Scenario merge integrity (final integration) ─────────────────────────


async def _scenario_status(client, world, scenario_id) -> str:
    body = await _ok(
        await client.get(f"/api/v1/scenarios/{scenario_id}", headers=_h(world, "admin"))
    )
    return body["status"]


async def test_partial_merge_keeps_the_scenario_open_for_an_authorized_merger(db, client, world):
    ah, rh = _h(world, "admin"), _h(world, "restricted")
    scenario = await _ok(await client.post("/api/v1/scenarios", json={"name": "S"}, headers=ah))
    sid = scenario["id"]
    for target in (world["secret"], world["anchor"]):
        await _ok(
            await client.post(
                f"/api/v1/scenarios/{sid}/changes",
                json={"op": "retire", "target_card_id": target},
                headers=ah,
            )
        )

    partial = await _ok(await client.post(f"/api/v1/scenarios/{sid}/merge", headers=rh))
    assert partial["complete"] is False and partial["applied"] == 1
    assert SECRET not in str(partial) and world["secret"] not in str(partial)
    # Not marked merged: the withheld change is preserved for later.
    assert await _scenario_status(client, world, sid) != "merged"
    assert await _card_status(db, world["secret"]) == "ACTIVE"

    # Someone who may see every card finishes it; what was applied is not
    # re-applied (the anchor, now archived, would otherwise read as a conflict).
    final = await _ok(await client.post(f"/api/v1/scenarios/{sid}/merge", headers=ah))
    assert final["complete"] is True
    assert final["applied"] == 1 and final["conflicts"] == 0
    assert len(final["results"]) == 1
    assert await _card_status(db, world["secret"]) == "ARCHIVED"
    assert await _scenario_status(client, world, sid) == "merged"


async def test_relation_changes_are_recorded_and_need_relations_manage(db, client, world):
    """``scenario_changes.op`` was VARCHAR(8): relation ops could not be saved."""
    await create_relation_type(
        db,
        key="relAppToApp",
        label="feeds",
        source_type_key="Application",
        target_type_key="Application",
    )
    await create_role(
        db,
        key="norelations",
        label="No relations",
        permissions={**NON_ADMIN, "relations.manage": False},
    )
    merger = await create_user(db, email="norel@disclosure.test", role="norelations")
    await db.commit()
    ah = _h(world, "admin")
    sid = (await _ok(await client.post("/api/v1/scenarios", json={"name": "R"}, headers=ah)))["id"]
    change = await client.post(
        f"/api/v1/scenarios/{sid}/changes",
        json={
            "op": "add_relation",
            "payload": {
                "relation_type": "relAppToApp",
                "source_id": world["anchor"],
                "target_id": world["beyond"],
            },
        },
        headers=ah,
    )
    assert change.status_code == 201, change.text
    assert change.json()["op"] == "add_relation"

    refused = await _ok(
        await client.post(f"/api/v1/scenarios/{sid}/merge", headers=auth_headers(merger))
    )
    assert refused["forbidden"] == 1 and refused["complete"] is False
    assert await _scenario_status(client, world, sid) != "merged"

    done = await _ok(await client.post(f"/api/v1/scenarios/{sid}/merge", headers=ah))
    assert done["applied"] == 1 and done["complete"] is True


# ── Executive endpoint ───────────────────────────────────────────────────


async def test_executive_applies_scope_hidden_types_and_cost_rules(client, world):
    admin = await _ok(await client.get("/api/v1/reports/executive", headers=_h(world, "admin")))
    reader = await _ok(
        await client.get("/api/v1/reports/executive", headers=_h(world, "restricted"))
    )
    nocost = await _ok(await client.get("/api/v1/reports/executive", headers=_h(world, "nocost")))

    for body in (admin, reader):
        portfolio = body["portfolio"]
        assert "Retired" not in portfolio["by_type"]  # hidden type, everyone (D-01)
        assert portfolio["total_cards"] == sum(portfolio["by_type"].values())
        assert portfolio["total_cards"] == sum(portfolio["lifecycle"].values())
    assert admin["portfolio"]["by_type"].get("Secret") == 1
    assert "Secret" not in reader["portfolio"]["by_type"]
    assert admin["portfolio"]["total_cards"] - reader["portfolio"]["total_cards"] == 1
    assert SECRET not in str(reader) and world["secret"] not in str(reader)

    # Money: the same rule as the rationalization totals — costs.view itself.
    assert admin["rationalization"]["planned_savings"]["status"] == "ok"
    assert nocost["rationalization"]["planned_savings"]["status"] == "restricted"
    assert "total" not in nocost["rationalization"]["planned_savings"]
    assert nocost["can_view_costs"] is False
