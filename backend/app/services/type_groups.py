"""Shared card-type groupings for cross-profile module wiring.

[FORK] NORA exact-fidelity metamodel (noraPlanMeta.md, Phase 4).

The tool's tech-layer modules (EOL, compliance, cost, landscape) were originally
keyed to the single generic ``ITComponent`` type. Under the exact NORA metamodel
the technology layer is split across dedicated building blocks
(Server, PhysicalHost, …). These constants let those modules recognise the
NORA-native technology types **and** the classic ``ITComponent`` so they work
under both the NORA and TOGAF profiles without per-module hardcoding.

Keep this the single source of truth — modules import from here rather than
inlining a type-key list.
"""

from __future__ import annotations

# NORA technology-domain component building blocks (§5.3.6) that carry a
# support-end date / cost and behave like the classic ITComponent.
NORA_TECH_COMPONENT_TYPE_KEYS: list[str] = [
    "Server",
    "PhysicalHost",
    "NetworkDevice",
    "Storage",
    "ContainerizationEngine",
    "InfrastructureService",
    "InfrastructureManagementTool",
    "PeripheralDevice",
    "License",
]

# Container / link technology types (grouped separately — they host or connect
# the components above rather than being lifecycle-tracked hardware).
NORA_TECH_CONTAINER_TYPE_KEYS: list[str] = [
    "Datacenter",
    "NetworkCircuit",
]

# Everything the tool historically treated as "an ITComponent" for tech-layer
# reports/features — the generic type plus its NORA-native replacements.
INFRASTRUCTURE_TYPE_KEYS: list[str] = ["ITComponent", *NORA_TECH_COMPONENT_TYPE_KEYS]

# Types eligible for End-of-Life tracking: Applications plus all infrastructure.
EOL_TYPE_KEYS: list[str] = ["Application", *INFRASTRUCTURE_TYPE_KEYS]

# NORA-native security building blocks (§5.3.7).
SECURITY_TYPE_KEYS: list[str] = ["SecurityHardware", "SecuritySoftware", "SecurityService"]

# All types shown in the technology-landscape report, across both profiles.
TECH_LANDSCAPE_TYPE_KEYS: list[str] = [
    "ITComponent",
    "Datacenter",
    "NetworkCircuit",
    *NORA_TECH_COMPONENT_TYPE_KEYS,
    *SECURITY_TYPE_KEYS,
]

# The data-center hosts these directly (License is a usage agreement, not hosted
# hardware, so it is excluded from physical containment).
_DATACENTER_HOSTED_TYPE_KEYS: list[str] = [
    k for k in NORA_TECH_COMPONENT_TYPE_KEYS if k != "License"
]

# Relation-type keys that express physical containment in the technology
# landscape (data-center ⊃ component, physical-host ⊃ server). Mirrors the key
# format produced by seed_nora_technology_relations (``relNora{src}{tgt}``).
TECH_CONTAINMENT_RELATION_KEYS: list[str] = [
    f"relNoraDatacenter{k}" for k in _DATACENTER_HOSTED_TYPE_KEYS
] + ["relNoraPhysicalHostServer"]
