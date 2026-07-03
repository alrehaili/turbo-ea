"""Tests for the NORA framework profile ([FORK] — noraPlan.md WP1.1).

Two groups:

* Pure definition tests (no database) — translation completeness across all
  9 non-English locales, key uniqueness, no collisions with the seed
  metamodel, and zero data-quality weight on every injected field.
* Database tests — idempotent field injection, preservation of admin
  customisations, and the stored profile flag lifecycle.
"""

from __future__ import annotations

import pytest

from app.services.nora_profile import (
    NORA_CARD_TYPES,
    NORA_PROFILE_VERSION,
    NORA_RELATION_TYPES,
    NORA_SECTION,
    NORA_SECTION_TRANSLATIONS,
    NORA_TYPE_FIELDS,
    apply_nora_profile,
    get_framework_profile,
    set_togaf_profile,
)
from app.services.seed import RELATIONS, TYPES
from tests.conftest import create_card_type, create_relation_type

SUPPORTED_LOCALES = ["de", "fr", "es", "it", "pt", "zh", "ru", "da", "ar"]


def _all_fields():
    return [
        pytest.param(type_key, field, id=f"{type_key}.{field['key']}")
        for type_key, fields in NORA_TYPE_FIELDS.items()
        for field in fields
    ]


# ---------------------------------------------------------------------------
# Definition tests (no database)
# ---------------------------------------------------------------------------


class TestNoraProfileDefinitions:
    def test_section_translations_complete(self):
        for locale in SUPPORTED_LOCALES:
            assert NORA_SECTION_TRANSLATIONS.get(locale), f"section missing {locale}"

    @pytest.mark.parametrize("type_key,field", _all_fields())
    def test_field_translations_complete(self, type_key, field):
        for locale in SUPPORTED_LOCALES:
            assert field["translations"].get(locale), f"{field['key']} missing {locale}"

    @pytest.mark.parametrize("type_key,field", _all_fields())
    def test_option_translations_complete(self, type_key, field):
        for option in field.get("options", []):
            for locale in SUPPORTED_LOCALES:
                assert option["translations"].get(locale), (
                    f"{field['key']}.{option['key']} missing {locale}"
                )

    @pytest.mark.parametrize("type_key,field", _all_fields())
    def test_fields_carry_zero_weight(self, type_key, field):
        """Enabling the profile must never degrade existing data-quality scores."""
        assert field.get("weight") == 0

    @pytest.mark.parametrize("type_key,field", _all_fields())
    def test_select_fields_have_options(self, type_key, field):
        if field["type"] in ("single_select", "multiple_select"):
            assert field.get("options"), f"{field['key']} has no options"

    def test_target_types_exist_in_seed(self):
        seed_keys = {t["key"] for t in TYPES}
        assert set(NORA_TYPE_FIELDS) <= seed_keys

    def test_no_key_collisions_with_seed_fields(self):
        """NORA field keys must not shadow fields the seed metamodel already has."""
        for type_key, fields in NORA_TYPE_FIELDS.items():
            seed_type = next(t for t in TYPES if t["key"] == type_key)
            existing = {
                f["key"]
                for section in seed_type.get("fields_schema", [])
                for f in section.get("fields", [])
            }
            clashes = [f["key"] for f in fields if f["key"] in existing]
            assert not clashes, f"{type_key}: {clashes} already defined in seed"

    def test_field_keys_unique_per_type(self):
        for type_key, fields in NORA_TYPE_FIELDS.items():
            keys = [f["key"] for f in fields]
            assert len(keys) == len(set(keys)), f"duplicate keys on {type_key}"

    def test_ndmo_classification_levels(self):
        """DataObject classification must carry the four Saudi NDMO levels."""
        field = next(f for f in NORA_TYPE_FIELDS["DataObject"] if f["key"] == "dataClassification")
        assert [o["key"] for o in field["options"]] == [
            "topSecret",
            "secret",
            "restricted",
            "public",
        ]


# ---------------------------------------------------------------------------
# NORA card type + relation type definitions (WP1.2)
# ---------------------------------------------------------------------------


def _nora_type_fields():
    return [
        pytest.param(t, f, id=f"{t['key']}.{f['key']}")
        for t in NORA_CARD_TYPES
        for section in t["fields_schema"]
        for f in section["fields"]
    ]


class TestNoraCardTypeDefinitions:
    def test_govservice_is_defined(self):
        assert "GovService" in {t["key"] for t in NORA_CARD_TYPES}

    @pytest.mark.parametrize("type_def", [pytest.param(t, id=t["key"]) for t in NORA_CARD_TYPES])
    def test_type_label_and_description_translated(self, type_def):
        for prop in ("label", "description"):
            for locale in SUPPORTED_LOCALES:
                assert type_def["translations"][prop].get(locale), f"{prop} missing {locale}"

    @pytest.mark.parametrize("type_def,field", _nora_type_fields())
    def test_type_field_translations_complete(self, type_def, field):
        for locale in SUPPORTED_LOCALES:
            assert field["translations"].get(locale), f"{field['key']} missing {locale}"
        for option in field.get("options", []):
            for locale in SUPPORTED_LOCALES:
                assert option["translations"].get(locale), (
                    f"{field['key']}.{option['key']} missing {locale}"
                )

    @pytest.mark.parametrize("type_def", [pytest.param(t, id=t["key"]) for t in NORA_CARD_TYPES])
    def test_stakeholder_roles_translated(self, type_def):
        keys = [sr["key"] for sr in type_def["stakeholder_roles"]]
        assert "service_owner" in keys or type_def["key"] != "GovService"
        for sr in type_def["stakeholder_roles"]:
            for locale in SUPPORTED_LOCALES:
                assert sr["translations"]["label"].get(locale), f"{sr['key']} missing {locale}"

    def test_type_keys_do_not_collide_with_seed(self):
        seed_keys = {t["key"] for t in TYPES}
        assert not seed_keys & {t["key"] for t in NORA_CARD_TYPES}


class TestNoraRelationTypeDefinitions:
    @pytest.mark.parametrize("rel", [pytest.param(r, id=r["key"]) for r in NORA_RELATION_TYPES])
    def test_relation_translations_complete(self, rel):
        for prop in ("label", "reverse_label"):
            for locale in SUPPORTED_LOCALES:
                assert rel["translations"][prop].get(locale), f"{prop} missing {locale}"

    def test_relation_pairs_do_not_collide_with_seed(self):
        """One relation type per ordered (source, target) pair — including seed."""
        seed_pairs = {(r["source_type_key"], r["target_type_key"]) for r in RELATIONS}
        nora_pairs = [(r["source_type_key"], r["target_type_key"]) for r in NORA_RELATION_TYPES]
        assert not seed_pairs & set(nora_pairs)
        assert len(nora_pairs) == len(set(nora_pairs))

    def test_relation_endpoints_exist(self):
        known = {t["key"] for t in TYPES} | {t["key"] for t in NORA_CARD_TYPES}
        for r in NORA_RELATION_TYPES:
            assert r["source_type_key"] in known
            assert r["target_type_key"] in known


# ---------------------------------------------------------------------------
# Database tests
# ---------------------------------------------------------------------------


class TestApplyNoraProfile:
    async def test_apply_injects_fields_and_sets_flag(self, db):
        await create_card_type(
            db,
            key="Application",
            fields_schema=[{"section": "General", "fields": [{"key": "vendor"}]}],
            built_in=True,
        )

        summary = await apply_nora_profile(db)

        assert "Application" in summary["types_updated"]
        assert summary["fields_added"] >= len(NORA_TYPE_FIELDS["Application"])

        from sqlalchemy import select

        from app.models.card_type import CardType

        ct = (await db.execute(select(CardType).where(CardType.key == "Application"))).scalar_one()
        nora_section = next(s for s in ct.fields_schema if s["section"] == NORA_SECTION)
        injected = {f["key"] for f in nora_section["fields"]}
        assert {"armCode", "armCategory", "automationLevel", "sharedService"} <= injected
        # Pre-existing sections untouched.
        assert ct.fields_schema[0]["section"] == "General"

        profile = await get_framework_profile(db)
        assert profile["profile"] == "nora"
        assert profile["nora_profile_version"] == NORA_PROFILE_VERSION

    async def test_apply_is_idempotent(self, db):
        await create_card_type(db, key="Application", fields_schema=[], built_in=True)

        first = await apply_nora_profile(db)
        second = await apply_nora_profile(db)

        assert first["fields_added"] > 0
        assert second["fields_added"] == 0
        assert second["types_updated"] == []

    async def test_apply_preserves_admin_moved_field(self, db):
        """A NORA-keyed field an admin already has (anywhere) is never duplicated."""
        custom = {"key": "armCode", "label": "My ARM Ref", "type": "text"}
        await create_card_type(
            db,
            key="Application",
            fields_schema=[{"section": "Custom", "fields": [custom]}],
            built_in=True,
        )

        await apply_nora_profile(db)

        from sqlalchemy import select

        from app.models.card_type import CardType

        ct = (await db.execute(select(CardType).where(CardType.key == "Application"))).scalar_one()
        arm_fields = [
            f for s in ct.fields_schema for f in s.get("fields", []) if f["key"] == "armCode"
        ]
        assert len(arm_fields) == 1
        assert arm_fields[0]["label"] == "My ARM Ref"

    async def test_missing_types_are_skipped(self, db):
        """Applying against an empty metamodel still records the profile flag."""
        summary = await apply_nora_profile(db)
        assert summary["types_updated"] == []
        assert (await get_framework_profile(db))["profile"] == "nora"

    async def test_apply_creates_govservice_with_roles_and_relations(self, db):
        # Endpoints the GovService relations point at.
        for key in ("Application", "BusinessProcess", "BusinessCapability", "DataObject"):
            await create_card_type(db, key=key, fields_schema=[], built_in=True)
        await create_card_type(db, key="Organization", fields_schema=[], built_in=True)

        summary = await apply_nora_profile(db)

        assert "GovService" in summary["card_types_created"]
        assert set(summary["relation_types_created"]) == {
            "relGovServiceToProcess",
            "relGovServiceToApp",
            "relOrgToGovService",
            "relGovServiceToBC",
            "relGovServiceToDO",
        }
        assert summary["relation_types_skipped"] == []

        from sqlalchemy import select

        from app.models.card_type import CardType
        from app.models.stakeholder_role_definition import StakeholderRoleDefinition

        gov = (await db.execute(select(CardType).where(CardType.key == "GovService"))).scalar_one()
        assert gov.category == "Business Architecture"
        assert gov.built_in is True
        field_keys = {f["key"] for s in gov.fields_schema for f in s["fields"]}
        assert {
            "serviceCode",
            "beneficiaryType",
            "deliveryChannel",
            "serviceMaturity",
        } <= field_keys

        srds = (
            (
                await db.execute(
                    select(StakeholderRoleDefinition).where(
                        StakeholderRoleDefinition.card_type_key == "GovService"
                    )
                )
            )
            .scalars()
            .all()
        )
        srd_map = {s.key: s for s in srds}
        assert {"responsible", "observer", "service_owner"} <= set(srd_map)
        # Service owner inherits the responsible permission set.
        assert srd_map["service_owner"].permissions.get("card.edit") is True

        # Second apply creates nothing new.
        second = await apply_nora_profile(db)
        assert second["card_types_created"] == []
        assert second["relation_types_created"] == []

    async def test_relation_pair_conflict_is_skipped(self, db):
        """An admin-modelled (source, target) pair is never given a second relation type."""
        await create_card_type(db, key="Application", fields_schema=[], built_in=True)
        await create_relation_type(
            db,
            key="myCustomServiceRel",
            label="serves",
            source_type_key="GovService",
            target_type_key="Application",
        )

        summary = await apply_nora_profile(db)

        assert "relGovServiceToApp" in summary["relation_types_skipped"]
        assert "relGovServiceToApp" not in summary["relation_types_created"]

    async def test_existing_govservice_type_is_preserved(self, db):
        custom = await create_card_type(
            db,
            key="GovService",
            label="My Services",
            fields_schema=[{"section": "Mine", "fields": [{"key": "x"}]}],
            built_in=False,
        )

        summary = await apply_nora_profile(db)

        assert summary["card_types_created"] == []
        from sqlalchemy import select

        from app.models.card_type import CardType

        gov = (await db.execute(select(CardType).where(CardType.key == "GovService"))).scalar_one()
        assert gov.id == custom.id
        assert gov.label == "My Services"

    async def test_switch_back_to_togaf_preserves_fields(self, db):
        await create_card_type(db, key="DataObject", fields_schema=[], built_in=True)
        await apply_nora_profile(db)
        await set_togaf_profile(db)

        assert (await get_framework_profile(db))["profile"] == "togaf"

        from sqlalchemy import select

        from app.models.card_type import CardType

        ct = (await db.execute(select(CardType).where(CardType.key == "DataObject"))).scalar_one()
        assert any(s["section"] == NORA_SECTION for s in ct.fields_schema)


class TestGovernancePack:
    async def test_apply_seeds_governance_roles(self, db):
        summary = await apply_nora_profile(db)
        assert set(summary["roles_created"]) == {
            "ea_working_team",
            "chief_architect",
            "ea_governance_committee",
        }

        from sqlalchemy import select

        from app.models.role import Role

        roles = {r.key: r for r in (await db.execute(select(Role))).scalars().all()}
        assert roles["chief_architect"].permissions.get("governance.approve_step") is True
        assert roles["ea_governance_committee"].permissions.get("governance.approve_step") is True
        # Working team drafts but never approves.
        wt = roles["ea_working_team"].permissions
        assert wt.get("governance.approve_step") is not True
        assert wt.get("inventory.approval_status") is not True

        # Second apply creates nothing (existing roles untouched).
        second = await apply_nora_profile(db)
        assert second["roles_created"] == []

    async def test_apply_injects_transition_role_attribute(self, db):
        from tests.conftest import create_relation_type

        await create_relation_type(
            db,
            key="relInitiativeToApp",
            label="delivers",
            source_type_key="Initiative",
            target_type_key="Application",
        )
        # Not an Initiative relation — must stay untouched.
        await create_relation_type(
            db,
            key="relAppToITC",
            label="uses",
            source_type_key="Application",
            target_type_key="ITComponent",
        )

        summary = await apply_nora_profile(db)
        assert "relInitiativeToApp" in summary.get("relation_types_updated", [])

        from sqlalchemy import select

        from app.models.relation_type import RelationType

        rt = (
            await db.execute(select(RelationType).where(RelationType.key == "relInitiativeToApp"))
        ).scalar_one()
        attr = next(a for a in rt.attributes_schema if a["key"] == "transitionRole")
        assert [o["key"] for o in attr["options"]] == ["introduces", "modifies", "retires"]

        other = (
            await db.execute(select(RelationType).where(RelationType.key == "relAppToITC"))
        ).scalar_one()
        assert all(a.get("key") != "transitionRole" for a in (other.attributes_schema or []))

        # Idempotent.
        second = await apply_nora_profile(db)
        assert "relInitiativeToApp" not in second.get("relation_types_updated", [])


class TestPhase4Passes:
    async def test_database_subtype_and_regulations_seeded(self, db):
        await create_card_type(
            db,
            key="ITComponent",
            label="IT Component",
            fields_schema=[],
            built_in=True,
            subtypes=[{"key": "software", "label": "Software"}],
        )

        summary = await apply_nora_profile(db)

        assert summary.get("subtypes_added") == ["ITComponent.database"]
        assert set(summary.get("regulations_created", [])) == {
            "nca_ecc",
            "ndmo_dm",
            "pdpl",
            "dga_policy",
        }

        from sqlalchemy import select

        from app.models.card_type import CardType
        from app.models.compliance_regulation import ComplianceRegulation

        itc = (await db.execute(select(CardType).where(CardType.key == "ITComponent"))).scalar_one()
        keys = [s["key"] for s in itc.subtypes]
        assert keys == ["software", "database"]

        regs = (await db.execute(select(ComplianceRegulation))).scalars().all()
        assert {r.key for r in regs} >= {"nca_ecc", "ndmo_dm", "pdpl", "dga_policy"}

        # Second apply: nothing new.
        second = await apply_nora_profile(db)
        assert "subtypes_added" not in second
        assert "regulations_created" not in second

    async def test_new_types_created_with_relations(self, db):
        for key in (
            "Application",
            "BusinessProcess",
            "BusinessCapability",
            "DataObject",
            "Organization",
            "Objective",
            "Initiative",
            "ITComponent",
        ):
            await create_card_type(db, key=key, fields_schema=[], built_in=True)

        summary = await apply_nora_profile(db)

        assert {"GovService", "DataExchange", "KPI"} <= set(summary["card_types_created"])
        assert {
            "relAppToDataExchange",
            "relDataExchangeToDO",
            "relDataObjectToITC",
            "relObjectiveToKPI",
            "relKPIToGovService",
            "relInitiativeToKPI",
        } <= set(summary["relation_types_created"])
