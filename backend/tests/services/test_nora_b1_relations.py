"""B1 relationship coverage guard ([FORK] NORAreadiness.md B-7).

Every pair of building blocks that the June 2025 Content Meta Model guideline
(B1, §5.3.x.3 relationship tables) relates must have a relation type in the
NORA metamodel, in either direction: the app keeps one type per pair and names
the other end with its reverse label. Same-type links (Vision → Vision,
KPI → KPI, …) are listed in Appendix B-7 and are not in this list yet.
"""

from __future__ import annotations

import pytest

# (source, target) as B1 lists them, grouped by B1 domain. Pairs that B1
# lists from both ends appear once.
B1_PAIRS: list[tuple[str, str]] = [
    # Strategy
    ("Vision", "Mission"),
    ("Vision", "OrganizationalUnit"),
    ("Mission", "Objective"),
    ("Objective", "Pillar"),
    ("Objective", "Initiative"),
    ("Objective", "OrganizationalUnit"),
    ("Objective", "KPI"),
    ("Pillar", "Initiative"),
    ("Initiative", "Project"),
    ("Initiative", "OrganizationalUnit"),
    ("Initiative", "KPI"),
    ("Project", "OrganizationalUnit"),
    ("Project", "KPI"),
    ("Project", "ServiceProvider"),
    ("KPI", "OrganizationalUnit"),
    ("KPI", "GovService"),
    ("KPI", "BusinessProcess"),
    # Business
    ("BusinessCapability", "OrganizationalUnit"),
    ("BusinessCapability", "ProcessesGroup"),
    ("BusinessCapability", "DataObject"),
    ("OrganizationalUnit", "GovService"),
    ("OrganizationalUnit", "DataObject"),
    ("OrganizationalUnit", "Position"),
    ("OrganizationalUnit", "ServiceProvider"),
    ("ServiceProvider", "GovService"),
    ("GovService", "BusinessProcess"),
    ("GovService", "Beneficiary"),
    ("GovService", "ModelTemplate"),
    ("GovService", "Product"),
    ("GovService", "Application"),
    ("ProcessesGroup", "BusinessProcess"),
    ("ProcessesGroup", "Position"),
    ("BusinessProcess", "ModelTemplate"),
    ("BusinessProcess", "Role"),
    ("BusinessProcess", "Policy"),
    ("BusinessProcess", "Product"),
    ("BusinessProcess", "Activity"),
    ("BusinessProcess", "Application"),
    ("Activity", "Role"),
    ("Activity", "Policy"),
    ("Product", "Beneficiary"),
    ("Product", "OrganizationalUnit"),
    ("Product", "Application"),
    ("Position", "Role"),
    ("Role", "DataObject"),
    ("Policy", "DataObject"),
    ("ModelTemplate", "DataObject"),
    # Beneficiary
    ("Beneficiary", "ServiceProvider"),
    ("Beneficiary", "OrganizationalUnit"),
    ("Beneficiary", "Persona"),
    ("BeneficiaryJourney", "Phase"),
    ("BeneficiaryJourney", "Persona"),
    ("Step", "Phase"),
    # Data
    ("DataObject", "DataAttribute"),
    ("DataObject", "DataVault"),
    ("DataObject", "Application"),
    ("DataVault", "Storage"),
    ("DataVault", "Server"),
    ("DataVault", "SecurityHardware"),
    ("DataVault", "SecuritySoftware"),
    ("DataVault", "SecurityService"),
    # Application
    ("Application", "ApplicationModule"),
    ("Application", "Interface"),
    ("Application", "Beneficiary"),
    ("Application", "Role"),
    ("Application", "OrganizationalUnit"),
    ("Application", "SecuritySoftware"),
    ("Application", "SecurityHardware"),
    ("Application", "SecurityService"),
    ("Application", "Server"),
    ("ApplicationModule", "ApplicationFunction"),
    ("ApplicationModule", "SecuritySoftware"),
    ("ApplicationModule", "SecurityHardware"),
    ("ApplicationModule", "SecurityService"),
    ("ApplicationFunction", "Interface"),
    ("ApplicationFunction", "SecuritySoftware"),
    ("ApplicationFunction", "SecurityService"),
    ("Interface", "DataObject"),
    ("Interface", "SecuritySoftware"),
    ("Interface", "SecurityService"),
    # Technology
    ("Datacenter", "ServiceProvider"),
    ("Datacenter", "InfrastructureService"),
    ("Datacenter", "PeripheralDevice"),
    ("Datacenter", "PhysicalHost"),
    ("Datacenter", "Server"),
    ("Datacenter", "NetworkDevice"),
    ("Datacenter", "Storage"),
    ("Datacenter", "ContainerizationEngine"),
    ("Datacenter", "InfrastructureManagementTool"),
    ("Datacenter", "NetworkCircuit"),
    ("Datacenter", "SecurityHardware"),
    ("Datacenter", "SecuritySoftware"),
    ("PhysicalHost", "Server"),
    ("PhysicalHost", "InfrastructureManagementTool"),
    ("PhysicalHost", "License"),
    ("PhysicalHost", "NetworkCircuit"),
    ("PhysicalHost", "ServiceProvider"),
    ("PhysicalHost", "OrganizationalUnit"),
    ("PhysicalHost", "SecurityHardware"),
    ("PhysicalHost", "SecuritySoftware"),
    ("PhysicalHost", "SecurityService"),
    ("Server", "License"),
    ("Server", "InfrastructureManagementTool"),
    ("Server", "ServiceProvider"),
    ("Server", "OrganizationalUnit"),
    ("Server", "SecurityHardware"),
    ("Server", "SecuritySoftware"),
    ("Server", "SecurityService"),
    ("NetworkDevice", "InfrastructureManagementTool"),
    ("NetworkDevice", "License"),
    ("NetworkDevice", "NetworkCircuit"),
    ("NetworkDevice", "ServiceProvider"),
    ("NetworkDevice", "OrganizationalUnit"),
    ("NetworkDevice", "SecurityHardware"),
    ("NetworkDevice", "SecuritySoftware"),
    ("NetworkDevice", "SecurityService"),
    ("NetworkCircuit", "OrganizationalUnit"),
    ("NetworkCircuit", "ServiceProvider"),
    ("NetworkCircuit", "InfrastructureManagementTool"),
    ("NetworkCircuit", "PeripheralDevice"),
    ("NetworkCircuit", "Storage"),
    ("NetworkCircuit", "SecurityHardware"),
    ("NetworkCircuit", "SecuritySoftware"),
    ("NetworkCircuit", "SecurityService"),
    ("Storage", "InfrastructureManagementTool"),
    ("Storage", "ServiceProvider"),
    ("Storage", "OrganizationalUnit"),
    ("Storage", "SecurityHardware"),
    ("Storage", "SecuritySoftware"),
    ("Storage", "SecurityService"),
    ("ContainerizationEngine", "InfrastructureManagementTool"),
    ("ContainerizationEngine", "ServiceProvider"),
    ("ContainerizationEngine", "OrganizationalUnit"),
    ("ContainerizationEngine", "SecurityHardware"),
    ("ContainerizationEngine", "SecuritySoftware"),
    ("ContainerizationEngine", "SecurityService"),
    ("InfrastructureManagementTool", "PeripheralDevice"),
    ("InfrastructureManagementTool", "InfrastructureService"),
    ("InfrastructureManagementTool", "OrganizationalUnit"),
    ("InfrastructureManagementTool", "ServiceProvider"),
    ("InfrastructureManagementTool", "SecurityHardware"),
    ("InfrastructureManagementTool", "SecuritySoftware"),
    ("InfrastructureManagementTool", "SecurityService"),
    ("InfrastructureManagementTool", "Interface"),
    ("InfrastructureManagementTool", "Application"),
    ("License", "InfrastructureManagementTool"),
    ("License", "InfrastructureService"),
    ("License", "ContainerizationEngine"),
    ("License", "Storage"),
    ("License", "PeripheralDevice"),
    ("License", "OrganizationalUnit"),
    ("License", "ServiceProvider"),
    ("License", "SecurityHardware"),
    ("License", "SecuritySoftware"),
    ("PeripheralDevice", "ServiceProvider"),
    ("PeripheralDevice", "OrganizationalUnit"),
    ("PeripheralDevice", "SecurityHardware"),
    ("PeripheralDevice", "SecuritySoftware"),
    ("PeripheralDevice", "SecurityService"),
    ("InfrastructureService", "ServiceProvider"),
    ("InfrastructureService", "OrganizationalUnit"),
    ("InfrastructureService", "SecurityHardware"),
    ("InfrastructureService", "SecuritySoftware"),
    ("InfrastructureService", "SecurityService"),
    # Security
    ("SecurityHardware", "ServiceProvider"),
    ("SecurityHardware", "OrganizationalUnit"),
    ("SecurityHardware", "Interface"),
    ("SecurityHardware", "ApplicationFunction"),
    ("SecuritySoftware", "ServiceProvider"),
    ("SecuritySoftware", "OrganizationalUnit"),
    ("SecurityService", "Datacenter"),
    ("SecurityService", "License"),
    ("SecurityService", "ServiceProvider"),
    ("SecurityService", "OrganizationalUnit"),
]


def _relation_types() -> list[dict]:
    from app.services.nora_profile import NORA_RELATION_TYPES
    from app.services.seed import RELATIONS

    return list(RELATIONS) + list(NORA_RELATION_TYPES)


def _pairs() -> set[frozenset[str]]:
    return {frozenset((r["source_type_key"], r["target_type_key"])) for r in _relation_types()}


def test_the_list_has_every_b1_pair_once():
    assert len(B1_PAIRS) == 174
    assert len({frozenset(p) for p in B1_PAIRS}) == len(B1_PAIRS)
    assert all(s != t for s, t in B1_PAIRS)


@pytest.mark.parametrize(("source", "target"), B1_PAIRS)
def test_every_b1_pair_has_a_relation_type(source, target):
    assert frozenset((source, target)) in _pairs(), (
        f"no relation type between {source} and {target}"
    )


def test_b1_pairs_connect_visible_nora_types():
    from app.services.nora_profile import NORA_HIDDEN_TYPE_KEYS

    hidden = set(NORA_HIDDEN_TYPE_KEYS)
    assert not [p for p in B1_PAIRS if hidden & set(p)]


def test_b7_relation_types_are_translated_and_unique():
    from app.services.seed_nora_domain_relations import NORA_DOMAIN_RELATIONS

    keys = [r["key"] for r in _relation_types()]
    assert len(keys) == len(set(keys))
    added = {
        ("InfrastructureManagementTool", "Application"),
        ("SecurityService", "ServiceProvider"),
        ("Objective", "OrganizationalUnit"),
        ("Datacenter", "SecurityHardware"),
        ("ApplicationFunction", "SecurityHardware"),
    }
    by_pair = {(r["source_type_key"], r["target_type_key"]): r for r in NORA_DOMAIN_RELATIONS}
    for pair in added:
        rel = by_pair[pair]
        assert rel["translations"]["label"]["ar"]
        assert rel["translations"]["reverse_label"]["ar"]
    assert by_pair[("InfrastructureManagementTool", "Application")]["label"] == "supports"
    assert by_pair[("Datacenter", "SecurityHardware")]["label"] == "hosts"


def test_operational_kpi_contributes_to_strategic_kpi():
    # B1 §5.3.1.3: every strategic KPI links to one or more operational KPIs.
    from app.services.nora_profile import NORA_RELATION_TYPES

    rel = next(r for r in NORA_RELATION_TYPES if r["key"] == "relKPIToKPI")
    assert (rel["source_type_key"], rel["target_type_key"]) == ("KPI", "KPI")
    assert (rel["label"], rel["reverse_label"]) == ("contributes to", "is supported by")
    assert rel["cardinality"] == "n:m"
    assert rel["translations"]["label"]["ar"] == "يساهم في"
