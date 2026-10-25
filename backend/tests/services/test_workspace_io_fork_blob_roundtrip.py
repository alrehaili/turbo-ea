"""Fork blob references must survive a transfer to newly assigned card ids."""

from sqlalchemy import delete, select

from app.models.adm import AdmPhase, AdmPhaseArtefact, AdmWorkspace
from app.models.card import Card
from app.models.relation import Relation
from app.models.roadmap import Roadmap
from app.models.scenario import Scenario, ScenarioChange
from app.models.web_portal import WebPortal
from app.services.workspace_io import apply_bundle, build_bundle, diff_bundle, parse_bundle
from tests.conftest import (
    create_card,
    create_card_type,
    create_relation,
    create_relation_type,
    create_user,
)


async def test_fork_blobs_remap_without_changing_module_ids_or_prose(db):
    user = await create_user(db, email="fork-transfer@test.com", role="admin")
    await create_card_type(db, key="Application", label="Application")
    await create_card_type(db, key="Initiative", label="Initiative")
    await create_relation_type(
        db, key="uses", source_type_key="Application", target_type_key="Application"
    )
    a = await create_card(db, name="App A")
    b = await create_card(db, name="App B")
    initiative = await create_card(db, name="Migration", card_type="Initiative")
    rel = await create_relation(db, type_key="uses", source_id=a.id, target_id=b.id)
    old_a, old_b, old_rel = str(a.id), str(b.id), str(rel.id)
    prose = f"Evidence about {old_a} remains an historical note"
    scenario = Scenario(name="Proposed", description=prose, created_by=user.id)
    roadmap = Roadmap(name="Plan", config={"type": "Application", "scopeIds": [old_a]})
    workspace = AdmWorkspace(name="Engagement", initiative_id=initiative.id)
    db.add_all([scenario, roadmap, workspace])
    await db.flush()
    phase = AdmPhase(workspace_id=workspace.id, phase_key="phase_a", title="Vision", sort_order=0)
    change = ScenarioChange(
        scenario_id=scenario.id,
        op="remove_relation",
        payload={
            "source_id": old_a,
            "target_id": old_b,
            "relation_id": old_rel,
            "relation_type": "uses",
        },
        baseline={"attributes": {"related": old_a}, "existed": True},
    )
    portal = WebPortal(
        name="Hub",
        slug="fork-hub",
        kind="hub",
        tiles=[{"title": "Apps", "tiles": [{"target": f"/cards/{old_a}"}]}],
    )
    db.add_all([phase, change, portal])
    await db.flush()
    artefact = AdmPhaseArtefact(phase_id=phase.id, kind="card", ref_id=a.id, title="App")
    db.add(artefact)
    await db.flush()
    ids = (scenario.id, roadmap.id, portal.id, artefact.id, change.id)
    bundle = parse_bundle(await build_bundle(db))
    for model in (
        AdmPhaseArtefact,
        AdmPhase,
        AdmWorkspace,
        ScenarioChange,
        Scenario,
        Roadmap,
        WebPortal,
        Relation,
        Card,
    ):
        await db.execute(delete(model))
    await db.flush()

    preview = await diff_bundle(db, bundle, user)
    assert preview.total_failed == 0 and preview.total_conflict == 0, preview.as_dict()
    result = await apply_bundle(db, bundle, user)
    assert result.total_failed == 0 and result.total_conflict == 0, result.as_dict()
    assert sum(s.created for s in result.sections) == sum(s.created for s in preview.sections)
    new_a = (await db.execute(select(Card).where(Card.name == "App A"))).scalar_one()
    new_b = (await db.execute(select(Card).where(Card.name == "App B"))).scalar_one()
    new_rel = (await db.execute(select(Relation))).scalar_one()
    assert str(new_a.id) != old_a and str(new_rel.id) != old_rel
    restored_change = await db.get(ScenarioChange, ids[4])
    assert restored_change.payload == {
        "source_id": str(new_a.id),
        "target_id": str(new_b.id),
        "relation_id": str(new_rel.id),
        "relation_type": "uses",
    }
    assert restored_change.baseline["attributes"]["related"] == str(new_a.id)
    assert (await db.get(Scenario, ids[0])).description == prose
    assert (await db.get(Roadmap, ids[1])).config["scopeIds"] == [str(new_a.id)]
    assert (await db.get(WebPortal, ids[2])).tiles[0]["tiles"][0]["target"] == f"/cards/{new_a.id}"
    assert (await db.get(AdmPhaseArtefact, ids[3])).ref_id == new_a.id
    again = await apply_bundle(db, bundle, user)
    assert sum(s.created for s in again.sections) == 0 and again.total_failed == 0, again.as_dict()
