"""NORA/DGA data-collection template adapter — implements ``MigrationSource``.

[FORK FEATURE] — noraPlan.md WP6.6.

Ingests the six official حصر البيانات workbooks of the updated (Dec-2024)
Saudi National EA Framework: Business, Applications, Technology, Security,
Data and Beneficiary-Experience architecture. One upload = one workbook;
cross-workbook name references (services → applications, …) resolve via
the shared identity map, so agencies can upload the domains in any order
and re-run safely.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.migration.snapshot import MigrationSnapshot, SourceEntity
from app.services.migration.sources.nora_xlsx import mappings, xlsx_parser


class NoraXlsxSource:
    """DGA NORA data-collection template (حصر البيانات) adapter."""

    key: str = "nora_xlsx"
    label: str = "NORA data-collection templates (DGA)"
    accepted_extensions: tuple[str, ...] = (".xlsx",)

    # ---- Mapping tables ----
    type_mapping: dict[str, str] = mappings.TYPE_MAPPING
    relation_mapping: dict[str, str] = mappings.RELATION_MAPPING
    flip_direction: frozenset[str] = mappings.FLIP_DIRECTION
    field_type_mapping: dict[str, str] = mappings.FIELD_TYPE_MAPPING
    subscription_role_mapping: dict[str, str] = mappings.SUBSCRIPTION_ROLE_MAPPING
    hierarchy_relations: frozenset[str] = mappings.HIERARCHY_RELATIONS

    # Template columns the parser routes into canonical slots or NORA
    # profile fields automatically — surfaced verbatim in the admin's
    # "Map imported fields" tab.
    auto_mapped_columns: tuple[tuple[str, str], ...] = (
        ("اسم الخدمة / الاسم / اسم المضيف", "name"),
        ("وصف الخدمة / الوصف", "description"),
        ("الخدمة الأساسية", "parent (hierarchy)"),
        ("تصنيف / نوع / مستوى أتمتة الخدمة", "NORA profile fields"),
        ("قنوات التقديم / نوع المستفيد / مستوى النضج", "NORA profile fields"),
        ("التطبيقات المستخدمة / الأنظمة المستخدمة", "relations"),
        ("المستهلك / المنتج (نقاط الربط)", "relations"),
        ("حالة التطبيق + تاريخ الإطلاق", "lifecycle"),
        ("التكاليف الرأسمالية والتشغيلية", "cost fields"),
        ("أعمدة الدعم والتشغيل (البنية التقنية والأمن)", "NORA profile fields"),
    )

    # ---- Parsing ----
    def validate_payload(self, head: bytes) -> bool:
        return xlsx_parser.is_xlsx_payload(head)

    def parse(self, path: str | Path) -> MigrationSnapshot:
        return xlsx_parser.parse_xlsx_path(path)

    # ---- Extension hooks ----
    def post_build_card_payload(
        self,
        entity: SourceEntity,
        target_type: str,
        payload: dict[str, Any],
    ) -> None:
        """NORA-template quirks on the generic card payload.

        Stub entities (created only because another row referenced them by
        name) must never blank fields on an existing card they match — drop
        the empty description so the apply pass leaves it untouched, and tag
        the origin so admins can find un-enriched stubs after import.
        """
        if entity.raw.get("nora_stub"):
            payload.pop("description", None)
            attrs = payload.setdefault("attributes", {})
            attrs.setdefault("source_origin", f"{self.key}:referenced")

    def map_subscription_role(
        self,
        role_name: str | None,
        role_type: str | None,
    ) -> str:
        """The templates carry no importable subscriptions (names without
        emails) — conventional fallback only."""
        if role_type and role_type.upper() == "OBSERVER":
            return "observer"
        return "responsible"
