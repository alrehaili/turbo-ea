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
        # v2: NORA_TYPE_FIELDS may also target NORA-created types (GovService)
        # — those are created by pass 1 before pass 4 runs.
        known_keys = {t["key"] for t in TYPES} | {t["key"] for t in NORA_CARD_TYPES}
        assert set(NORA_TYPE_FIELDS) <= known_keys

    def test_no_key_collisions_with_seed_fields(self):
        """NORA field keys must not shadow fields the target type already has."""
        for type_key, fields in NORA_TYPE_FIELDS.items():
            base_type = next(
                (t for t in TYPES if t["key"] == type_key),
                None,
            ) or next(t for t in NORA_CARD_TYPES if t["key"] == type_key)
            existing = {
                f["key"]
                for section in base_type.get("fields_schema", [])
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

    # ── Profile v2 (WP6.2) — Dec-2024 Meta Model / template alignment ──────

    def test_profile_version_is_10(self):
        from app.services.nora_profile import NORA_PROFILE_VERSION

        assert NORA_PROFILE_VERSION == 10

    def test_v8_rm_code_fields_defined(self):
        """Profile v8 — every one of the six domains has an RM code field."""
        expected = {
            "BusinessCapability": "brmCode",
            "Application": "armCode",
            "DataObject": "drmCode",
            "ITComponent": "trmCode",
            "GovService": "bxrmCode",
            "SecurityControl": "srmCode",
        }
        for type_key, field_key in expected.items():
            keys = {f["key"] for f in NORA_TYPE_FIELDS.get(type_key, [])}
            assert field_key in keys, f"{type_key} is missing {field_key}"

    def test_pillar_card_type_defined(self):
        """Profile v6 — Pillar is a first-class card type with the
        Objective → Pillar supports relation, fully translated."""
        pillar = next(t for t in NORA_CARD_TYPES if t["key"] == "Pillar")
        locales = {"de", "fr", "es", "it", "pt", "zh", "ru", "da", "ar"}
        assert set(pillar["translations"]["label"]) == locales
        field_keys = {f["key"] for s in pillar["fields_schema"] for f in s.get("fields", [])}
        assert {"pillarCode", "pillarOrder"} <= field_keys

        rel = next(r for r in NORA_RELATION_TYPES if r["key"] == "relObjectiveToPillar")
        assert (rel["source_type_key"], rel["target_type_key"]) == ("Objective", "Pillar")
        assert set(rel["translations"]["label"]) == locales

    def test_usage_role_attribute_translations(self):
        """WP6.4 — the usageRole attribute + options carry all 9 locales."""
        from app.services.nora_profile import USAGE_ROLE_ATTRIBUTE

        locales = {"de", "fr", "es", "it", "pt", "zh", "ru", "da", "ar"}
        assert set(USAGE_ROLE_ATTRIBUTE["translations"]) == locales
        assert {o["key"] for o in USAGE_ROLE_ATTRIBUTE["options"]} == {"uses", "protects"}
        for opt in USAGE_ROLE_ATTRIBUTE["options"]:
            assert set(opt["translations"]) == locales

    def test_nca_ecc_scope_mentions_security_components(self):
        """WP6.4 — the NCA ECC scanner scope carries the missing-security-
        component rule (and the guarded-upgrade constant matches its prefix)."""
        from app.services.nora_profile import _NCA_ECC_DESCRIPTION_V4, SAUDI_REGULATION_PACK

        nca = next(r for r in SAUDI_REGULATION_PACK if r["key"] == "nca_ecc")
        assert nca["description"].startswith(_NCA_ECC_DESCRIPTION_V4)
        assert "security component" in nca["description"]

    def test_v2_template_fields_present(self):
        """Every حصر البيانات template column has a landing field (or a documented
        mapping to a seed field — those are deliberately absent here)."""
        by_type = {tk: {f["key"] for f in fields} for tk, fields in NORA_TYPE_FIELDS.items()}
        assert {
            "serviceClassification",
            "serviceType",
            "automationLevel",
            "geoCoverage",
            "serviceRequirements",
            "serviceInputs",
            "serviceOutputs",
            "participatingEntities",
            "executionSteps",
        } <= by_type["GovService"]
        assert {
            "processClassification",
            "triggerEvent",
            "businessRules",
            "durationDays",
            "processInputs",
            "processOutputs",
        } <= by_type["BusinessProcess"]
        assert {
            "appLayer",
            "developmentType",
            "sourceType",
            "contractor",
            "appUrl",
            "authenticationMethod",
            "launchDate",
            "architecturePattern",
            "costCapex",
        } <= by_type["Application"]
        assert {
            "integrationScope",
            "integrationPlatform",
            "linkType",
            "interfaceInputs",
            "interfaceOutputs",
        } <= by_type["Interface"]
        assert {
            "supportEndDate",
            "supportContractStatus",
            "operationType",
            "initialCost",
            "environment",
            "clusterId",
            "firmwareVersion",
            "inBackupPolicy",
            "inDrPolicy",
        } <= by_type["ITComponent"]
        assert "dataType" in by_type["DataObject"]

    def test_v2_app_layer_matches_template_lookup(self):
        """appLayer options mirror the template's five-layer classification."""
        field = next(f for f in NORA_TYPE_FIELDS["Application"] if f["key"] == "appLayer")
        assert [o["key"] for o in field["options"]] == [
            "access",
            "core",
            "support",
            "data",
            "infrastructure",
        ]

    def test_v2_subtypes_translated(self):
        from app.services.nora_profile import NORA_V2_SUBTYPES

        assert {t["key"] for t in NORA_V2_SUBTYPES["Objective"]} == {"pillar"}
        # NEA TA (§5.3.6) + Security (§5.3.7) building blocks + DRM data vault.
        assert {t["key"] for t in NORA_V2_SUBTYPES["ITComponent"]} == {
            "dataVault",
            "dataCenter",
            "physicalHost",
            "virtualServer",
            "networkDevice",
            "storage",
            "infraTool",
            "infraService",
            "license",
            "containerEngine",
            "peripheral",
            "securityHardware",
            "securitySoftware",
            "securityService",
        }
        for subtype_defs in NORA_V2_SUBTYPES.values():
            for sub in subtype_defs:
                for locale in SUPPORTED_LOCALES:
                    assert sub["translations"].get(locale), f"{sub['key']} missing {locale}"

    def test_v7_org_hierarchy_subtypes(self):
        """Profile v7 (WP100.2) — Saudi government organizational-hierarchy
        levels as Organization subtypes, Arabic first-class, and the
        publicAdministration orgUnitType option renamed so «إدارة عامة»
        means only the generalDepartment subtype."""
        from app.services.nora_profile import NORA_TYPE_FIELDS, NORA_V2_SUBTYPES

        org_subs = {s["key"]: s for s in NORA_V2_SUBTYPES["Organization"]}
        assert set(org_subs) == {"sector", "generalDepartment", "department", "sectionUnit"}
        assert org_subs["sector"]["translations"]["ar"] == "قطاع"
        assert org_subs["generalDepartment"]["translations"]["ar"] == "إدارة عامة"
        assert org_subs["department"]["translations"]["ar"] == "إدارة"
        assert org_subs["sectionUnit"]["translations"]["ar"] == "قسم/وحدة"

        org_unit_type = next(
            f for f in NORA_TYPE_FIELDS["Organization"] if f["key"] == "orgUnitType"
        )
        pub_admin = next(o for o in org_unit_type["options"] if o["key"] == "publicAdministration")
        assert pub_admin["translations"]["ar"] == "جهة إدارية عامة"

    def test_v2_subtype_keys_do_not_collide_with_seed(self):
        from app.services.nora_profile import NORA_V2_SUBTYPES

        for type_key, subtype_defs in NORA_V2_SUBTYPES.items():
            # v4: subtypes may also target profile-created types
            # (BeneficiaryJourney) — those are created by pass 1 before 4d.
            base_type = next((t for t in TYPES if t["key"] == type_key), None) or next(
                t for t in NORA_CARD_TYPES if t["key"] == type_key
            )
            existing = {s["key"] for s in base_type.get("subtypes", [])}
            clashes = [s["key"] for s in subtype_defs if s["key"] in existing]
            assert not clashes, f"{type_key}: {clashes} already in seed subtypes"

    def test_govservice_definition_has_hierarchy(self):
        gov = next(t for t in NORA_CARD_TYPES if t["key"] == "GovService")
        assert gov["has_hierarchy"] is True

    # ── Profile v4 (GFSA EA Metamodel v3) ──────────────────────────────────

    def test_v4_persona_and_policy_defined(self):
        by_key = {t["key"]: t for t in NORA_CARD_TYPES}
        assert by_key["Persona"]["category"] == "Beneficiary Experience"
        assert by_key["Policy"]["category"] == "Business"

    def test_v4_journey_subtypes(self):
        from app.services.nora_profile import NORA_V2_SUBTYPES

        assert {t["key"] for t in NORA_V2_SUBTYPES["BeneficiaryJourney"]} == {
            "journeyPhase",
            "journeyStep",
        }

    def test_v4_attribute_gap_fields_present(self):
        by_type = {tk: {f["key"] for f in fields} for tk, fields in NORA_TYPE_FIELDS.items()}
        assert "capabilityType" in by_type["BusinessCapability"]
        assert {"orgUnitType", "mandates"} <= by_type["Organization"]
        assert {
            "fieldOfActivity",
            "servicesProvided",
            "providerStatus",
            "geoLocation",
        } <= by_type["Provider"]
        assert {"productType", "productOwner", "productBeneficiary"} <= by_type["BusinessContext"]
        assert {
            "projectSponsor",
            "projectManager",
            "executionEntity",
            "priorityLevel",
            "projectDeliverables",
            "scopeOfWork",
        } <= by_type["Initiative"]
        assert {"beneficiaryType", "participatingEntities"} <= by_type["BusinessProcess"]
        assert {
            "structureClassification",
            "dataBusinessRules",
            "securityControls",
        } <= by_type["DataObject"]
        assert {"accessChannel", "developmentTechnology"} <= by_type["Application"]
        assert "serviceFee" in by_type["GovService"]
        assert {
            "indicatorLevel",
            "calculationFormula",
            "dataSource",
            "lastMeasuredDate",
            "baselineDate",
            "targetValueDate",
        } <= by_type["KPI"]

    def test_v4_sectioned_fields_translated_and_zero_weight(self):
        from app.services.nora_profile import NORA_SECTIONED_FIELDS

        for type_key, section_defs in NORA_SECTIONED_FIELDS.items():
            for section_def in section_defs:
                for locale in SUPPORTED_LOCALES:
                    assert section_def["translations"].get(locale), (
                        f"{type_key}.{section_def['section']} missing {locale}"
                    )
                for field in section_def["fields"]:
                    assert field.get("weight") == 0, f"{field['key']} must be weight 0"
                    for locale in SUPPORTED_LOCALES:
                        assert field["translations"].get(locale), f"{field['key']} missing {locale}"
                    if field["type"] in ("single_select", "multiple_select"):
                        assert field.get("options"), f"{field['key']} has no options"
                        for option in field["options"]:
                            for locale in SUPPORTED_LOCALES:
                                assert option["translations"].get(locale), (
                                    f"{field['key']}.{option['key']} missing {locale}"
                                )

    def test_v4_sectioned_field_keys_do_not_collide(self):
        from app.services.nora_profile import NORA_SECTIONED_FIELDS

        for type_key, section_defs in NORA_SECTIONED_FIELDS.items():
            base_type = next((t for t in TYPES if t["key"] == type_key), None) or next(
                t for t in NORA_CARD_TYPES if t["key"] == type_key
            )
            existing = {
                f["key"]
                for section in base_type.get("fields_schema", [])
                for f in section.get("fields", [])
            } | {f["key"] for f in NORA_TYPE_FIELDS.get(type_key, [])}
            sectioned = [f["key"] for s in section_defs for f in s["fields"]]
            clashes = [k for k in sectioned if k in existing]
            assert not clashes, f"{type_key}: {clashes} already defined elsewhere"
            assert len(sectioned) == len(set(sectioned)), f"duplicate keys on {type_key}"


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
        # The fork promoted several NORA types (GovService, Pillar, Policy,
        # Persona, BeneficiaryJourney) into the base seed metamodel while their
        # richer field/stakeholder definitions still live in NORA_CARD_TYPES;
        # apply_nora_profile skips creating a type the seed already owns. Those
        # overlaps are intentional and allow-listed here so the guard still
        # catches any NEW accidental collision.
        allowed = {"GovService", "Pillar", "Policy", "Persona", "BeneficiaryJourney"}
        seed_keys = {t["key"] for t in TYPES}
        collisions = (seed_keys & {t["key"] for t in NORA_CARD_TYPES}) - allowed
        assert not collisions, f"unexpected type-key collisions with seed: {collisions}"


class TestNoraRelationTypeDefinitions:
    @pytest.mark.parametrize("rel", [pytest.param(r, id=r["key"]) for r in NORA_RELATION_TYPES])
    def test_relation_translations_complete(self, rel):
        for prop in ("label", "reverse_label"):
            for locale in SUPPORTED_LOCALES:
                assert rel["translations"][prop].get(locale), f"{prop} missing {locale}"

    def test_relation_pairs_do_not_collide_with_seed(self):
        """One relation type per ordered (source, target) pair — including seed.

        A few GovService relations were promoted into the base seed while their
        definitions remain in NORA_RELATION_TYPES (apply skips occupied pairs);
        those overlaps are intentional and allow-listed so the guard still
        catches any NEW accidental collision.
        """
        allowed_pairs = {
            ("GovService", "BusinessProcess"),
            ("GovService", "Application"),
            ("Organization", "GovService"),
        }
        seed_pairs = {(r["source_type_key"], r["target_type_key"]) for r in RELATIONS}
        nora_pairs = [(r["source_type_key"], r["target_type_key"]) for r in NORA_RELATION_TYPES]
        collisions = (seed_pairs & set(nora_pairs)) - allowed_pairs
        assert not collisions, f"unexpected relation-pair collisions with seed: {collisions}"
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
        # v2: GovService is created by pass 1 and receives its v2 fields via
        # pass 4 even on an otherwise empty metamodel; no seed type is touched.
        # v4: KPI likewise receives its v4 fields via pass 4, and the
        # profile-created BeneficiaryJourney gets Journey Mapping via pass 4f.
        # v8: SecurityControl receives srmCode via pass 4.
        assert set(summary["types_updated"]) == {
            "GovService",
            "KPI",
            "BeneficiaryJourney",
            "SecurityControl",
        }
        assert (await get_framework_profile(db))["profile"] == "nora"

    async def test_apply_creates_govservice_with_roles_and_relations(self, db):
        # Endpoints the GovService relations point at.
        for key in ("Application", "BusinessProcess", "BusinessCapability", "DataObject"):
            await create_card_type(db, key=key, fields_schema=[], built_in=True)
        await create_card_type(db, key="Organization", fields_schema=[], built_in=True)

        summary = await apply_nora_profile(db)

        assert "GovService" in summary["card_types_created"]
        # Superset: WP4.1/4.2 create further relation types (DataExchange, KPI)
        # in the same apply when their endpoints exist.
        assert set(summary["relation_types_created"]) >= {
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
        assert gov.category == "Beneficiary Experience"
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

        # Other NORA types (DataExchange, KPI) are still created; the existing
        # GovService row is never recreated or overwritten.
        assert "GovService" not in summary["card_types_created"]
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

    async def test_apply_v5_security_and_governance_additions(self, db):
        """Profile v5 (WP6.4 + WP2.3 remainder + Strategic House): usageRole
        on relAppToITC, data-governance stakeholder roles, Objective
        hierarchy, and the guarded NCA ECC scope upgrade."""
        from sqlalchemy import select

        from tests.conftest import create_card_type, create_relation_type

        await create_card_type(db, key="BusinessCapability", built_in=True, fields_schema=[])
        await create_card_type(db, key="DataObject", built_in=True, fields_schema=[])
        await create_card_type(
            db, key="Objective", built_in=True, fields_schema=[], has_hierarchy=False
        )
        await create_relation_type(
            db,
            key="relAppToITC",
            label="uses",
            source_type_key="Application",
            target_type_key="ITComponent",
        )

        summary = await apply_nora_profile(db)

        # (a) usageRole on the Application → ITComponent relation.
        from app.models.relation_type import RelationType

        rt = (
            await db.execute(select(RelationType).where(RelationType.key == "relAppToITC"))
        ).scalar_one()
        attr = next(a for a in rt.attributes_schema if a["key"] == "usageRole")
        assert {o["key"] for o in attr["options"]} == {"uses", "protects"}

        # (b) domain_owner / data_steward stakeholder roles seeded.
        from app.models.stakeholder_role_definition import StakeholderRoleDefinition

        created = summary.get("stakeholder_roles_created", [])
        assert "BusinessCapability.domain_owner" in created
        assert "DataObject.data_steward" in created
        srd = (
            await db.execute(
                select(StakeholderRoleDefinition).where(
                    StakeholderRoleDefinition.key == "data_steward"
                )
            )
        ).scalar_one()
        assert srd.card_type_key == "DataObject"
        assert set(srd.translations) >= {"ar", "de", "fr"}

        # (c) Objective hierarchy enabled (Strategic House pillar tree).
        from app.models.card_type import CardType

        obj = (await db.execute(select(CardType).where(CardType.key == "Objective"))).scalar_one()
        assert obj.has_hierarchy is True
        assert summary.get("objective_hierarchy_enabled") is True

        # (d) An untouched pre-v5 NCA ECC description is upgraded in place.
        from app.models.compliance_regulation import ComplianceRegulation
        from app.services.nora_profile import _NCA_ECC_DESCRIPTION_V4

        nca = (
            await db.execute(
                select(ComplianceRegulation).where(ComplianceRegulation.key == "nca_ecc")
            )
        ).scalar_one()
        nca.description = _NCA_ECC_DESCRIPTION_V4
        await db.flush()
        second = await apply_nora_profile(db)
        assert "nca_ecc" in second.get("regulations_updated", [])
        await db.refresh(nca)
        assert "security component" in nca.description

        # An admin-edited description is never overwritten.
        nca.description = "Custom scope"
        await db.flush()
        third = await apply_nora_profile(db)
        assert "nca_ecc" not in third.get("regulations_updated", [])

        # All idempotent.
        assert third.get("stakeholder_roles_created", []) == []


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

        # v2: pass 4d appends the NEA subtype set after pass 4b's database.
        # v4: pass 4d also adds the BeneficiaryJourney phase/step subtypes, so
        # compare as a superset rather than an exact ordered list.
        from app.services.nora_profile import NORA_V2_SUBTYPES

        expected_v2 = {f"ITComponent.{s['key']}" for s in NORA_V2_SUBTYPES["ITComponent"]}
        assert {"ITComponent.database", *expected_v2} <= set(summary.get("subtypes_added", []))
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
        assert keys[:2] == ["software", "database"]
        assert set(keys) >= {s["key"] for s in NORA_V2_SUBTYPES["ITComponent"]}

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


class TestProfileV2Passes:
    """WP6.2 — pass 4d subtypes, GovService hierarchy, v2 field injection."""

    async def test_pillar_subtype_and_govservice_hierarchy(self, db):
        await create_card_type(
            db,
            key="Objective",
            label="Objective",
            fields_schema=[],
            built_in=True,
            subtypes=[],
        )
        # Simulate a v1 install: the profile-created GovService predates the
        # hierarchy upgrade.
        await create_card_type(
            db,
            key="GovService",
            label="Government Service",
            fields_schema=[],
            built_in=True,
            has_hierarchy=False,
        )

        summary = await apply_nora_profile(db)

        assert "Objective.pillar" in summary.get("subtypes_added", [])
        assert summary.get("gov_service_hierarchy_enabled") is True

        from sqlalchemy import select

        from app.models.card_type import CardType

        obj = (await db.execute(select(CardType).where(CardType.key == "Objective"))).scalar_one()
        assert "pillar" in [s["key"] for s in obj.subtypes]
        gov = (await db.execute(select(CardType).where(CardType.key == "GovService"))).scalar_one()
        assert gov.has_hierarchy is True

        # Second apply: nothing new, hierarchy stays on.
        second = await apply_nora_profile(db)
        assert "subtypes_added" not in second
        assert "gov_service_hierarchy_enabled" not in second

    async def test_admin_created_govservice_hierarchy_untouched(self, db):
        await create_card_type(
            db,
            key="GovService",
            label="My Services",
            fields_schema=[],
            built_in=False,
        )

        summary = await apply_nora_profile(db)

        assert "gov_service_hierarchy_enabled" not in summary
        from sqlalchemy import select

        from app.models.card_type import CardType

        gov = (await db.execute(select(CardType).where(CardType.key == "GovService"))).scalar_one()
        assert gov.has_hierarchy is False

    async def test_v2_fields_injected_into_existing_and_nora_types(self, db):
        await create_card_type(db, key="BusinessProcess", fields_schema=[], built_in=True)
        await create_card_type(db, key="Interface", fields_schema=[], built_in=True)

        summary = await apply_nora_profile(db)

        from sqlalchemy import select

        from app.models.card_type import CardType

        bp = (
            await db.execute(select(CardType).where(CardType.key == "BusinessProcess"))
        ).scalar_one()
        bp_keys = {f["key"] for s in bp.fields_schema for f in s.get("fields", [])}
        assert {"processClassification", "triggerEvent", "durationDays"} <= bp_keys

        # GovService is created by pass 1, then pass 4 adds the v2 fields.
        gov = (await db.execute(select(CardType).where(CardType.key == "GovService"))).scalar_one()
        gov_keys = {f["key"] for s in gov.fields_schema for f in s.get("fields", [])}
        assert {"serviceClassification", "serviceType", "executionSteps"} <= gov_keys
        assert "GovService" in summary["types_updated"]

        iface = (await db.execute(select(CardType).where(CardType.key == "Interface"))).scalar_one()
        iface_keys = {f["key"] for s in iface.fields_schema for f in s.get("fields", [])}
        assert {"integrationScope", "linkType", "interfaceOutputs"} <= iface_keys


class TestProfileV3SixLayers:
    """Profile v3 — six-layer categories + Beneficiary Experience / Security types."""

    async def test_new_types_created_with_six_layer_categories(self, db):
        summary = await apply_nora_profile(db)

        from sqlalchemy import select

        from app.models.card_type import CardType

        for key, category in (
            ("BeneficiaryJourney", "Beneficiary Experience"),
            ("Channel", "Beneficiary Experience"),
            ("SecurityControl", "Security"),
            ("GovService", "Beneficiary Experience"),
            ("KPI", "Business"),
            ("DataExchange", "Data"),
        ):
            ct = (await db.execute(select(CardType).where(CardType.key == key))).scalar_one()
            assert ct.category == category, key
            assert ct.built_in is True
        # (pre-existing bug fixed with v4: the summary key is
        # card_types_created — "types_created" never existed.)
        assert {"BeneficiaryJourney", "Channel", "SecurityControl"} <= set(
            summary.get("card_types_created", [])
        )

    async def test_category_moves_are_guarded(self, db):
        # A v2-era install: built-ins still carry the legacy four-layer names,
        # except one the admin re-categorised (must be preserved).
        await create_card_type(
            db,
            key="Objective",
            label="Objective",
            fields_schema=[],
            built_in=True,
            category="Strategy & Transformation",
        )
        await create_card_type(
            db,
            key="DataObject",
            label="Data Object",
            fields_schema=[],
            built_in=True,
            category="Application & Data",
        )
        await create_card_type(
            db,
            key="ITComponent",
            label="IT Component",
            fields_schema=[],
            built_in=True,
            category="My Custom Layer",
        )

        summary = await apply_nora_profile(db)

        from sqlalchemy import select

        from app.models.card_type import CardType

        cats = dict((await db.execute(select(CardType.key, CardType.category))).all())
        assert cats["Objective"] == "Business"
        assert cats["DataObject"] == "Data"
        # Admin-customised category untouched.
        assert cats["ITComponent"] == "My Custom Layer"
        moved = summary.get("categories_moved", [])
        assert any(m.startswith("Objective") for m in moved)
        assert not any(m.startswith("ITComponent") for m in moved)

        # Re-apply is a no-op for categories.
        second = await apply_nora_profile(db)
        assert "categories_moved" not in second


class TestProfileV4GfsaMetamodel:
    """Profile v4 — GFSA EA Metamodel v3 alignment (Persona, Policy, journey
    structure, Technical Specification section, attribute gaps)."""

    async def test_persona_and_policy_created_with_relations(self, db):
        summary = await apply_nora_profile(db)

        from sqlalchemy import select

        from app.models.card_type import CardType
        from app.models.relation_type import RelationType

        for key, category in (("Persona", "Beneficiary Experience"), ("Policy", "Business")):
            ct = (await db.execute(select(CardType).where(CardType.key == key))).scalar_one()
            assert ct.category == category
            assert ct.built_in is True
        assert {"Persona", "Policy"} <= set(summary["card_types_created"])

        rel_keys = {r for (r,) in (await db.execute(select(RelationType.key))).all()}
        assert {
            "relPersonaToGovService",
            "relPersonaToJourney",
            "relJourneyToGovService",
            "relJourneyToChannel",
            "relPolicyToBC",
            "relPolicyToGovService",
            "relPolicyToProcess",
        } <= rel_keys

    async def test_journey_subtypes_and_mapping_section(self, db):
        await apply_nora_profile(db)

        from sqlalchemy import select

        from app.models.card_type import CardType

        journey = (
            await db.execute(select(CardType).where(CardType.key == "BeneficiaryJourney"))
        ).scalar_one()
        assert {"journeyPhase", "journeyStep"} <= {s["key"] for s in journey.subtypes}
        mapping = next(s for s in journey.fields_schema if s["section"] == "Journey Mapping")
        assert {"journeyCode", "associatedGaps", "improvementPriority"} <= {
            f["key"] for f in mapping["fields"]
        }

    async def test_technical_specification_injected_and_idempotent(self, db):
        await create_card_type(
            db,
            key="ITComponent",
            fields_schema=[{"section": "General", "fields": [{"key": "version"}]}],
            built_in=True,
        )

        first = await apply_nora_profile(db)
        assert "ITComponent" in first["types_updated"]

        from sqlalchemy import select

        from app.models.card_type import CardType

        itc = (await db.execute(select(CardType).where(CardType.key == "ITComponent"))).scalar_one()
        spec = next(s for s in itc.fields_schema if s["section"] == "Technical Specification")
        spec_keys = {f["key"] for f in spec["fields"]}
        assert {"networkSegment", "cpuCores", "ramGb", "osType", "dcRole"} <= spec_keys
        assert all(f.get("weight") == 0 for f in spec["fields"])

        second = await apply_nora_profile(db)
        assert second["fields_added"] == 0
        assert second["types_updated"] == []

    async def test_sectioned_fields_respect_admin_moved_field(self, db):
        """A spec-keyed field an admin already has (anywhere) is never duplicated."""
        custom = {"key": "cpuCores", "label": "My Cores", "type": "number"}
        await create_card_type(
            db,
            key="ITComponent",
            fields_schema=[{"section": "Custom", "fields": [custom]}],
            built_in=True,
        )

        await apply_nora_profile(db)

        from sqlalchemy import select

        from app.models.card_type import CardType

        itc = (await db.execute(select(CardType).where(CardType.key == "ITComponent"))).scalar_one()
        cores = [
            f for s in itc.fields_schema for f in s.get("fields", []) if f["key"] == "cpuCores"
        ]
        assert len(cores) == 1
        assert cores[0]["label"] == "My Cores"
