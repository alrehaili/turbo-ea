"""Unit tests for the Reference Models xlsx build/parse helpers ([FORK] —
noraPlan.md WP100.3). Pure — no database required."""

from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook

from app.services.reference_models import (
    RM_EXPORT_HEADERS,
    STARTER_REFERENCE_MODELS,
    parse_rm_workbook,
)


def _workbook_bytes(rows: list[list], headers: list[str] | None = None) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(headers or RM_EXPORT_HEADERS)
    for row in rows:
        ws.append(row)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


class TestParseRmWorkbook:
    def test_happy_path_with_hierarchy(self):
        data = _workbook_bytes(
            [
                ["BRM-1", None, "Core Capabilities", "القدرات الأساسية", "Top level", 0],
                ["BRM-1.1", "BRM-1", "Payments", None, None, 1],
                ["BRM-1.2", "BRM-1", "Licensing", "التراخيص", "", 2],
            ]
        )
        rows, errors = parse_rm_workbook(data)
        assert errors == []
        assert len(rows) == 3
        root = rows[0]
        assert root["code"] == "BRM-1"
        assert root["parent_code"] is None
        assert root["name_ar"] == "القدرات الأساسية"
        assert rows[1]["parent_code"] == "BRM-1"
        assert rows[2]["name_ar"] == "التراخيص"
        assert rows[2]["description"] is None  # empty string folds to None
        assert rows[2]["sort_order"] == 2

    def test_duplicate_code_reported_and_skipped(self):
        data = _workbook_bytes(
            [
                ["A", None, "First", None, None, 0],
                ["A", None, "Duplicate", None, None, 1],
            ]
        )
        rows, errors = parse_rm_workbook(data)
        assert len(rows) == 1
        assert any("duplicate code 'A'" in e for e in errors)

    def test_unknown_parent_becomes_root_with_warning(self):
        data = _workbook_bytes([["B", "MISSING", "Orphan", None, None, 0]])
        rows, errors = parse_rm_workbook(data)
        assert rows[0]["parent_code"] is None
        assert any("MISSING" in e for e in errors)

    def test_missing_code_or_name_skipped(self):
        data = _workbook_bytes(
            [
                [None, None, "No code", None, None, 0],
                ["C", None, None, None, None, 0],
                [None, None, None, None, None, None],  # blank spacer — silent
                ["D", None, "Valid", None, None, 0],
            ]
        )
        rows, errors = parse_rm_workbook(data)
        assert [r["code"] for r in rows] == ["D"]
        assert len(errors) == 2

    def test_header_row_must_carry_code_and_name(self):
        data = _workbook_bytes([["x"]], headers=["Something", "Else"])
        rows, errors = parse_rm_workbook(data)
        assert rows == []
        assert errors

    def test_not_an_xlsx(self):
        rows, errors = parse_rm_workbook(b"definitely not a workbook")
        assert rows == []
        assert errors

    def test_tolerant_headers_arabic(self):
        data = _workbook_bytes(
            [["X-1", None, "خدمة", "خدمة رقمية", None, 0]],
            headers=["الرمز", "رمز الأصل", "الاسم", "الاسم بالعربية", "الوصف", "الترتيب"],
        )
        rows, errors = parse_rm_workbook(data)
        assert errors == []
        assert rows[0]["code"] == "X-1"
        assert rows[0]["name"] == "خدمة"
        assert rows[0]["name_ar"] == "خدمة رقمية"


class TestStarterDefinitions:
    def test_starters_cover_business_and_applications(self):
        domains = {s["domain"] for s in STARTER_REFERENCE_MODELS}
        assert domains == {"business", "applications"}

    def test_starters_are_arabic_first_class(self):
        for starter in STARTER_REFERENCE_MODELS:
            assert starter["name_ar"], f"{starter['key']} missing Arabic name"
            for code, _name, name_ar in starter["items"]:
                assert name_ar, f"{starter['key']}/{code} missing Arabic name"

    def test_starter_codes_unique_per_model(self):
        for starter in STARTER_REFERENCE_MODELS:
            codes = [code for code, _n, _a in starter["items"]]
            assert len(codes) == len(set(codes))
