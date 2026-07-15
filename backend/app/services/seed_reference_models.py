"""Reference Models seed data — 6 domains × 10 items each (60 total).

[FORK FEATURE] — Complete Reference Model catalogue:
✓ BRM (Business Reference Model) — 10 items
✓ ARM (Applications Reference Model) — 10 items
✓ DRM (Data Reference Model) — 10 items
✓ TRM (Technology Reference Model) — 10 items
✓ BXRM (Beneficiary Experience RM) — 10 items
✓ SRM (Security Reference Model) — 10 items

All hierarchical, with proper parent-child relationships.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reference_model import ReferenceModel, ReferenceModelItem

# ════════════════════════════════════════════════════════════════════════════
# BRM — Business Reference Model (10 items, 3 levels)
# ════════════════════════════════════════════════════════════════════════════

BRM_HIERARCHY = {
    "BRM-1.0": {"name": "Strategic Leadership", "parent": None},
    "BRM-1.1": {"name": "Strategy & Planning", "parent": "BRM-1.0"},
    "BRM-1.2": {"name": "Organizational Development", "parent": "BRM-1.0"},
    "BRM-2.0": {"name": "Performance Management", "parent": None},
    "BRM-2.1": {"name": "Financial Management", "parent": "BRM-2.0"},
    "BRM-2.2": {"name": "Budget Analysis & Control", "parent": "BRM-2.1"},
    "BRM-3.0": {"name": "Service Delivery", "parent": None},
    "BRM-3.1": {"name": "Customer Service & Support", "parent": "BRM-3.0"},
    "BRM-3.2": {"name": "Program & Project Management", "parent": "BRM-3.0"},
    "BRM-4.0": {"name": "Enterprise Operations", "parent": None},
}

# ════════════════════════════════════════════════════════════════════════════
# ARM — Applications Reference Model (10 items)
# ════════════════════════════════════════════════════════════════════════════

ARM_HIERARCHY = {
    "ARM-A.0": {"name": "Enterprise Resource Planning", "parent": None},
    "ARM-A.1": {"name": "Financial Management Systems", "parent": "ARM-A.0"},
    "ARM-A.2": {"name": "Human Resources Management", "parent": "ARM-A.0"},
    "ARM-B.0": {"name": "Customer Relations Management", "parent": None},
    "ARM-B.1": {"name": "Customer Relationship Management", "parent": "ARM-B.0"},
    "ARM-B.2": {"name": "Service Interaction Management", "parent": "ARM-B.0"},
    "ARM-C.0": {"name": "Content & Knowledge Management", "parent": None},
    "ARM-D.0": {"name": "Enterprise Integration", "parent": None},
    "ARM-E.0": {"name": "Business Intelligence & Analytics", "parent": None},
    "ARM-F.0": {"name": "Collaboration & Communication", "parent": None},
}

# ════════════════════════════════════════════════════════════════════════════
# DRM — Data Reference Model (10 items)
# ════════════════════════════════════════════════════════════════════════════

DRM_HIERARCHY = {
    "DRM-C.0": {"name": "Business Information", "parent": None},
    "DRM-C.1": {"name": "Organization & Structure Data", "parent": "DRM-C.0"},
    "DRM-C.2": {"name": "Product & Service Data", "parent": "DRM-C.0"},
    "DRM-E.0": {"name": "Entity Reference Data", "parent": None},
    "DRM-E.1": {"name": "Master Data (MDM)", "parent": "DRM-E.0"},
    "DRM-G.0": {"name": "Geospatial & Location Data", "parent": None},
    "DRM-I.0": {"name": "Imagery & Spatial Data", "parent": None},
    "DRM-S.0": {"name": "Sensor & IoT Data", "parent": None},
    "DRM-T.0": {"name": "Trade & Commerce Data", "parent": None},
    "DRM-X.0": {"name": "XML & Metadata", "parent": None},
}

# ════════════════════════════════════════════════════════════════════════════
# TRM — Technology Reference Model (10 items)
# ════════════════════════════════════════════════════════════════════════════

TRM_HIERARCHY = {
    "TRM-1.0": {"name": "Infrastructure & Computing", "parent": None},
    "TRM-1.1": {"name": "Computing Resources (Servers, VMs)", "parent": "TRM-1.0"},
    "TRM-1.2": {"name": "Storage Resources (SAN, NAS)", "parent": "TRM-1.0"},
    "TRM-2.0": {"name": "Integration & Messaging", "parent": None},
    "TRM-3.0": {"name": "Security & Cryptography", "parent": None},
    "TRM-3.1": {"name": "Encryption & PKI", "parent": "TRM-3.0"},
    "TRM-4.0": {"name": "Networking & Connectivity", "parent": None},
    "TRM-5.0": {"name": "Database Management", "parent": None},
    "TRM-6.0": {"name": "Middleware & Application Servers", "parent": None},
    "TRM-7.0": {"name": "Systems & Operations Management", "parent": None},
}

# ════════════════════════════════════════════════════════════════════════════
# BXRM — Beneficiary Experience Reference Model (10 items)
# ════════════════════════════════════════════════════════════════════════════

BXRM_HIERARCHY = {
    "BXRM-1.0": {"name": "Service Accessibility", "parent": None},
    "BXRM-1.1": {"name": "Multi-Channel Availability", "parent": "BXRM-1.0"},
    "BXRM-1.2": {"name": "Digital Accessibility (WCAG)", "parent": "BXRM-1.0"},
    "BXRM-2.0": {"name": "User Experience & Usability", "parent": None},
    "BXRM-2.1": {"name": "Usability & Interface Design", "parent": "BXRM-2.0"},
    "BXRM-3.0": {"name": "Service Quality & Performance", "parent": None},
    "BXRM-3.1": {"name": "Response Time & Reliability", "parent": "BXRM-3.0"},
    "BXRM-4.0": {"name": "Feedback & Support", "parent": None},
    "BXRM-5.0": {"name": "Personalization & Preferences", "parent": None},
    "BXRM-6.0": {"name": "Privacy & Trust", "parent": None},
}

# ════════════════════════════════════════════════════════════════════════════
# SRM — Security Reference Model (10 items)
# ════════════════════════════════════════════════════════════════════════════

SRM_HIERARCHY = {
    "SRM-1.0": {"name": "Identification & Authentication", "parent": None},
    "SRM-1.1": {"name": "User Authentication Methods", "parent": "SRM-1.0"},
    "SRM-1.2": {"name": "Multi-Factor Authentication (MFA)", "parent": "SRM-1.0"},
    "SRM-2.0": {"name": "Authorization & Access Control", "parent": None},
    "SRM-2.1": {"name": "Role-Based Access Control (RBAC)", "parent": "SRM-2.0"},
    "SRM-3.0": {"name": "Data Protection & Encryption", "parent": None},
    "SRM-3.1": {"name": "Data Encryption (At-Rest & In-Transit)", "parent": "SRM-3.0"},
    "SRM-4.0": {"name": "Threat & Vulnerability Management", "parent": None},
    "SRM-5.0": {"name": "Security Monitoring & Detection", "parent": None},
    "SRM-6.0": {"name": "Incident Response & Recovery", "parent": None},
}

# ════════════════════════════════════════════════════════════════════════════
# SEED FUNCTION
# ════════════════════════════════════════════════════════════════════════════


async def seed_reference_models(db: AsyncSession) -> dict:
    """Seed 6 published Reference Models (one per NORA domain) with hierarchies.

    Idempotent **per key** — each model carries a stable ``key`` so re-running
    is a no-op and this coexists with the NORA profile's built-in "kit preview"
    starters (which use their own ``nea_*_preview`` keys). We publish these so
    they become the active RM per domain (publishing supersedes any prior
    published RM of the same domain; the draft kit previews are untouched).

    Creates up to 60 ReferenceModelItems across 6 domains.
    """
    # key, domain, name, description, hierarchy
    rm_data = [
        (
            "nora_kit_business",
            "business",
            "Business Reference Model (BRM)",
            "Business architecture framework",
            BRM_HIERARCHY,
        ),
        (
            "nora_kit_applications",
            "applications",
            "Applications Reference Model (ARM)",
            "Application categorization",
            ARM_HIERARCHY,
        ),
        (
            "nora_kit_data",
            "data",
            "Data Reference Model (DRM)",
            "Data classification framework",
            DRM_HIERARCHY,
        ),
        (
            "nora_kit_technology",
            "technology",
            "Technology Reference Model (TRM)",
            "Technology standards",
            TRM_HIERARCHY,
        ),
        (
            "nora_kit_beneficiary",
            "beneficiaryExperience",
            "Beneficiary Experience RM (BXRM)",
            "User experience standards",
            BXRM_HIERARCHY,
        ),
        (
            "nora_kit_security",
            "security",
            "Security Reference Model (SRM)",
            "Security standards",
            SRM_HIERARCHY,
        ),
    ]

    # Which of our keys already exist? Skip those (idempotent per key).
    keys = [k for (k, *_rest) in rm_data]
    existing_keys = {
        k
        for (k,) in (
            await db.execute(select(ReferenceModel.key).where(ReferenceModel.key.in_(keys)))
        ).all()
    }

    now = datetime.now(timezone.utc)
    total_items = 0
    models_created = 0
    domains_seeded: list[str] = []

    for key, domain, name, description, hierarchy in rm_data:
        if key in existing_keys:
            continue

        # Publishing supersedes: demote any currently-published RM of this domain.
        published = (
            (
                await db.execute(
                    select(ReferenceModel).where(
                        ReferenceModel.domain == domain,
                        ReferenceModel.status == "published",
                    )
                )
            )
            .scalars()
            .all()
        )
        for prev in published:
            prev.status = "archived"

        model = ReferenceModel(
            key=key,
            domain=domain,
            name=name,
            description=description,
            version="1.0",
            source="national",
            status="published",  # active RM for the domain
            built_in=True,
            published_at=now,
        )
        db.add(model)
        await db.flush()
        models_created += 1
        domains_seeded.append(domain)

        # Items with parent relationships (parents precede children in dict order).
        item_map: dict[str, ReferenceModelItem] = {}
        codes = list(hierarchy.keys())
        for code, spec in hierarchy.items():
            parent_id = None
            if spec["parent"]:
                parent_id = item_map[spec["parent"]].id
            item = ReferenceModelItem(
                model_id=model.id,
                parent_id=parent_id,
                code=code,
                name=spec["name"],
                sort_order=codes.index(code),
            )
            db.add(item)
            await db.flush()
            item_map[code] = item
            total_items += 1

    await db.commit()

    if models_created == 0:
        return {"skipped": True, "reason": "Reference Models already seeded (all keys present)"}

    return {
        "loaded": True,
        "reference_models": models_created,
        "reference_model_items": total_items,
        "domains": domains_seeded,
        "status": "published",
        "validation": "hierarchy_complete_with_parent_links",
    }
