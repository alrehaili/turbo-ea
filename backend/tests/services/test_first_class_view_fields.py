"""The change-governance views read first-class metamodel fields.

Guards migration 158 + the seed defaults: the Executive Strategy Map,
Resilience / Critical Service and Data Flow Map views used to read a KPI,
RTO/RPO and Data Domain value opportunistically from ``cards.attributes``.
Those keys are now first-class fields on the built-in card types, so the field
keys the services read must match the field keys the seed defines. No database
is required.
"""

from __future__ import annotations

from app.services.seed import TYPES


def _field_keys(type_key: str, section_name: str) -> set[str]:
    card_type = next(t for t in TYPES if t["key"] == type_key)
    section = next(s for s in card_type["fields_schema"] if s.get("section") == section_name)
    return {f["key"] for f in section["fields"]}


def test_objective_has_first_class_kpi_field():
    assert "kpi" in _field_keys("Objective", "Objective Information")


def test_application_has_first_class_resilience_fields():
    keys = _field_keys("Application", "Assessment")
    assert {"rto", "rpo", "recoveryTier"} <= keys


def test_data_object_has_first_class_data_domain_field():
    assert "dataDomain" in _field_keys("DataObject", "Data Information")
