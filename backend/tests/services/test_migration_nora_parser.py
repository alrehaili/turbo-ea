"""Unit tests for the NORA/DGA data-collection template parser ([FORK] WP6.6).

Synthetic workbooks built in-memory mirror the official حصر البيانات layout
(row 1 title, row 2 Arabic headers, row 3 explanations, row 4+ data) —
never real agency data.
"""

from __future__ import annotations

from openpyxl import Workbook  # type: ignore[import-untyped]

from app.services.migration.registry import SOURCES
from app.services.migration.sources.nora_xlsx.xlsx_parser import (
    _entity_id,
    is_xlsx_payload,
    parse_xlsx_path,
)


def _write_sheet(wb: Workbook, name: str, rows: list[list]) -> None:
    if wb.sheetnames == ["Sheet"]:
        ws = wb.active
        ws.title = name
    else:
        ws = wb.create_sheet(name)
    for row in rows:
        ws.append(row)


def _save(wb: Workbook, tmp_path) -> str:
    p = tmp_path / "template.xlsx"
    wb.save(p)
    return str(p)


def _by_id(snapshot):
    return {e.source_id: e for e in snapshot.entities}


# ---------------------------------------------------------------------------
# Business architecture workbook
# ---------------------------------------------------------------------------


def _business_workbook() -> Workbook:
    wb = Workbook()
    _write_sheet(wb, "المقدمة", [["مقدمة"]])
    _write_sheet(
        wb,
        "دليل الخدمات",
        [
            ["دليل الخدمات"],
            [
                "رمز الخدمة",
                "اسم الخدمة",
                "وصف الخدمة",
                "تصنيف الخدمة",
                "الخدمة الأساسية",
                "نوع الخدمة",
                "مستوى أتمتة الخدمة",
                "التطبيقات المستخدمة لتنفيذ الخدمة",
                "التغطية الجغرافية للخدمة",
                "قنوات تقديم الخدمة",
                "نوع المستفيد من الخدمة",
                "",
                "",
                "مستوى نضج الخدمة",
                "وجود رسوم الخدمة",
                "معدل طلبات الخدمة شهريا",
                "اتفاقية مستوى الخدمة",
            ],
            [
                "شرح",
                "شرح",
                "شرح",
                "شرح",
                "شرح",
                "شرح",
                "شرح",
                "شرح",
                "شرح",
                "شرح",
                "أفراد",
                "قطاع أعمال",
                "جهات حكومية",
                "شرح",
                "شرح",
                "شرح",
                "شرح",
            ],
            [
                "S02",
                "خدمة تقديم شكوى",
                "استلام شكاوى المستفيدين",
                "فرعي",
                "خدمة العناية بالمستفيدين",
                "داعمة",
                "مؤتمت جزئيا",
                "نظام إدارة الشكاوى\nبوابة الجهة",
                "كافة مناطق المملكة",
                "•مركز الاتصال بالجهة\n•الموقع الإلكتروني للجهة\n•تطبيق الأجهزة الذكية",
                "نعم",
                "نعم",
                "لا",
                "تفاعلية",
                "لا",
                "7500 مرة",
                "10 أيام عمل",
            ],
        ],
    )
    _write_sheet(
        wb,
        "دليل الإجراءات",
        [
            ["دليل الإجراءات"],
            [
                "رمز الإجراء",
                "اسم الإجراء",
                "وصف الإجراء",
                "تصنيف الإجراء",
                "مستوى أتمتة الإجراء",
                "الأنظمة المستخدمة لتنفيذ الإجراء",
                "خدمات ذات علاقة",
                "مدة تنفيذ إجراء العمل",
                "حدث الإطلاق",
                "قواعد العمل",
            ],
            ["شرح"] * 10,
            [
                "P01",
                "معالجة شكاوى المستفيدين",
                "التعامل مع الشكاوى",
                "رئيسي",
                "مؤتمت جزئيا",
                "نظام إدارة الشكاوى",
                "خدمة تقديم شكوى",
                "14 يوم عمل",
                "استقبال شكوى",
                "تصنيف الشكاوى حسب طبيعتها",
            ],
        ],
    )
    _write_sheet(wb, "Lookups", [["رئيسي"]])
    return wb


def test_business_workbook_services_and_processes(tmp_path):
    snapshot = parse_xlsx_path(_save(_business_workbook(), tmp_path))
    ents = _by_id(snapshot)

    svc = ents["nora:GovService:خدمه تقديم شكوي"]
    assert svc.type == "GovService"
    assert svc.name == "خدمة تقديم شكوى"
    assert svc.description == "استلام شكاوى المستفيدين"
    attrs = svc.custom_fields
    assert attrs["serviceCode"] == "S02"
    assert attrs["serviceClassification"] == "sub"
    assert attrs["serviceType"] == "supporting"
    assert attrs["automationLevel"] == "partiallyAutomated"
    assert attrs["geoCoverage"] == "كافة مناطق المملكة"
    assert set(attrs["deliveryChannel"]) == {"callCenter", "portal", "mobileApp"}
    assert attrs["beneficiaryType"] == ["citizen", "business"]
    assert attrs["serviceMaturity"] == "interactive"
    assert attrs["feeModel"] == "free"
    assert attrs["monthlyTransactions"] == 7500
    assert attrs["slaDays"] == 10

    # Parent (main service) becomes a stub + hierarchy edge.
    assert svc.parent_id == "nora:GovService:خدمه العنايه بالمستفيدين"
    parent = ents[svc.parent_id]
    assert parent.raw.get("nora_stub") is True

    proc = ents["nora:BusinessProcess:معالجه شكاوي المستفيدين"]
    assert proc.custom_fields["processClassification"] == "main"
    assert proc.custom_fields["automationLevel"] == "partiallyAutomated"
    assert proc.custom_fields["durationDays"] == 14
    assert proc.custom_fields["triggerEvent"] == "استقبال شكوى"

    # Referenced applications are stubbed once, even across sheets.
    app_stub = ents["nora:Application:نظام اداره الشكاوي"]
    assert app_stub.type == "Application"

    rel_types = {(r.type, r.from_entity_id, r.to_entity_id) for r in snapshot.relations}
    assert (
        "serviceToApplication",
        svc.source_id,
        "nora:Application:نظام اداره الشكاوي",
    ) in rel_types
    assert (
        "serviceToApplication",
        svc.source_id,
        "nora:Application:بوابه الجهه",
    ) in rel_types
    # Procedure's related-service column links service → process.
    assert ("serviceToProcess", svc.source_id, proc.source_id) in rel_types
    assert (
        "processToApplication",
        proc.source_id,
        "nora:Application:نظام اداره الشكاوي",
    ) in rel_types

    # Intro + lookup sheets are noted, not imported.
    assert any("المقدمة" in e for e in snapshot.parse_errors)
    assert any("Lookups" in e for e in snapshot.parse_errors)


# ---------------------------------------------------------------------------
# Applications architecture workbook
# ---------------------------------------------------------------------------


def _applications_workbook() -> Workbook:
    wb = Workbook()
    _write_sheet(
        wb,
        "سجل التطبيقات",
        [
            ["سجل التطبيقات"],
            [
                "الاسم",
                "الوصف",
                "الطبقة",
                "عدد المستخدمين",
                "نوع التطوير",
                "نوع المصدر",
                "المقاول",
                "رابط التطبيق",
                "نوع المصادقة",
                "تاريخ الاطلاق",
                "الأهمية",
                "حالة التطبيق",
                "نمط الهيكلية المعيارية",
                "التكلفة الرأسمالية",
                "التكلفة التشغيلية",
            ],
            ["شرح"] * 15,
            [
                "بوابة الجهة الخارجية",
                "تطبيق صفحات ويب",
                "Access Application Layer – طبقة الوصول",
                12000,
                "COTS – كود مصدري جاهز",
                "In-House Development – تم التطوير داخليا",
                "شركة التقنية",
                "http://www.example.gov.sa",
                "الدخول الموحد",
                "2021-12-12",
                "عالية",
                "Active - نشط",
                "N-Tier Architecture",
                "1,000,000 ريال",
                "500,000 ريال",
            ],
        ],
    )
    _write_sheet(
        wb,
        "نقاط الربط التقني",
        [
            ["سجل نقاط الربط التقني"],
            [
                "الرقم",
                "الاسم",
                "الوصف",
                "المستهلك",
                "المنتج",
                "نطاق الربط",
                "المدخلات",
                "المخرجات",
                "منصة التكامل",
                "نوع الربط",
                "طريقة الربط",
                "صيغة البيانات",
            ],
            ["شرح"] * 12,
            [
                "Ex01",
                "استعلام عن العنوان الوطني",
                "ربط مع مركز المعلومات الوطني",
                "بوابة الجهة الخارجية",
                "البريد السعودي - سبل",
                "خارجي",
                "XML {ID}",
                "XML {Name}",
                "منصة التكامل الموحدة",
                "GSB",
                "Web Services",
                "XML",
            ],
        ],
    )
    return wb


def test_applications_workbook(tmp_path):
    snapshot = parse_xlsx_path(_save(_applications_workbook(), tmp_path))
    ents = _by_id(snapshot)

    app = ents["nora:Application:بوابه الجهه الخارجيه"]
    attrs = app.custom_fields
    assert attrs["appLayer"] == "access"
    assert attrs["numberOfUsers"] == 12000
    assert attrs["developmentType"] == "cots"
    assert attrs["sourceType"] == "inHouse"
    assert attrs["contractor"] == "شركة التقنية"
    assert attrs["appUrl"] == "http://www.example.gov.sa"
    assert attrs["launchDate"] == "2021-12-12"
    assert attrs["businessCriticality"] == "businessCritical"
    assert attrs["architecturePattern"] == "nTier"
    assert attrs["costCapex"] == 1000000
    assert attrs["costTotalAnnual"] == 500000
    # Active status + launch date → lifecycle.
    assert app.lifecycle == {"active": "2021-12-12"}

    iface = ents["nora:Interface:استعلام عن العنوان الوطني"]
    assert iface.custom_fields["integrationScope"] == "external"
    assert iface.custom_fields["linkType"] == "gsb"
    assert iface.custom_fields["viaGsb"] is True
    assert iface.custom_fields["protocol"] == "Web Services"
    assert iface.custom_fields["dataFormat"] == "XML"
    assert iface.custom_fields["integrationPlatform"] == "منصة التكامل الموحدة"

    # Consumer resolves to the in-file application, producer to a stub.
    triples = {(r.type, r.from_entity_id, r.to_entity_id) for r in snapshot.relations}
    assert ("applicationToInterface", app.source_id, iface.source_id) in triples
    assert (
        "applicationToInterface",
        "nora:Application:البريد السعودي - سبل",
        iface.source_id,
    ) in triples
    assert ents["nora:Application:البريد السعودي - سبل"].raw.get("nora_stub") is True


# ---------------------------------------------------------------------------
# Technology + Security workbooks
# ---------------------------------------------------------------------------


def test_technology_and_security_sheets(tmp_path):
    wb = Workbook()
    _write_sheet(
        wb,
        "أجهزة المضيف المادي",
        [
            ["دليل أجهزة المضيف المادي"],
            [
                "اسم المضيف",
                "الشركة المصنعة",
                "الطراز",
                "معرف الكتلة",
                "قطاع الشبكة",
                "تاريخ نهاية الدعم حسب المزود",
                "حالة عقد الدعم مع المزود",
                "نوع التشغيل",
                "التكلفة الأولية",
                "التكلفة التشغيلية",
            ],
            ["شرح"] * 10,
            [
                "RYD-Host01",
                "DELL",
                "Tier 3",
                "Cluster01",
                "DMZ",
                "31-12-2028",
                "Active",
                "Internal Team",
                165000,
                50000,
            ],
        ],
    )
    _write_sheet(
        wb,
        "دليل الخوادم الافتراضية",
        [
            ["دليل الخوادم الافتراضية"],
            [
                "اسم المضيف",
                "معرّف الكتلة",
                "قطاع الشبكة",
                "البيئة",
                "النسخ الاحتياطي",
                "التعافي من الكوارث",
                "نوع التشغيل",
                "التكلفة الأولية",
                "التكلفة التشغيلية",
            ],
            ["شرح"] * 9,
            ["RYDVM0081", "RYDCluster01", "DMZ", "Production", "Yes", "No", "Internal Team", 1, 2],
        ],
    )
    _write_sheet(
        wb,
        "برمجيات الأمن",
        [
            ["دليل برمجيات الأمن"],
            [
                "الرمز",
                "الاسم",
                "الشركة المصنعة",
                "الإصدار",
                "تاريخ نهاية الدعم حسب المزود",
                "حالة عقد الدعم مع المزود",
                "نوع التشغيل",
                "التكلفة الأولية",
                "التكلفة التشغيلية",
            ],
            ["شرح"] * 9,
            [
                "SecuritySoftware007",
                "Data Leakage Prevention (DLP)",
                "Symantec",
                "DLP 15.5",
                "31-12-2028",
                "expire",
                "Internal Team",
                750000,
                1750000,
            ],
        ],
    )
    snapshot = parse_xlsx_path(_save(wb, tmp_path))
    ents = _by_id(snapshot)

    host = ents["nora:PhysicalHost:ryd-host01"]
    # The NORA technology building blocks' own fields (§5.3.8), no subtype.
    assert host.category is None
    assert host.custom_fields["manufacturer"] == "DELL"
    assert host.custom_fields["model"] == "Tier 3"
    assert host.custom_fields["clusterId"] == "Cluster01"
    assert host.custom_fields["networkSegment"] == "dmz"
    assert host.custom_fields["supportEndDate"] == "2028-12-31"
    assert host.custom_fields["supportContractStatus"] == "active"
    assert host.custom_fields["typeOfOperation"] == "inHouse"
    assert host.custom_fields["capitalCost"] == 165000
    assert host.custom_fields["operatingCost"] == 50000
    assert not {"modelNumber", "securityZone", "initialCost", "operationType"} & set(
        host.custom_fields
    )

    vm = ents["nora:VirtualServer:rydvm0081"]
    assert vm.category == "virtual"
    assert vm.custom_fields["environment"] == "production"
    assert vm.custom_fields["inBackupPolicy"] is True
    assert vm.custom_fields["inDrPolicy"] is False

    dlp = ents["nora:SecuritySoftware:data leakage prevention (dlp)"]
    assert dlp.category is None
    assert dlp.custom_fields["code"] == "SecuritySoftware007"
    assert dlp.custom_fields["supportContractStatus"] == "expired"
    assert dlp.custom_fields["version"] == "DLP 15.5"


def test_template_types_map_to_visible_nora_types():
    from app.services.migration.sources.nora_xlsx.mappings import TYPE_MAPPING
    from app.services.nora_profile import NORA_HIDDEN_TYPE_KEYS

    assert not set(TYPE_MAPPING.values()) & set(NORA_HIDDEN_TYPE_KEYS)
    assert TYPE_MAPPING["VirtualServer"] == "Server"
    assert TYPE_MAPPING["InfraTool"] == "InfrastructureManagementTool"


def test_every_template_field_exists_on_its_target_type():
    """Each column rule writes a field the NORA type really has, so nothing a
    template carries is stored where no card page shows it."""
    from app.services.migration.sources.nora_xlsx.mappings import TYPE_MAPPING
    from app.services.migration.sources.nora_xlsx.xlsx_parser import _SHEET_SPECS
    from app.services.nora_profile import (
        NORA_CARD_TYPES,
        NORA_SECTIONED_FIELDS,
        NORA_TYPE_FIELDS,
        NORA_V2_TYPE_FIELDS,
        NORA_V4_TYPE_FIELDS,
        NORA_V8_TYPE_FIELDS,
    )
    from app.services.seed import TYPES

    defs = {t["key"]: t for t in TYPES}
    for t in NORA_CARD_TYPES:
        defs.setdefault(t["key"], t)

    def keys(type_key):
        out = {f["key"] for s in defs[type_key].get("fields_schema") or [] for f in s["fields"]}
        for extra in (
            NORA_TYPE_FIELDS,
            NORA_V2_TYPE_FIELDS,
            NORA_V4_TYPE_FIELDS,
            NORA_V8_TYPE_FIELDS,
        ):
            out |= {f["key"] for f in extra.get(type_key, [])}
        out |= {f["key"] for s in NORA_SECTIONED_FIELDS.get(type_key, []) for f in s["fields"]}
        return out

    synthetic = {"__name_en", "__desc_en", "beneficiaryType"}
    missing = []
    for spec in _SHEET_SPECS:
        type_key = TYPE_MAPPING[spec["native_type"]]
        known = keys(type_key)
        for token, rule in spec["columns"]:
            if rule[0] in ("attr", "option", "multi_option", "number", "cost", "date", "bool"):
                if rule[1] not in known and rule[1] not in synthetic:
                    missing.append(f"{type_key}.{rule[1]} ({token})")
    assert not missing


def test_network_device_reads_location_type_and_function(tmp_path):
    wb = Workbook()
    _write_sheet(
        wb,
        "دليل الأجهزة الشبكية",
        [
            ["دليل الأجهزة الشبكية"],
            ["اسم المضيف", "الطراز", "الموقع", "جزء الشبكة", "النوع", "الوظيفة", "نوع التشغيل"],
            ["شرح"] * 7,
            [
                "Core-SW01",
                "Catalyst 9500",
                "HQ",
                "WAN",
                "Switch",
                "Core Switch",
                "Service Provider",
            ],
        ],
    )
    sw = _by_id(parse_xlsx_path(_save(wb, tmp_path)))["nora:NetworkDevice:core-sw01"]
    assert sw.custom_fields == {
        "model": "Catalyst 9500",
        "location": "HQ",
        "networkSegment": "wan",
        "deviceType": "Switch",
        "function": "Core Switch",
        "typeOfOperation": "serviceProvider",
    }


def test_physical_host_reads_hypervisor_cpu_memory_and_storage(tmp_path):
    wb = Workbook()
    _write_sheet(
        wb,
        "أجهزة المضيف المادي",
        [
            ["دليل أجهزة المضيف المادي"],
            [
                "اسم المضيف",
                "نوع مراقب الآلة الافتراضي",
                "إصدار مراقب الآلة الافتراضي",
                "قطاع الشبكة",
                "العدد الكلي لنوى وحدات المعالجة المركزية",
                "المعالج",
                "الذاكرة العشوائية",
                "السعة التخزينية المحلية",
            ],
            ["شرح"] * 8,
            ["RYD-Host02", "ESXi", "6.5.0", "Data Center", 24, "3", 256, 900],
        ],
    )
    host = _by_id(parse_xlsx_path(_save(wb, tmp_path)))["nora:PhysicalHost:ryd-host02"]
    assert host.custom_fields == {
        "hypervisorType": "ESXi",
        "hypervisorVersion": "6.5.0",
        "networkSegment": "dataCenter",
        "physicalCpuCores": 24,
        "centralProcessingUnit": "3",
        "physicalRam": 256,
        "localStorageCapacity": 900,
    }


# ---------------------------------------------------------------------------
# Data + Experience workbooks
# ---------------------------------------------------------------------------


def test_data_dictionary_sheet(tmp_path):
    wb = Workbook()
    _write_sheet(
        wb,
        "دليل قاموس البيانات",
        [
            ["دليل قاموس البيانات"],
            [
                "معرف كيان البيانات",
                "اسم كيان البيانات (انجليزي)",
                "اسم كيان البيانات(عربي)",
                "وصف الكيان (عربي)",
                "وصف الكيان (انجليزي)",
                "نوع البيانات",
                "تصنيف البيانات",
            ],
            ["شرح"] * 7,
            [
                "ENT_1",
                "Employee",
                "موظف",
                "بيانات موظفي الجهة",
                "Employee data",
                "Alphabetical",
                "مقيد",
            ],
        ],
    )
    snapshot = parse_xlsx_path(_save(wb, tmp_path))
    ents = _by_id(snapshot)
    obj = ents["nora:DataObject:موظف"]
    assert obj.type == "DataObject"
    assert obj.name == "موظف"
    assert obj.description == "بيانات موظفي الجهة"
    assert obj.custom_fields["dataType"] == "Alphabetical"
    assert obj.custom_fields["dataClassification"] == "restricted"
    assert obj.custom_fields["__name_en"] == "Employee"


def test_experience_workbook_is_descoped(tmp_path):
    wb = Workbook()
    _write_sheet(
        wb,
        " التحسينات على رحلات المس",
        [
            ["قائمة التحسينات على رحلات المستفيدين"],
            ["رحلة المستفيد", "المرحلة", "الفجوة"],
            ["شرح"] * 3,
            ["رحلة التقديم على شكوى", "المتابعة", "لا يمكن الاطلاع على الحالة"],
        ],
    )
    snapshot = parse_xlsx_path(_save(wb, tmp_path))
    assert snapshot.entities == []
    assert any("التحسينات" in e for e in snapshot.parse_errors)


# ---------------------------------------------------------------------------
# Policy, model/template and data-attribute sheets (NORAreadiness.md B-6)
# ---------------------------------------------------------------------------


def _rels(snapshot):
    return {(r.type, r.from_entity_id, r.to_entity_id) for r in snapshot.relations}


def test_policy_sheet(tmp_path):
    wb = Workbook()
    _write_sheet(
        wb,
        "دليل السياسات",
        [
            ["دليل السياسات"],
            [
                "رمز السياسة",
                "اسم السياسة",
                "وصف السياسة",
                "الإدارة العامة المالكة للسياسة",
                "نوع السياسة",
                "نطاق السياسة",
                "حالة السياسة",
                "تاريخ تفعيل السياسة",
                "قدرة العمل ذات العلاقة",
                "خدمات ذات علاقة",
                "إجراءات ذات علاقة",
                "بنود السياسة",
            ],
            ["شرح"] * 12,
            [
                "P002",
                "سياسة التعامل مع الشكاوى",
                "تهدف السياسة إلى تحديد مبادئ معالجة الشكاوى",
                "الإدارة العامة لحماية حقوق المستفيدين",
                "سياسة داخلية",
                "تنطبق على جميع موظفي الجهة",
                "مفعّلة",
                "2023-01-15",
                "علاقات العملاء",
                "خدمة تقديم شكوى",
                "معالجة شكاوى المستفيدين",
                "البند الأول",
            ],
        ],
    )
    snapshot = parse_xlsx_path(_save(wb, tmp_path))
    policy = _by_id(snapshot)[_entity_id("Policy", "سياسة التعامل مع الشكاوى")]
    assert policy.description == "تهدف السياسة إلى تحديد مبادئ معالجة الشكاوى"
    assert policy.custom_fields == {
        "policyCode": "P002",
        "policyType": "internal",
        "policyScope": "تنطبق على جميع موظفي الجهة",
        "policyStatus": "active",
        "activationDate": "2023-01-15",
        "policyClauses": "البند الأول",
    }
    pid = policy.source_id
    assert _rels(snapshot) == {
        ("policyToService", pid, _entity_id("GovService", "خدمة تقديم شكوى")),
        ("policyToProcess", pid, _entity_id("BusinessProcess", "معالجة شكاوى المستفيدين")),
    }


def test_policy_type_and_status_options():
    from app.services.migration.sources.nora_xlsx import mappings
    from app.services.migration.sources.nora_xlsx.xlsx_parser import _match_option

    assert _match_option("سياسة خارجية/ حكومية", mappings.POLICY_TYPE) == "external"
    assert _match_option("موقوفة", mappings.POLICY_STATUS) == "suspended"
    assert _match_option("ملغيّة", mappings.POLICY_STATUS) == "cancelled"


def test_model_sheet(tmp_path):
    wb = Workbook()
    _write_sheet(
        wb,
        "دليل النماذج",
        [
            ["دليل النماذج"],
            [
                "رمز النموذج",
                "اسم النموذج",
                "وصف النموذج",
                "نوع النموذج",
                "خدمات ذات علاقة",
                "إجراءات ذات علاقة",
                "المرفقات",
            ],
            ["شرح"] * 7,
            [
                "1002",
                "نموذج الشكوى",
                "حصر بيانات الشاكي",
                "نموذج طلب خدمة",
                "خدمة تقديم شكوى",
                "إجراء تقديم شكوى",
                "الوثائق الداعمة",
            ],
        ],
    )
    snapshot = parse_xlsx_path(_save(wb, tmp_path))
    model = _by_id(snapshot)[_entity_id("ModelTemplate", "نموذج الشكوى")]
    assert model.custom_fields == {"code": "1002", "modelType": "serviceRequestForm"}
    mid = model.source_id
    assert _rels(snapshot) == {
        ("serviceToModel", _entity_id("GovService", "خدمة تقديم شكوى"), mid),
        ("processToModel", _entity_id("BusinessProcess", "إجراء تقديم شكوى"), mid),
    }


def _attribute_header(*extra: str) -> list[str]:
    return [
        "معرف كيان البيانات",
        "اسم كيان البيانات (انجليزي)",
        "اسم كيان البيانات(عربي)",
        "معرف سمة البيانات",
        "اسم السمة (انجليزي)",
        "اسم السمة (عربي)",
        *extra,
    ]


def test_data_attribute_sheets_merge_into_one_attribute(tmp_path):
    wb = Workbook()
    # Business catalogue first, as in the template.
    _write_sheet(
        wb,
        "دليل فهرس الأعمال",
        [
            ["فهرس الأعمال"],
            _attribute_header(
                "وصف السمة (انجليزي)",
                "وصف السمة(عربي)",
                "إمكانية قبول الفراغ",
                "عينة من القيم",
                "القوائم المعتمدة لايجاد بيانات محددة",
                "قواعد أعمال السمة",
                "اسم ممثل بيانات الأعمال",
                "اسم مختص بيانات الأعمال",
                "تصنيف البيانات",
            ),
            ["شرح"] * 15,
            [
                "ENT_1",
                "Employee",
                "موظف",
                "ATR1",
                "name",
                "الاسم",
                "employee name",
                "اسم الموظف",
                "N",
                "احمد",
                "N/A",
                "إلزامي",
                "مدير الموارد البشرية",
                "محلل البيانات",
                "مقيد",
            ],
        ],
    )
    _write_sheet(
        wb,
        "دليل سمات البيانات",
        [
            ["سمات البيانات"],
            _attribute_header(
                "نطاق العمل",
                "مصدر البيانات",
                "مفتاح أساسي",
                "إمكانية قبول الفراغ",
                "نوع البيانات",
                "طول البيانات",
                "تنسيق البيانات",
                "اسم ممثل البيانات",
                "اسم مختص البيانات",
                "اسم الجدول في قاعدة البيانات",
                "اسم مخطط قاعدة البيانات",
            ),
            ["شرح"] * 17,
            [
                "ENT_1",
                "Employee",
                "موظف",
                "ATR1",
                "name",
                "الاسم",
                "الموارد البشرية",
                "نظام الموارد",
                "Y",
                "Y",
                "Alphabetical",
                20,
                "Arabic Characters",
                "مدير آخر",
                "مختص آخر",
                "EMPLOYEE",
                "HR",
            ],
        ],
    )
    snapshot = parse_xlsx_path(_save(wb, tmp_path))
    attrs = [e for e in snapshot.entities if e.type == "DataAttribute"]
    assert len(attrs) == 1
    attr = attrs[0]
    assert attr.name == "الاسم"
    assert attr.description == "اسم الموظف"
    assert attr.custom_fields == {
        # From the catalogue (first sheet) — the second sheet never overrides.
        "code": "ATR1",
        "nullable": False,
        "sampleValues": "احمد",
        "lookupSource": "N/A",
        "qualityRules": "إلزامي",
        "dataOwner": "مدير الموارد البشرية",
        "dataSteward": "محلل البيانات",
        "dataClassification": "restricted",
        # Added by the attributes sheet.
        "businessScope": "الموارد البشرية",
        "dataSource": "نظام الموارد",
        "primaryKey": True,
        "dataType": "Alphabetical",
        "dataLength": 20,
        "dataFormat": "Arabic Characters",
        "tableName": "EMPLOYEE",
        "schemaName": "HR",
    }
    assert not snapshot.parse_errors
    assert _rels(snapshot) == {
        ("dataObjectToAttribute", _entity_id("DataObject", "موظف"), attr.source_id)
    }


def test_single_letter_yes_no_match_only_on_their_own():
    from app.services.migration.sources.nora_xlsx.xlsx_parser import _match_bool

    assert _match_bool("Y") is True
    assert _match_bool("n") is False
    assert _match_bool("No") is False
    # A word that only starts with "n" is not "no".
    assert _match_bool("Nasser") is None
    assert _match_bool("yes please") is True


# ---------------------------------------------------------------------------
# Adapter contract
# ---------------------------------------------------------------------------


def test_nora_source_is_registered():
    assert "nora_xlsx" in SOURCES
    src = SOURCES["nora_xlsx"]
    assert src.label == "NORA data-collection templates (DGA)"
    assert src.accepted_extensions == (".xlsx",)
    assert src.relation_mapping["serviceToApplication"] == "relGovServiceToApp"
    assert src.relation_mapping["applicationToInterface"] == "relAppToInterface"


def test_is_xlsx_payload():
    assert is_xlsx_payload(b"PK\x03\x04rest")
    assert not is_xlsx_payload(b"<?xml")


def test_stub_payload_never_blanks_description():
    """The post-build hook drops the empty description on stub entities so an
    update against an existing card can't wipe it."""
    from app.services.migration.snapshot import SourceEntity
    from app.services.migration.staging import build_card_payload

    src = SOURCES["nora_xlsx"]
    stub = SourceEntity(
        source_id="nora:Application:x",
        type="Application",
        name="X",
        raw={"nora_stub": True},
    )
    payload = build_card_payload(src, stub, "Application")
    assert "description" not in payload
    assert payload["attributes"]["source_origin"] == "nora_xlsx:referenced"

    real = SourceEntity(
        source_id="nora:Application:y", type="Application", name="Y", description="d"
    )
    payload = build_card_payload(src, real, "Application")
    assert payload["description"] == "d"


def test_free_text_keeps_its_line_breaks():
    from app.services.migration.sources.nora_xlsx.xlsx_parser import _norm_text

    assert _norm_text("1-  الرد خلال المدة\r\n\n2- سرية  البيانات ") == (
        "1- الرد خلال المدة\n2- سرية البيانات"
    )
    assert _norm_text("  سطر واحد  ") == "سطر واحد"


def test_policy_clauses_and_description_keep_one_item_per_line(tmp_path):
    wb = Workbook()
    _write_sheet(
        wb,
        "دليل السياسات",
        [
            ["دليل السياسات"],
            ["رمز السياسة", "اسم السياسة", "وصف السياسة", "بنود السياسة"],
            ["شرح"] * 4,
            ["P1", "سياسة الشكاوى", "سطر أول\nسطر ثان", "1- البند الأول\n2- البند الثاني"],
        ],
    )
    policy = _by_id(parse_xlsx_path(_save(wb, tmp_path)))["nora:Policy:سياسة الشكاوى"]
    assert policy.description == "سطر أول\nسطر ثان"
    assert policy.custom_fields["policyClauses"] == "1- البند الأول\n2- البند الثاني"
