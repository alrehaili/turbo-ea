"""Build filled sample copies of the DGA business and data collection templates.

Writes from row 4 (rows 1-3 are the title, headers and explanations) and clears
the template's own example row first, so every link in the sample resolves.
"""

import shutil
import sys
import warnings
from pathlib import Path

import openpyxl

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "NORA"
OUT = ROOT / "examp" / "dga-templates-sample"
OUT.mkdir(parents=True, exist_ok=True)

# ── Business architecture ──────────────────────────────────────────────────
SERVICES = [
    # code, name, description, general dept, dept, class, parent, type, automation, apps,
    # steps, coverage, requirements, channels, individuals, business, government,
    # maturity, inputs, outputs, fee, partners, kpis, monthly, sla, notes
    ["S01", "خدمة تقديم شكوى", "استلام شكاوى المستفيدين ودراستها والرد عليها",
     "الإدارة العامة لحماية حقوق المستفيدين", "إدارة شكاوى المستفيدين", "رئيسي", None,
     "داعمة", "مؤتمت جزئيا", "نظام إدارة الشكاوى",
     "1- استقبال الشكوى\n2- دراسة الشكوى\n3- الرد على المستفيد", "كافة مناطق المملكة",
     "•استكمال الوثائق الداعمة للشكوى", "•الموقع الإلكتروني للجهة\n•تطبيق الأجهزة الذكية",
     "نعم", "نعم", "لا", "تفاعلية", "•نموذج الشكوى\n•الوثائق الداعمة", "شكوى مغلقة", "لا",
     "إدارة علاقات العملاء", "مؤشر رضا المستفيدين", "7500", "10 أيام عمل", None],
    ["S02", "خدمة إصدار شهادة", "إصدار شهادة رسمية للمستفيد بعد التحقق من بياناته",
     "الإدارة العامة للخدمات", "إدارة الشهادات", "رئيسي", None, "محورية", "مؤتمت كليا",
     "بوابة الخدمات الإلكترونية", "1- تقديم الطلب\n2- التحقق\n3- إصدار الشهادة",
     "كافة مناطق المملكة", "•هوية وطنية سارية", "•بوابة الخدمات الإلكترونية",
     "نعم", "لا", "لا", "تكاملية", "•نموذج طلب شهادة", "شهادة إلكترونية", "نعم",
     None, "متوسط مدة إصدار الشهادة", "12000", "3 أيام عمل", None],
    ["S03", "خدمة طلب تصريح", "استقبال طلبات التصاريح ودراستها وإصدار القرار",
     "الإدارة العامة للخدمات", "إدارة التصاريح", "رئيسي", None, "محورية", "مؤتمت جزئيا",
     "بوابة الخدمات الإلكترونية", "1- تقديم الطلب\n2- المراجعة\n3- القرار",
     "مناطق محددة", "•سجل تجاري ساري", "•بوابة الخدمات الإلكترونية\n•مراكز الخدمة",
     "لا", "نعم", "نعم", "إجرائية", "•نموذج طلب تصريح", "قرار التصريح", "نعم",
     "وزارة التجارة", "نسبة الطلبات المنجزة في الوقت", "900", "15 يوم عمل", None],
]

PROCESSES = [
    # code, name, desc, class, general dept, dept, automation, systems,
    # individuals, business, government, steps, inputs, outputs, services, processes,
    # duration, trigger, rules, notes
    ["P01", "معالجة شكاوى المستفيدين", "التعامل مع الشكاوى ومعالجتها حسب نوعها", "رئيسي",
     "الإدارة العامة لحماية حقوق المستفيدين", "إدارة شكاوى المستفيدين", "مؤتمت جزئيا",
     "نظام إدارة الشكاوى", "نعم", "نعم", "لا", "•استقبال الشكوى\n•إحالتها للإدارة المختصة",
     "•وصف الشكوى", "الرد على الشكوى", "خدمة تقديم شكوى", "مراجعة مسببات الشكاوى",
     "14 يوم عمل", "استقبال شكوى", "•تصنيف الشكاوى حسب طبيعتها", None],
    ["P02", "مراجعة مسببات الشكاوى", "تحليل الشكاوى المتكررة واقتراح التحسينات", "فرعي",
     "الإدارة العامة لحماية حقوق المستفيدين", "إدارة جودة الخدمات", "غير مؤتمت", None,
     "لا", "لا", "لا", "•تجميع الشكاوى\n•تحليل الأسباب", "•تقارير الشكاوى",
     "توصيات التحسين", "خدمة تقديم شكوى", None, "30 يوم عمل", "نهاية كل ربع سنة",
     None, None],
    ["P03", "إصدار الشهادات", "التحقق من بيانات الطلب وإصدار الشهادة", "رئيسي",
     "الإدارة العامة للخدمات", "إدارة الشهادات", "مؤتمت كليا", "بوابة الخدمات الإلكترونية",
     "نعم", "لا", "لا", "•التحقق من البيانات\n•إصدار الشهادة", "•طلب الشهادة",
     "شهادة إلكترونية", "خدمة إصدار شهادة", None, "3 أيام عمل", "تقديم طلب شهادة",
     None, None],
    ["P04", "دراسة طلبات التصاريح", "مراجعة طلب التصريح واتخاذ القرار", "رئيسي",
     "الإدارة العامة للخدمات", "إدارة التصاريح", "مؤتمت جزئيا", "بوابة الخدمات الإلكترونية",
     "لا", "نعم", "نعم", "•المراجعة الفنية\n•القرار", "•طلب التصريح", "قرار التصريح",
     "خدمة طلب تصريح", None, "15 يوم عمل", "تقديم طلب تصريح", None, None],
]

MODELS = [
    # code, name, desc, type, services, processes, attachments
    ["1001", "نموذج الشكوى", "حصر بيانات الشاكي ووصف الشكوى", "نموذج طلب خدمة",
     "خدمة تقديم شكوى", "معالجة شكاوى المستفيدين", "•الوثائق الداعمة"],
    ["1002", "نموذج طلب شهادة", "بيانات طالب الشهادة ونوعها", "نموذج طلب خدمة",
     "خدمة إصدار شهادة", "إصدار الشهادات", None],
    ["1003", "نموذج حصر الشكاوى المتكررة", "تجميع بيانات الشكاوى لتحليل أسبابها",
     "نموذج حصر بيانات", None, "مراجعة مسببات الشكاوى", None],
    ["1004", "قالب سياسة", "القالب المعتمد لكتابة سياسات الجهة", "قالب سياسة", None, None,
     None],
]

POLICIES = [
    # code, name, desc, general dept, dept, type, scope, status, date, capability,
    # services, processes, clauses
    ["POL01", "سياسة التعامل مع الشكاوى", "مبادئ وضوابط الجهة في معالجة الشكاوى",
     "الإدارة العامة لحماية حقوق المستفيدين", "إدارة شؤون المستفيدين", "سياسة داخلية",
     "تنطبق على جميع موظفي الجهة", "مفعّلة", "15/01/2023", "علاقات العملاء",
     "خدمة تقديم شكوى", "•معالجة شكاوى المستفيدين\n•مراجعة مسببات الشكاوى",
     "1- الرد خلال المدة المحددة\n2- سرية بيانات الشاكي"],
    ["POL02", "سياسة حماية البيانات الشخصية", "حماية البيانات الشخصية للمستفيدين",
     "الإدارة العامة للبيانات", "إدارة حوكمة البيانات", "سياسة خارجية/ حكومية",
     "تنطبق على جميع الخدمات التي تجمع بيانات شخصية", "مفعّلة", "01/09/2023",
     "إدارة البيانات", "•خدمة إصدار شهادة\n•خدمة طلب تصريح", "إصدار الشهادات",
     "1- جمع الحد الأدنى من البيانات\n2- عدم المشاركة دون موافقة"],
    ["POL03", "سياسة رسوم الخدمات", "تحديد رسوم الخدمات وآلية تحصيلها",
     "الإدارة العامة للمالية", "إدارة الإيرادات", "سياسة داخلية",
     "تنطبق على الخدمات ذات الرسوم", "موقوفة", "01/03/2022", "الإدارة المالية",
     "•خدمة إصدار شهادة\n•خدمة طلب تصريح", None, None],
]

# ── Data architecture ──────────────────────────────────────────────────────
ENTITIES = [
    # id, en, ar, desc ar, desc en, data type, classification
    ["ENT_1", "Employee", "موظف", "بيانات موظفي الجهة", "The entity's employees",
     "Alphabetical", "مقيد"],
    ["ENT_2", "Beneficiary", "مستفيد", "بيانات المستفيدين من خدمات الجهة",
     "People who use the entity's services", "Alphabetical", "سري"],
    ["ENT_3", "Complaint", "شكوى", "الشكاوى المقدمة من المستفيدين",
     "Complaints raised by beneficiaries", "Alphanumeric", "مقيد"],
]
ENT = {e[0]: e for e in ENTITIES}

# Attributes: (entity, id, en, ar) + catalogue values + attribute-sheet values.
ATTRS = [
    ("ENT_1", "ATR1", "name", "الاسم",
     dict(desc_en="Employee name", desc_ar="اسم الموظف", sector="قطاع الموارد البشرية",
          dept="إدارة شؤون الموظفين", nullable="N", sample="أحمد", listed="N",
          lookup="N/A", rules="إلزامي، 50 حرفا كحد أقصى", owner="مدير الموارد البشرية",
          steward="محلل بيانات الموارد البشرية", cls="مقيد"),
     dict(scope="الموارد البشرية", source="نظام الموارد البشرية", pk="N", nullable="N",
          type="Alphabetical", length=50, fmt="Arabic Characters",
          owner="مدير الموارد البشرية", steward="محلل بيانات الموارد البشرية",
          table="EMPLOYEE", schema="HR")),
    ("ENT_1", "ATR2", "employee_id", "الرقم الوظيفي",
     dict(desc_en="Employee number", desc_ar="الرقم الوظيفي للموظف", nullable="N",
          sample="100245", listed="N", lookup="N/A", rules="فريد لكل موظف", cls="مقيد"),
     dict(scope="الموارد البشرية", source="نظام الموارد البشرية", pk="Y", nullable="N",
          type="Numeric", length=10, fmt="Digits", table="EMPLOYEE", schema="HR")),
    ("ENT_2", "ATR3", "national_id", "رقم الهوية",
     dict(desc_en="National ID number", desc_ar="رقم الهوية الوطنية للمستفيد",
          nullable="N", sample="1xxxxxxxxx", listed="N", lookup="N/A",
          rules="10 أرقام تبدأ بـ 1 أو 2", owner="مدير حوكمة البيانات",
          steward="مختص بيانات المستفيدين", cls="سري"),
     dict(scope="خدمات المستفيدين", source="بوابة الخدمات الإلكترونية", pk="Y", nullable="N",
          type="Numeric", length=10, fmt="Digits", table="BENEFICIARY", schema="CRM")),
    ("ENT_2", "ATR4", "email", "البريد الإلكتروني",
     dict(desc_en="Contact e-mail", desc_ar="البريد الإلكتروني للتواصل", nullable="Y",
          sample="name@example.com", listed="N", lookup="N/A", cls="سري"),
     dict(scope="خدمات المستفيدين", source="بوابة الخدمات الإلكترونية", pk="N", nullable="Y",
          type="Alphanumeric", length=100, fmt="E-mail", table="BENEFICIARY", schema="CRM")),
    ("ENT_3", "ATR5", "complaint_no", "رقم الشكوى",
     dict(desc_en="Complaint number", desc_ar="الرقم المرجعي للشكوى", nullable="N",
          sample="C-2024-0001", listed="N", lookup="N/A", rules="يولد آليا", cls="مقيد"),
     dict(scope="الشكاوى", source="نظام إدارة الشكاوى", pk="Y", nullable="N",
          type="Alphanumeric", length=12, fmt="C-YYYY-NNNN", table="COMPLAINT",
          schema="CMS")),
    ("ENT_3", "ATR6", "status", "حالة الشكوى",
     dict(desc_en="Complaint status", desc_ar="الحالة الحالية للشكوى", nullable="N",
          sample="مغلقة", listed="Y", lookup="قائمة حالات الشكوى", cls="مقيد"),
     dict(scope="الشكاوى", source="نظام إدارة الشكاوى", pk="N", nullable="N",
          type="Alphabetical", length=20, fmt="Arabic Characters", table="COMPLAINT",
          schema="CMS")),
    # Only in the business catalogue: the attributes sheet adds nothing for it.
    ("ENT_3", "ATR7", "submitted_on", "تاريخ تقديم الشكوى",
     dict(desc_en="Submission date", desc_ar="تاريخ تقديم الشكوى", nullable="N",
          sample="2024-05-01", listed="N", lookup="N/A", cls="عام"),
     None),
]


def fill(ws, rows):
    """Clear the template's example rows, then write ours from row 4."""
    for r in range(4, ws.max_row + 1):
        for c in range(1, ws.max_column + 1):
            cell = ws.cell(r, c)
            if not isinstance(cell, openpyxl.cell.cell.MergedCell):
                cell.value = None
    for i, row in enumerate(rows):
        for j, value in enumerate(row):
            ws.cell(4 + i, 1 + j).value = value


def sheet(wb, title):
    return next(ws for ws in wb.worksheets if ws.title.strip() == title)


def catalogue_row(a):
    ent, aid, en, ar, cat, _ = a
    e = ENT[ent]
    return [e[0], e[1], e[2], aid, en, ar, cat.get("desc_en"), cat.get("desc_ar"),
            cat.get("sector"), None, cat.get("dept"), cat.get("nullable"), cat.get("sample"),
            cat.get("listed"), cat.get("lookup"), cat.get("rules"), cat.get("owner"), None,
            cat.get("steward"), None, None, None, None, None, cat.get("cls"), None]


def attribute_row(a):
    ent, aid, en, ar, _, at = a
    e = ENT[ent]
    return [e[0], e[1], e[2], aid, en, ar, at.get("scope"), at.get("source"), at.get("pk"),
            at.get("nullable"), at.get("type"), at.get("length"), at.get("fmt"),
            at.get("owner"), at.get("steward"), at.get("table"), at.get("schema")]


def build(src_glob, out_name, fills):
    src = next(SRC.glob(src_glob))
    dst = OUT / out_name
    shutil.copyfile(src, dst)
    wb = openpyxl.load_workbook(dst)
    for title, rows in fills:
        fill(sheet(wb, title), rows)
    wb.save(dst)
    print("wrote", dst)


build("*بنية الأعمال*.xlsx", "DGA-sample-business.xlsx", [
    ("دليل الخدمات", SERVICES),
    ("دليل الإجراءات", PROCESSES),
    ("دليل النماذج", MODELS),
    ("دليل السياسات", POLICIES),
])
build("*بنية البيانات*.xlsx", "DGA-sample-data.xlsx", [
    ("دليل قاموس البيانات", ENTITIES),
    ("دليل فهرس الأعمال", [catalogue_row(a) for a in ATTRS]),
    ("دليل سمات البيانات", [attribute_row(a) for a in ATTRS if a[5]]),
])
sys.exit(0)
