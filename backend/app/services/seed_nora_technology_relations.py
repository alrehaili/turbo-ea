"""NORA Content Meta Model — Technology Architecture connections (§5.3.6.3).

[FORK] NORA exact-fidelity metamodel (noraPlanMeta.md, Phase 2).

Wires the nine new Technology building blocks (see ``seed_nora_technology``) into
the metamodel with the document's §5.3.6.3 connections — the hosts / manages /
uses-license / linked-through / owned-by / provided-by backbone.

Respects the **one-relation-type-per-ordered-pair** rule (CLAUDE.md): every
``(source, target)`` pair below is unique and does not collide with a relation
already defined in ``seed.RELATIONS``. Appended onto ``seed.RELATIONS`` so the
standard seed loop and ``test_i18n_seed`` (which checks label + reverse_label in
all nine non-English locales) pick them up.
"""

from __future__ import annotations

from app.services.seed_nora_technology import _tx

# ---------------------------------------------------------------------------
# Verb registry — forward/reverse English + 9-locale translations, reused across
# every pair that shares the verb so the wording stays consistent and DRY.
# ---------------------------------------------------------------------------

_VERBS: dict[str, dict] = {
    "hosts": {
        "label": "hosts",
        "reverse_label": "is hosted in",
        "cardinality": "1:n",
        "label_tx": _tx(
            de="hostet",
            fr="héberge",
            es="aloja",
            it="ospita",
            pt="aloja",
            zh="托管",
            ru="размещает",
            da="hoster",
            ar="يستضيف",
        ),
        "reverse_tx": _tx(
            de="wird gehostet in",
            fr="est hébergé dans",
            es="está alojado en",
            it="è ospitato in",
            pt="está alojado em",
            zh="托管于",
            ru="размещается в",
            da="hostes i",
            ar="مُستضاف في",
        ),
    },
    "manages": {
        "label": "manages",
        "reverse_label": "is managed by",
        "cardinality": "1:n",
        "label_tx": _tx(
            de="verwaltet",
            fr="gère",
            es="gestiona",
            it="gestisce",
            pt="gere",
            zh="管理",
            ru="управляет",
            da="administrerer",
            ar="يدير",
        ),
        "reverse_tx": _tx(
            de="wird verwaltet von",
            fr="est géré par",
            es="es gestionado por",
            it="è gestito da",
            pt="é gerido por",
            zh="由…管理",
            ru="управляется",
            da="administreres af",
            ar="يُدار بواسطة",
        ),
    },
    "uses": {
        "label": "uses",
        "reverse_label": "is used by",
        "cardinality": "n:m",
        "label_tx": _tx(
            de="verwendet",
            fr="utilise",
            es="utiliza",
            it="utilizza",
            pt="utiliza",
            zh="使用",
            ru="использует",
            da="bruger",
            ar="يستخدم",
        ),
        "reverse_tx": _tx(
            de="wird verwendet von",
            fr="est utilisé par",
            es="es utilizado por",
            it="è utilizzato da",
            pt="é utilizado por",
            zh="被…使用",
            ru="используется",
            da="bruges af",
            ar="يُستخدم بواسطة",
        ),
    },
    "linkedThrough": {
        "label": "is linked through",
        "reverse_label": "links",
        "cardinality": "n:m",
        "label_tx": _tx(
            de="ist verbunden über",
            fr="est relié via",
            es="está enlazado a través de",
            it="è collegato tramite",
            pt="está ligado através de",
            zh="通过…连接",
            ru="связан через",
            da="er forbundet via",
            ar="مرتبط عبر",
        ),
        "reverse_tx": _tx(
            de="verbindet",
            fr="relie",
            es="enlaza",
            it="collega",
            pt="liga",
            zh="连接",
            ru="связывает",
            da="forbinder",
            ar="يربط",
        ),
    },
    "ownedBy": {
        "label": "is owned by",
        "reverse_label": "owns",
        "cardinality": "n:1",
        "label_tx": _tx(
            de="gehört",
            fr="appartient à",
            es="es propiedad de",
            it="è di proprietà di",
            pt="pertence a",
            zh="归属于",
            ru="принадлежит",
            da="ejes af",
            ar="مملوك لـ",
        ),
        "reverse_tx": _tx(
            de="besitzt",
            fr="possède",
            es="posee",
            it="possiede",
            pt="possui",
            zh="拥有",
            ru="владеет",
            da="ejer",
            ar="يملك",
        ),
    },
    "providedBy": {
        "label": "is provided by",
        "reverse_label": "provides",
        "cardinality": "n:1",
        "label_tx": _tx(
            de="wird bereitgestellt von",
            fr="est fourni par",
            es="es proporcionado por",
            it="è fornito da",
            pt="é fornecido por",
            zh="由…提供",
            ru="предоставляется",
            da="leveres af",
            ar="مُقدَّم من",
        ),
        "reverse_tx": _tx(
            de="stellt bereit",
            fr="fournit",
            es="proporciona",
            it="fornisce",
            pt="fornece",
            zh="提供",
            ru="предоставляет",
            da="leverer",
            ar="يوفّر",
        ),
    },
}

# ---------------------------------------------------------------------------
# (verb, source_type_key, target_type_key) — one unique ordered pair each.
# ---------------------------------------------------------------------------

_TECH = [
    "Server",
    "PhysicalHost",
    "NetworkDevice",
    "Storage",
    "ContainerizationEngine",
    "InfrastructureService",
    "InfrastructureManagementTool",
    "PeripheralDevice",
]

_PAIRS: list[tuple[str, str, str]] = []

# Data Center hosts every infrastructure block
for _t in _TECH:
    _PAIRS.append(("hosts", "Datacenter", _t))
# Physical host hosts servers; servers/storage host higher-layer artifacts
_PAIRS += [
    ("hosts", "PhysicalHost", "Server"),
    ("hosts", "Server", "Application"),
    ("hosts", "Server", "DataVault"),
    ("hosts", "Storage", "DataVault"),
]
# Infrastructure Management Tool manages the infrastructure fleet + circuits
for _t in [
    "PhysicalHost",
    "Server",
    "NetworkDevice",
    "Storage",
    "ContainerizationEngine",
    "PeripheralDevice",
    "InfrastructureService",
    "NetworkCircuit",
]:
    _PAIRS.append(("manages", "InfrastructureManagementTool", _t))
# Each block consumes licenses
for _t in _TECH:
    _PAIRS.append(("uses", _t, "License"))
# Network-attached blocks are linked through a network circuit
for _t in ["PhysicalHost", "NetworkDevice", "Storage", "PeripheralDevice"]:
    _PAIRS.append(("linkedThrough", _t, "NetworkCircuit"))
# Ownership by an organizational unit (NORA-native type, Phase 1B)
for _t in _TECH + ["License", "NetworkCircuit"]:
    _PAIRS.append(("ownedBy", _t, "OrganizationalUnit"))
# Supply by a service provider (NORA-native type, Phase 1B)
for _t in _TECH + ["License"]:
    _PAIRS.append(("providedBy", _t, "ServiceProvider"))


def _key(src: str, tgt: str) -> str:
    return f"relNora{src}{tgt}"


NORA_TECHNOLOGY_RELATIONS: list[dict] = []
for _i, (_verb, _src, _tgt) in enumerate(_PAIRS):
    _v = _VERBS[_verb]
    NORA_TECHNOLOGY_RELATIONS.append(
        {
            "key": _key(_src, _tgt),
            "label": _v["label"],
            "reverse_label": _v["reverse_label"],
            "source_type_key": _src,
            "target_type_key": _tgt,
            "cardinality": _v["cardinality"],
            "sort_order": 600 + _i,
            "translations": {
                "label": _v["label_tx"],
                "reverse_label": _v["reverse_tx"],
            },
        }
    )
