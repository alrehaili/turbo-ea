"""NORA Content Meta Model — Security Architecture building blocks (split types).

[FORK] NORA exact-fidelity metamodel (noraPlanMeta.md, Phase 1G).

The National EA Framework "EA Content Meta Model" document (§5.3.7) defines the
Security Architecture domain as three independent building blocks: Security
Hardware, Security Software, and Security Service. ``SecurityService`` already
exists in ``seed.TYPES``; the stock fork collapsed hardware + software into a
single ``SecurityFunction`` type. This module restores the two as first-class
types (``SecurityFunction`` is left in place, to be hidden in Phase 3).

Appended onto ``seed.TYPES``; reuses the field helpers from
``seed_nora_technology``.
"""

from __future__ import annotations

from app.services.seed_nora_technology import (
    _MANUFACTURER,
    _MODEL,
    _NETWORK_SEGMENT,
    _SUPPORT_END,
    _field,
    _section,
    _tx,
)

NORA_SECURITY_TYPES: list[dict] = [
    # 43 · Security Hardware ----------------------------------------------
    {
        "key": "SecurityHardware",
        "label": "Security Hardware",
        "description": "Security solution hardware used by the entity to achieve information "
        "security (firewalls, IPS/IDS, etc.).",
        "icon": "security",
        "color": "#c62828",
        "category": "Security",
        "has_hierarchy": False,
        "translations": {
            "label": _tx(
                de="Sicherheitshardware",
                fr="Matériel de sécurité",
                es="Hardware de seguridad",
                it="Hardware di sicurezza",
                pt="Hardware de segurança",
                zh="安全硬件",
                ru="Оборудование безопасности",
                da="Sikkerhedshardware",
                ar="أجهزة الأمن",
            ),
            "description": _tx(
                de="Sicherheitslösungs-Hardware der Entität zur Gewährleistung der "
                "Informationssicherheit (Firewalls, IPS/IDS usw.).",
                fr="Matériel de solution de sécurité utilisé par l'entité pour assurer la "
                "sécurité de l'information (pare-feu, IPS/IDS, etc.).",
                es="Hardware de solución de seguridad usado por la entidad para lograr la "
                "seguridad de la información (cortafuegos, IPS/IDS, etc.).",
                it="Hardware di soluzioni di sicurezza usato dall'ente per garantire la "
                "sicurezza delle informazioni (firewall, IPS/IDS, ecc.).",
                pt="Hardware de solução de segurança usado pela entidade para alcançar a "
                "segurança da informação (firewalls, IPS/IDS, etc.).",
                zh="实体用于实现信息安全的安全解决方案硬件（防火墙、IPS/IDS 等）。",
                ru="Аппаратные средства безопасности, используемые организацией для обеспечения "
                "информационной безопасности (межсетевые экраны, IPS/IDS и т. д.).",
                da="Sikkerhedsløsningshardware brugt af enheden til at opnå "
                "informationssikkerhed (firewalls, IPS/IDS osv.).",
                ar="أجهزة الحلول الأمنية التي تستخدمها الجهة لتحقيق أمن المعلومات (جدران الحماية "
                "وأنظمة منع/كشف التسلل، إلخ).",
            ),
        },
        "subtypes": [],
        "sort_order": 44,
        "fields_schema": [
            _section(
                "Security Hardware Details",
                _tx(
                    de="Details der Sicherheitshardware",
                    fr="Détails du matériel de sécurité",
                    es="Detalles del hardware de seguridad",
                    it="Dettagli dell'hardware di sicurezza",
                    pt="Detalhes do hardware de segurança",
                    zh="安全硬件详情",
                    ru="Сведения об оборудовании безопасности",
                    da="Detaljer om sikkerhedshardware",
                    ar="تفاصيل أجهزة الأمن",
                ),
                [
                    _MANUFACTURER(1),
                    _MODEL(2),
                    _NETWORK_SEGMENT(3),
                    _field(
                        "function",
                        "Function",
                        "text",
                        4,
                        _tx(
                            de="Funktion",
                            fr="Fonction",
                            es="Función",
                            it="Funzione",
                            pt="Função",
                            zh="功能",
                            ru="Функция",
                            da="Funktion",
                            ar="الوظيفة",
                        ),
                    ),
                    _SUPPORT_END(5),
                ],
            ),
        ],
    },
    # 44 · Security Software ----------------------------------------------
    {
        "key": "SecuritySoftware",
        "label": "Security Software",
        "description": "Software or tools used by the entity to achieve information security.",
        "icon": "shield",
        "color": "#c62828",
        "category": "Security",
        "has_hierarchy": False,
        "translations": {
            "label": _tx(
                de="Sicherheitssoftware",
                fr="Logiciel de sécurité",
                es="Software de seguridad",
                it="Software di sicurezza",
                pt="Software de segurança",
                zh="安全软件",
                ru="Программное обеспечение безопасности",
                da="Sikkerhedssoftware",
                ar="برمجيات الأمن",
            ),
            "description": _tx(
                de="Software oder Werkzeuge der Entität zur Gewährleistung der "
                "Informationssicherheit.",
                fr="Logiciels ou outils utilisés par l'entité pour assurer la sécurité de "
                "l'information.",
                es="Software o herramientas usados por la entidad para lograr la seguridad de "
                "la información.",
                it="Software o strumenti usati dall'ente per garantire la sicurezza delle "
                "informazioni.",
                pt="Software ou ferramentas usados pela entidade para alcançar a segurança da "
                "informação.",
                zh="实体用于实现信息安全的软件或工具。",
                ru="Программное обеспечение или инструменты, используемые организацией для "
                "обеспечения информационной безопасности.",
                da="Software eller værktøjer brugt af enheden til at opnå informationssikkerhed.",
                ar="البرمجيات أو الأدوات التي تستخدمها الجهة لتحقيق أمن المعلومات.",
            ),
        },
        "subtypes": [],
        "sort_order": 45,
        "fields_schema": [
            _section(
                "Security Software Details",
                _tx(
                    de="Details der Sicherheitssoftware",
                    fr="Détails du logiciel de sécurité",
                    es="Detalles del software de seguridad",
                    it="Dettagli del software di sicurezza",
                    pt="Detalhes do software de segurança",
                    zh="安全软件详情",
                    ru="Сведения о ПО безопасности",
                    da="Detaljer om sikkerhedssoftware",
                    ar="تفاصيل برمجيات الأمن",
                ),
                [
                    _MANUFACTURER(1),
                    _field(
                        "function",
                        "Function",
                        "text",
                        2,
                        _tx(
                            de="Funktion",
                            fr="Fonction",
                            es="Función",
                            it="Funzione",
                            pt="Função",
                            zh="功能",
                            ru="Функция",
                            da="Funktion",
                            ar="الوظيفة",
                        ),
                    ),
                    _SUPPORT_END(3),
                ],
            ),
        ],
    },
]
