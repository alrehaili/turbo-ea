"""Integration tests for the /reports endpoints."""

from __future__ import annotations

import pytest

from tests.conftest import (
    auth_headers,
    create_card,
    create_card_type,
    create_relation,
    create_relation_type,
    create_role,
    create_user,
)


@pytest.fixture
async def reports_env(db):
    """Prerequisite data for report tests."""
    await create_role(db, key="admin", label="Admin", permissions={"*": True})
    await create_role(
        db,
        key="viewer",
        label="Viewer",
        permissions={
            "reports.ea_dashboard": True,
            "inventory.view": True,
        },
    )
    await create_role(
        db,
        key="noreports",
        label="No Reports",
        permissions={"inventory.view": True},
    )
    await create_card_type(
        db,
        key="Application",
        label="Application",
        fields_schema=[
            {
                "section": "General",
                "fields": [
                    {
                        "key": "costTotalAnnual",
                        "label": "Annual Cost",
                        "type": "cost",
                        "weight": 1,
                    },
                ],
            }
        ],
    )
    admin = await create_user(db, email="admin@test.com", role="admin")
    viewer = await create_user(db, email="viewer@test.com", role="viewer")
    noreports = await create_user(db, email="noreports@test.com", role="noreports")
    return {
        "admin": admin,
        "viewer": viewer,
        "noreports": noreports,
    }


class TestDashboard:
    async def test_dashboard_empty(self, client, db, reports_env):
        """Dashboard returns valid structure with no cards."""
        admin = reports_env["admin"]
        resp = await client.get(
            "/api/v1/reports/dashboard",
            headers=auth_headers(admin),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_cards"] == 0
        assert data["by_type"] == {}
        assert data["avg_data_quality"] == 0
        assert "approval_statuses" in data
        assert "data_quality_distribution" in data
        assert "lifecycle_distribution" in data
        assert "recent_events" in data

    async def test_dashboard_with_cards(self, client, db, reports_env):
        """Dashboard counts cards by type correctly."""
        admin = reports_env["admin"]
        await create_card(
            db,
            card_type="Application",
            name="App A",
            user_id=admin.id,
            data_quality=80.0,
        )
        await create_card(
            db,
            card_type="Application",
            name="App B",
            user_id=admin.id,
            data_quality=40.0,
        )
        resp = await client.get(
            "/api/v1/reports/dashboard",
            headers=auth_headers(admin),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_cards"] == 2
        assert data["by_type"]["Application"] == 2
        assert data["avg_data_quality"] == 60.0

    async def test_dashboard_data_quality_distribution(self, client, db, reports_env):
        """Data quality distribution buckets are populated."""
        admin = reports_env["admin"]
        await create_card(
            db,
            card_type="Application",
            name="Low DQ",
            user_id=admin.id,
            data_quality=10.0,
        )
        await create_card(
            db,
            card_type="Application",
            name="High DQ",
            user_id=admin.id,
            data_quality=90.0,
        )
        resp = await client.get(
            "/api/v1/reports/dashboard",
            headers=auth_headers(admin),
        )
        assert resp.status_code == 200
        dist = resp.json()["data_quality_distribution"]
        assert dist["0-25"] >= 1
        assert dist["75-100"] >= 1

    async def test_dashboard_viewer_can_access(self, client, db, reports_env):
        """Users with reports.ea_dashboard permission can view."""
        viewer = reports_env["viewer"]
        resp = await client.get(
            "/api/v1/reports/dashboard",
            headers=auth_headers(viewer),
        )
        assert resp.status_code == 200

    async def test_dashboard_forbidden_without_permission(self, client, db, reports_env):
        """Users without reports.ea_dashboard get 403."""
        noreports = reports_env["noreports"]
        resp = await client.get(
            "/api/v1/reports/dashboard",
            headers=auth_headers(noreports),
        )
        assert resp.status_code == 403

    async def test_dashboard_unauthenticated(self, client, db, reports_env):
        """No auth token returns 401."""
        resp = await client.get("/api/v1/reports/dashboard")
        assert resp.status_code == 401

    async def test_dashboard_trends_no_snapshot(self, client, db, reports_env):
        """With no historical snapshot, trends return nulls and snapshot_available=False."""
        admin = reports_env["admin"]
        await create_card(
            db,
            card_type="Application",
            name="App",
            user_id=admin.id,
            data_quality=80.0,
        )
        resp = await client.get(
            "/api/v1/reports/dashboard",
            headers=auth_headers(admin),
        )
        assert resp.status_code == 200
        trends = resp.json()["trends"]
        assert trends["snapshot_available"] is False
        assert trends["snapshot_date"] is None
        for key in ("total_cards", "avg_data_quality", "approved_count", "broken_count"):
            assert trends[key]["previous"] is None
            assert trends[key]["delta_pct"] is None
            assert trends[key]["delta_abs"] is None
            assert trends[key]["current"] is not None

    async def test_dashboard_trends_with_snapshot(self, client, db, reports_env):
        """A 30-day-old snapshot drives a real delta_pct in the response."""
        from datetime import datetime, timedelta, timezone

        from app.models.kpi_snapshot import KpiSnapshot

        admin = reports_env["admin"]
        # Two ACTIVE cards now: total_cards = 2, avg_data_quality = 60.
        await create_card(
            db,
            card_type="Application",
            name="App A",
            user_id=admin.id,
            data_quality=80.0,
            approval_status="APPROVED",
        )
        await create_card(
            db,
            card_type="Application",
            name="App B",
            user_id=admin.id,
            data_quality=40.0,
        )
        baseline_date = datetime.now(timezone.utc).date() - timedelta(days=30)
        db.add(
            KpiSnapshot(
                snapshot_date=baseline_date,
                total_cards=1,
                avg_data_quality=50.0,
                approved_count=0,
                broken_count=0,
            )
        )
        await db.commit()

        resp = await client.get(
            "/api/v1/reports/dashboard",
            headers=auth_headers(admin),
        )
        assert resp.status_code == 200
        trends = resp.json()["trends"]
        assert trends["snapshot_available"] is True
        assert trends["snapshot_date"] == baseline_date.isoformat()
        assert trends["comparison_days"] == 30
        # 1 -> 2 cards is +100 %, +1 absolute.
        assert trends["total_cards"]["current"] == 2
        assert trends["total_cards"]["previous"] == 1
        assert trends["total_cards"]["delta_pct"] == 100.0
        assert trends["total_cards"]["delta_abs"] == 1
        # 50 -> 60 % avg dq is +20 %, +10.0 abs points.
        assert trends["avg_data_quality"]["delta_pct"] == 20.0
        assert trends["avg_data_quality"]["delta_abs"] == 10.0

    async def test_dashboard_trends_zero_previous(self, client, db, reports_env):
        """When previous == 0 and current > 0 we return delta_pct=None to avoid div-by-zero."""
        from datetime import datetime, timedelta, timezone

        from app.models.kpi_snapshot import KpiSnapshot

        admin = reports_env["admin"]
        await create_card(
            db,
            card_type="Application",
            name="App",
            user_id=admin.id,
            approval_status="APPROVED",
        )
        baseline_date = datetime.now(timezone.utc).date() - timedelta(days=30)
        db.add(
            KpiSnapshot(
                snapshot_date=baseline_date,
                total_cards=0,
                avg_data_quality=0.0,
                approved_count=0,
                broken_count=0,
            )
        )
        await db.commit()

        resp = await client.get(
            "/api/v1/reports/dashboard",
            headers=auth_headers(admin),
        )
        assert resp.status_code == 200
        trends = resp.json()["trends"]
        assert trends["snapshot_available"] is True
        assert trends["approved_count"]["current"] == 1
        assert trends["approved_count"]["previous"] == 0
        assert trends["approved_count"]["delta_pct"] is None
        # Absolute delta is still meaningful even when previous == 0.
        assert trends["approved_count"]["delta_abs"] == 1


class TestChangeImpact:
    """Change Impact Workbench — /reports/impact blast-radius engine."""

    @pytest.fixture
    async def impact_env(self, db, reports_env):
        """Center Application -> Interface -> ITComponent chain across layers."""
        await create_card_type(
            db, key="Interface", label="Interface", category="Application & Data"
        )
        await create_card_type(
            db, key="ITComponent", label="IT Component", category="Technical Architecture"
        )
        # Application type from reports_env has no category; give it one.
        from sqlalchemy import update

        from app.models.card_type import CardType

        await db.execute(
            update(CardType)
            .where(CardType.key == "Application")
            .values(category="Application & Data")
        )
        await create_relation_type(
            db,
            key="relAppToInterface",
            label="uses",
            reverse_label="used by",
            source_type_key="Application",
            target_type_key="Interface",
        )
        await create_relation_type(
            db,
            key="relInterfaceToITC",
            label="runs on",
            reverse_label="hosts",
            source_type_key="Interface",
            target_type_key="ITComponent",
        )
        admin = reports_env["admin"]
        app = await create_card(
            db,
            card_type="Application",
            name="Core App",
            user_id=admin.id,
            attributes={"businessCriticality": "mission_critical"},
        )
        iface = await create_card(db, card_type="Interface", name="Sync API", user_id=admin.id)
        itc = await create_card(db, card_type="ITComponent", name="Postgres", user_id=admin.id)
        await create_relation(
            db, type_key="relAppToInterface", source_id=app.id, target_id=iface.id
        )
        await create_relation(
            db, type_key="relInterfaceToITC", source_id=iface.id, target_id=itc.id
        )
        return {**reports_env, "app": app, "iface": iface, "itc": itc}

    async def test_impact_blast_radius_grouped_by_layer(self, client, db, impact_env):
        admin = impact_env["admin"]
        resp = await client.get(
            f"/api/v1/reports/impact?card_id={impact_env['app'].id}&change_type=retire&depth=2",
            headers=auth_headers(admin),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["center"]["name"] == "Core App"
        assert data["change_type"] == "retire"
        # Interface (depth 1) + ITComponent (depth 2) both reachable.
        assert data["summary"]["total_affected"] == 2
        names = {row["name"]: row for row in data["affected"]}
        assert names["Sync API"]["depth"] == 1
        assert names["Postgres"]["depth"] == 2
        # ITComponent path runs back through the interface.
        assert names["Postgres"]["path"] == ["Sync API", "Postgres"]
        assert "Technical Architecture" in data["summary"]["by_layer"]

    async def test_impact_depth_limits_walk(self, client, db, impact_env):
        admin = impact_env["admin"]
        resp = await client.get(
            f"/api/v1/reports/impact?card_id={impact_env['app'].id}&depth=1",
            headers=auth_headers(admin),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["total_affected"] == 1
        assert data["affected"][0]["name"] == "Sync API"

    async def test_impact_unknown_card_404(self, client, db, impact_env):
        admin = impact_env["admin"]
        resp = await client.get(
            "/api/v1/reports/impact?card_id=00000000-0000-0000-0000-000000000000",
            headers=auth_headers(admin),
        )
        assert resp.status_code == 404

    async def test_impact_requires_permission(self, client, db, impact_env):
        noreports = impact_env["noreports"]
        resp = await client.get(
            f"/api/v1/reports/impact?card_id={impact_env['app'].id}",
            headers=auth_headers(noreports),
        )
        assert resp.status_code == 403


class TestStrategyMap:
    """Strategy-to-Execution — /reports/strategy-map traversal."""

    @pytest.fixture
    async def strategy_env(self, db, reports_env):
        for key, label in [
            ("Objective", "Objective"),
            ("BusinessCapability", "Business Capability"),
            ("Initiative", "Initiative"),
        ]:
            await create_card_type(db, key=key, label=label)
        await create_relation_type(
            db,
            key="relObjectiveToBC",
            source_type_key="Objective",
            target_type_key="BusinessCapability",
        )
        await create_relation_type(
            db,
            key="relInitiativeToObjective",
            source_type_key="Initiative",
            target_type_key="Objective",
        )
        await create_relation_type(
            db,
            key="relInitiativeToApp",
            source_type_key="Initiative",
            target_type_key="Application",
        )
        admin = reports_env["admin"]
        obj = await create_card(
            db,
            card_type="Objective",
            name="Grow EU revenue",
            user_id=admin.id,
            attributes={"kpi": "+20% ARR"},
        )
        cap = await create_card(
            db, card_type="BusinessCapability", name="Order Management", user_id=admin.id
        )
        init = await create_card(
            db,
            card_type="Initiative",
            name="ERP Rollout",
            user_id=admin.id,
            attributes={"costBudget": 1000, "costActual": 250},
        )
        app = await create_card(db, card_type="Application", name="NexaCore ERP", user_id=admin.id)
        await create_relation(db, type_key="relObjectiveToBC", source_id=obj.id, target_id=cap.id)
        await create_relation(
            db, type_key="relInitiativeToObjective", source_id=init.id, target_id=obj.id
        )
        await create_relation(
            db, type_key="relInitiativeToApp", source_id=init.id, target_id=app.id
        )
        return reports_env

    async def test_strategy_map_chain(self, client, db, strategy_env):
        admin = strategy_env["admin"]
        resp = await client.get("/api/v1/reports/strategy-map", headers=auth_headers(admin))
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["objective_count"] == 1
        assert data["summary"]["initiative_count"] == 1
        assert data["summary"]["application_count"] == 1
        assert data["summary"]["total_budget"] == 1000
        obj = data["objectives"][0]
        assert obj["name"] == "Grow EU revenue"
        assert obj["kpi"] == "+20% ARR"
        assert obj["capabilities"][0]["name"] == "Order Management"
        init = obj["initiatives"][0]
        assert init["name"] == "ERP Rollout"
        assert init["budget"] == 1000
        assert init["applications"][0]["name"] == "NexaCore ERP"

    async def test_strategy_map_requires_permission(self, client, db, strategy_env):
        noreports = strategy_env["noreports"]
        resp = await client.get("/api/v1/reports/strategy-map", headers=auth_headers(noreports))
        assert resp.status_code == 403


class TestFreshness:
    """Repository Freshness View — /reports/freshness + /cards/{id}/confirm."""

    async def test_confirm_stamps_metadata(self, client, db, reports_env):
        admin = reports_env["admin"]
        card = await create_card(db, card_type="Application", name="ERP", user_id=admin.id)
        await db.commit()
        resp = await client.post(
            f"/api/v1/cards/{card.id}/confirm?source_system=ServiceNow&confidence=high",
            headers=auth_headers(admin),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["source_system"] == "ServiceNow"
        assert body["confidence"] == "high"
        assert body["last_confirmed_at"] is not None

    async def test_confirm_requires_edit(self, client, db, reports_env):
        admin = reports_env["admin"]
        viewer = reports_env["viewer"]  # has inventory.view only, no edit
        card = await create_card(db, card_type="Application", name="CRM", user_id=admin.id)
        await db.commit()
        resp = await client.post(f"/api/v1/cards/{card.id}/confirm", headers=auth_headers(viewer))
        assert resp.status_code == 403

    async def test_freshness_rollup(self, client, db, reports_env):
        admin = reports_env["admin"]
        fresh = await create_card(db, card_type="Application", name="Fresh", user_id=admin.id)
        await create_card(db, card_type="Application", name="Never", user_id=admin.id)
        await db.commit()
        # Confirm one card so it is not stale.
        await client.post(f"/api/v1/cards/{fresh.id}/confirm", headers=auth_headers(admin))

        resp = await client.get("/api/v1/reports/freshness", headers=auth_headers(admin))
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["total"] == 2
        assert data["summary"]["confirmed"] == 1
        assert data["summary"]["stale"] == 1
        # The never-confirmed card is in the stale worklist.
        stale_names = {r["name"] for r in data["stale_records"]}
        assert "Never" in stale_names
        assert "Fresh" not in stale_names

    async def test_freshness_requires_permission(self, client, db, reports_env):
        resp = await client.get(
            "/api/v1/reports/freshness", headers=auth_headers(reports_env["noreports"])
        )
        assert resp.status_code == 403


class TestResilience:
    """Resilience / Critical Service View — /reports/resilience."""

    @pytest.fixture
    async def res_env(self, db, reports_env):
        await create_card_type(db, key="ITComponent", label="IT Component")
        await create_relation_type(
            db,
            key="relAppToITC",
            source_type_key="Application",
            target_type_key="ITComponent",
        )
        admin = reports_env["admin"]
        # Two critical apps both depending on one shared component (a SPOF).
        a1 = await create_card(
            db,
            card_type="Application",
            name="Payments",
            user_id=admin.id,
            attributes={"businessCriticality": "mission_critical", "rto": "4h"},
        )
        a2 = await create_card(
            db,
            card_type="Application",
            name="Trading",
            user_id=admin.id,
            attributes={"businessCriticality": "mission_critical"},
        )
        shared = await create_card(db, card_type="ITComponent", name="Shared DB", user_id=admin.id)
        await create_relation(db, type_key="relAppToITC", source_id=a1.id, target_id=shared.id)
        await create_relation(db, type_key="relAppToITC", source_id=a2.id, target_id=shared.id)
        return reports_env

    async def test_resilience_spof_and_gaps(self, client, db, res_env):
        admin = res_env["admin"]
        resp = await client.get("/api/v1/reports/resilience", headers=auth_headers(admin))
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["critical_services"] == 2
        # Shared DB depended on by both critical apps -> a SPOF.
        assert data["summary"]["spof_count"] == 1
        spof = data["spofs"][0]
        assert spof["name"] == "Shared DB"
        assert spof["concentration"] == 2
        assert set(spof["dependents"]) == {"Payments", "Trading"}
        # Trading is missing both rto + rpo; Payments missing rpo only.
        gap_names = {g["name"] for g in data["rto_rpo_gaps"]}
        assert "Trading" in gap_names
        assert data["summary"]["rto_rpo_gaps"] == 2

    async def test_resilience_requires_permission(self, client, db, res_env):
        resp = await client.get(
            "/api/v1/reports/resilience", headers=auth_headers(res_env["noreports"])
        )
        assert resp.status_code == 403


class TestDataFlow:
    """Data Domain & Flow Map — /reports/data-flow."""

    @pytest.fixture
    async def df_env(self, db, reports_env):
        await create_card_type(db, key="DataObject", label="Data Object")
        await create_card_type(db, key="Interface", label="Interface")
        await create_relation_type(
            db, key="relAppToDataObj", source_type_key="Application", target_type_key="DataObject"
        )
        admin = reports_env["admin"]
        app = await create_card(db, card_type="Application", name="CRM", user_id=admin.id)
        do = await create_card(
            db,
            card_type="DataObject",
            name="Customer",
            user_id=admin.id,
            attributes={"dataDomain": "Customer Domain"},
        )
        await create_card(db, card_type="DataObject", name="Orphan Data", user_id=admin.id)
        await create_relation(db, type_key="relAppToDataObj", source_id=app.id, target_id=do.id)
        return reports_env

    async def test_data_flow(self, client, db, df_env):
        admin = df_env["admin"]
        resp = await client.get("/api/v1/reports/data-flow", headers=auth_headers(admin))
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["data_objects"] == 2
        assert data["summary"]["orphans"] == 1
        customer = next(d for d in data["data_objects"] if d["name"] == "Customer")
        assert customer["domain"] == "Customer Domain"
        assert customer["applications"][0]["name"] == "CRM"

    async def test_data_flow_requires_permission(self, client, db, df_env):
        resp = await client.get(
            "/api/v1/reports/data-flow", headers=auth_headers(df_env["noreports"])
        )
        assert resp.status_code == 403


class TestIntegrationStatus:
    """Integration Hub — /reports/integration-status."""

    async def test_integration_status_empty(self, client, db, reports_env):
        admin = reports_env["admin"]
        resp = await client.get("/api/v1/reports/integration-status", headers=auth_headers(admin))
        assert resp.status_code == 200
        assert resp.json()["summary"]["connections"] == 0

    async def test_integration_status_with_connection(self, client, db, reports_env):
        from app.models.servicenow import SnowConnection

        admin = reports_env["admin"]
        conn = SnowConnection(name="Prod SNOW", instance_url="https://x.service-now.com")
        db.add(conn)
        await db.commit()
        resp = await client.get("/api/v1/reports/integration-status", headers=auth_headers(admin))
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["connections"] == 1
        row = data["connections"][0]
        assert row["name"] == "Prod SNOW"
        # No sync run yet -> stale.
        assert row["is_stale"] is True

    async def test_integration_status_requires_permission(self, client, db, reports_env):
        resp = await client.get(
            "/api/v1/reports/integration-status", headers=auth_headers(reports_env["noreports"])
        )
        assert resp.status_code == 403
