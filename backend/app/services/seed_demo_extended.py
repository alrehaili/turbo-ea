"""Extended demo seed data: users, calculations, recurring workflows, scenarios, roadmaps, rationalization."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.arb_review import ArbReview
from app.models.bookmark import Bookmark
from app.models.calculation import Calculation
from app.models.card import Card
from app.models.document import Document
from app.models.notification import Notification
from app.models.rationalization import AssessmentDecision, RationalizationAssessment
from app.models.risk import Risk
from app.models.risk_mitigation_task import (
    RiskMitigationTask,
    RiskMitigationTaskOccurrence,
)
from app.models.roadmap import Roadmap
from app.models.scenario import Scenario, ScenarioChange
from app.models.stakeholder import Stakeholder
from app.models.tech_standard import StandardException, TechStandard
from app.models.todo import Todo
from app.models.user import User
from app.models.user_favorite import UserFavorite

# ===================================================================
# PHASE 1: SAMPLE USERS & PERMISSIONS
# ===================================================================


async def seed_sample_users(db: AsyncSession) -> dict:
    """Create 5 sample users with different roles."""
    # Check if alice already exists (idempotent)
    existing = await db.execute(
        select(User).where(User.email == "abdulrahim@nexatech.demo").limit(1)
    )
    if existing.scalar_one_or_none():
        return {"skipped": "sample_users"}

    users_data = [
        {
            "email": "abdulrahim@nexatech.demo",
            "display_name": "Abdulrahim Alrehaili",
            "role": "admin",
            "description": "System Administrator",
        },
        {
            "email": "saleh@nexatech.demo",
            "display_name": "Saleh",
            "role": "member",
            "description": "Member - Enterprise Architect",
        },
        {
            "email": "talal@nexatech.demo",
            "display_name": "Talal",
            "role": "bpm_admin",
            "description": "BPM Administrator",
        },
        {
            "email": "abdulmajed@nexatech.demo",
            "display_name": "Abdul Majed",
            "role": "member",
            "description": "Member - Technology Lead",
        },
        {
            "email": "majid@nexatech.demo",
            "display_name": "Majid",
            "role": "viewer",
            "description": "Viewer - Board Observer",
        },
    ]

    created_users = {}
    for user_data in users_data:
        user = User(
            email=user_data["email"],
            display_name=user_data["display_name"],
            password_hash=hash_password("123456"),
            role=user_data["role"],
            is_active=True,
            auth_provider="local",
        )
        db.add(user)
        created_users[user_data["email"]] = user

    await db.commit()

    # Get user IDs for stakeholder assignments
    users_from_db = await db.execute(
        select(User).where(User.email.in_([u["email"] for u in users_data]))
    )
    users_dict = {u.email: u for u in users_from_db.scalars().all()}

    # Assign key stakeholders (use user IDs)
    stakeholder_assignments = []
    if "abdulrahim@nexatech.demo" in users_dict and "saleh@nexatech.demo" in users_dict:
        # Get some demo cards to assign stakeholders to
        from app.services.seed_demo import _refs

        card_refs = [
            "app_sap_s4",
            "app_sap_ariba",
            "cap_digital_prod_mgmt",
            "init_sap_migration",
            "bp_quote_to_cash",
        ]

        for ref in card_refs:
            if ref in _refs:
                card_id = _refs[ref]
                # Check if card exists
                card = await db.execute(select(Card).where(Card.id == card_id).limit(1))
                if card.scalar_one_or_none():
                    # Assign stakeholders
                    if "abdulrahim@nexatech.demo" in users_dict:
                        stakeholder = Stakeholder(
                            card_id=card_id,
                            user_id=users_dict["abdulrahim@nexatech.demo"].id,
                            role="responsible",
                        )
                        db.add(stakeholder)
                        stakeholder_assignments.append(stakeholder)

                    if "saleh@nexatech.demo" in users_dict:
                        stakeholder = Stakeholder(
                            card_id=card_id,
                            user_id=users_dict["saleh@nexatech.demo"].id,
                            role="observer",
                        )
                        db.add(stakeholder)
                        stakeholder_assignments.append(stakeholder)

    await db.commit()

    return {
        "users": len(users_data),
        "stakeholder_assignments": len(stakeholder_assignments),
    }


# ===================================================================
# PHASE 1: CALCULATED FIELDS
# ===================================================================


async def seed_calculations(db: AsyncSession) -> dict:
    """Create sample calculated field formulas."""
    # Check idempotence
    existing = await db.execute(
        select(Calculation).where(Calculation.target_field_key == "totalCostCalculated").limit(1)
    )
    if existing.scalar_one_or_none():
        return {"skipped": "calculations"}

    calculations_data = [
        {
            "name": "Application Total Annual Cost",
            "formula": "IF(attributes.costTotalAnnual, attributes.costTotalAnnual, 0)",
            "target_type_key": "Application",
            "target_field_key": "totalCostCalculated",
            "is_active": True,
            "execution_order": 1,
        },
        {
            "name": "Capability Coverage",
            "formula": 'COUNT(FILTER(related_applications, "status", "ACTIVE"))',
            "target_type_key": "BusinessCapability",
            "target_field_key": "appCoverageCalculated",
            "is_active": True,
            "execution_order": 2,
        },
        {
            "name": "Risk Exposure Score",
            "formula": 'SUM(PLUCK(related_risks, "initial_level"))',
            "target_type_key": "Application",
            "target_field_key": "riskExposureCalculated",
            "is_active": True,
            "execution_order": 3,
        },
    ]

    calculations = []
    for calc_data in calculations_data:
        calc = Calculation(
            name=calc_data["name"],
            formula=calc_data["formula"],
            target_type_key=calc_data["target_type_key"],
            target_field_key=calc_data["target_field_key"],
            is_active=calc_data["is_active"],
            execution_order=calc_data["execution_order"],
        )
        db.add(calc)
        calculations.append(calc)

    await db.commit()

    return {"calculations": len(calculations)}


# ===================================================================
# PHASE 1: USER FAVORITES & BOOKMARKS
# ===================================================================


async def seed_user_favorites(db: AsyncSession) -> dict:
    """Create user favorites for key cards."""
    user_result = await db.execute(select(User).where(User.email == "saleh@nexatech.demo").limit(1))
    user = user_result.scalar_one_or_none()
    if not user:
        return {"skipped": "user_favorites"}

    # Check idempotence
    existing = await db.execute(
        select(UserFavorite).where(UserFavorite.user_id == user.id).limit(1)
    )
    if existing.scalar_one_or_none():
        return {"skipped": "user_favorites"}

    from app.services.seed_demo import _refs

    favorite_refs = [
        "app_sap_s4",
        "app_nexacore_erp",
        "cap_digital_prod_mgmt",
        "init_sap_migration",
        "org_nexatech",
    ]

    favorites = []
    for ref in favorite_refs:
        if ref in _refs:
            card_id = _refs[ref]
            # Verify card exists
            card = await db.execute(select(Card).where(Card.id == card_id).limit(1))
            if card.scalar_one_or_none():
                fav = UserFavorite(user_id=user.id, card_id=card_id)
                db.add(fav)
                favorites.append(fav)

    await db.commit()

    return {"user_favorites": len(favorites)}


async def seed_user_bookmarks(db: AsyncSession) -> dict:
    """Create saved inventory views (bookmarks) for users."""
    user_result = await db.execute(select(User).where(User.email == "saleh@nexatech.demo").limit(1))
    user = user_result.scalar_one_or_none()
    if not user:
        return {"skipped": "user_bookmarks"}

    # Check idempotence
    existing = await db.execute(select(Bookmark).where(Bookmark.user_id == user.id).limit(1))
    if existing.scalar_one_or_none():
        return {"skipped": "user_bookmarks"}

    bookmarks_data = [
        {
            "title": "Critical Applications",
            "filters": {
                "status": "ACTIVE",
                "businessCriticality": ["missionCritical", "businessCritical"],
            },
            "sort_by": "costTotalAnnual",
            "sort_dir": "desc",
        },
        {
            "title": "My Stakeholder Cards",
            "filters": {"stakeholder_role": "responsible"},
            "sort_by": "name",
            "sort_dir": "asc",
        },
        {
            "title": "Microservices Inventory",
            "filters": {"type": "Application", "subtype": "microservice"},
            "sort_by": "name",
            "sort_dir": "asc",
        },
        {
            "title": "Active Initiatives",
            "filters": {"type": "Initiative", "status": "ACTIVE"},
            "sort_by": "name",
            "sort_dir": "asc",
        },
        {
            "title": "Cloud-Native Applications",
            "filters": {"type": "Application", "hostingType": "cloudSaaS"},
            "sort_by": "costTotalAnnual",
            "sort_dir": "desc",
        },
    ]

    bookmarks = []
    for bm_data in bookmarks_data:
        bookmark = Bookmark(
            user_id=user.id,
            name=bm_data["title"],
            card_type=bm_data["filters"].get("type"),
            filters=bm_data["filters"],
            sort={"field": bm_data["sort_by"], "direction": bm_data["sort_dir"]},
        )
        db.add(bookmark)
        bookmarks.append(bookmark)

    await db.commit()

    return {"bookmarks": len(bookmarks)}


# ===================================================================
# PHASE 1: NOTIFICATIONS
# ===================================================================


async def seed_notifications(db: AsyncSession) -> dict:
    """Create sample in-app notifications."""
    user_result = await db.execute(select(User).where(User.email == "saleh@nexatech.demo").limit(1))
    user = user_result.scalar_one_or_none()
    if not user:
        return {"skipped": "notifications"}

    # Check idempotence
    existing = await db.execute(
        select(Notification).where(Notification.user_id == user.id).limit(1)
    )
    if existing.scalar_one_or_none():
        return {"skipped": "notifications"}

    notifications_data = [
        {
            "type": "card_created",
            "title": "New card created",
            "message": "NexaCore ERP has been created by Abdulrahim",
            "read": False,
        },
        {
            "type": "comment_added",
            "title": "Comment on SAP Migration",
            "message": "Talal commented: 'Deployment timeline approved'",
            "read": False,
        },
        {
            "type": "task_assigned",
            "title": "Task assigned to you",
            "message": "Review Business Process assessment scores",
            "read": True,
        },
    ]

    notifications = []
    for notif_data in notifications_data:
        notif = Notification(
            user_id=user.id,
            type=notif_data["type"],
            title=notif_data["title"],
            message=notif_data["message"],
            is_read=notif_data["read"],
        )
        db.add(notif)
        notifications.append(notif)

    await db.commit()

    return {"notifications": len(notifications)}


# ===================================================================
# PHASE 1: DOCUMENTS & FILE ATTACHMENTS
# ===================================================================


async def seed_documents_and_attachments(db: AsyncSession) -> dict:
    """Add document links and attachment examples to demo cards."""
    from app.services.seed_demo import _refs

    # Check idempotence
    existing = await db.execute(select(Document).limit(1))
    if existing.scalar_one_or_none():
        return {"skipped": "documents_and_attachments"}

    documents_map = {
        "org_nexatech": [
            {"title": "2026 EA Strategy", "url": "https://nexatech.corp/docs/ea-strategy-2026.pdf"},
            {
                "title": "Annual Architectural Review",
                "url": "https://nexatech.corp/docs/arc-review-2025.pdf",
            },
        ],
        "init_sap_migration": [
            {"title": "Project Charter", "url": "https://nexatech.corp/projects/sap/charter.pdf"},
            {"title": "Risk Assessment", "url": "https://nexatech.corp/projects/sap/risks.xlsx"},
            {
                "title": "Vendor Evaluation Summary",
                "url": "https://nexatech.corp/projects/sap/vendor-eval.pptx",
            },
        ],
        "app_nexacore_erp": [
            {"title": "System Architecture", "url": "https://nexatech.corp/docs/nexacore-arch.pdf"},
            {
                "title": "API Documentation",
                "url": "https://nexatech.corp/docs/nexacore-api-docs.md",
            },
        ],
        "do_customer_master": [
            {
                "title": "Data Dictionary",
                "url": "https://nexatech.corp/docs/customer-data-dict.xlsx",
            },
            {"title": "Schema Diagram", "url": "https://nexatech.corp/docs/customer-schema.png"},
        ],
    }

    documents = []
    for ref, docs_list in documents_map.items():
        if ref in _refs:
            card_id = _refs[ref]
            # Verify card exists
            card = await db.execute(select(Card).where(Card.id == card_id).limit(1))
            if card.scalar_one_or_none():
                for doc in docs_list:
                    document = Document(
                        card_id=card_id,
                        name=doc["title"],
                        url=doc["url"],
                        type="link",
                    )
                    db.add(document)
                    documents.append(document)

    await db.commit()

    return {"documents": len(documents)}


# ===================================================================
# PHASE 2: RECURRING TODOS WITH LEAD-TIME GATING
# ===================================================================


async def seed_recurring_todos(db: AsyncSession) -> dict:
    """Create recurring system todos with lead-time gating."""
    user_result = await db.execute(select(User).where(User.email == "saleh@nexatech.demo").limit(1))
    user = user_result.scalar_one_or_none()
    if not user:
        return {"skipped": "recurring_todos"}

    # Check idempotence
    existing = await db.execute(
        select(Todo)
        .where(
            (Todo.description == "Review Application Portfolio Data Quality")
            & (Todo.assigned_to == user.id)
        )
        .limit(1)
    )
    if existing.scalar_one_or_none():
        return {"skipped": "recurring_todos"}

    # Resolve link targets by card *name*, not the in-memory ``_refs`` dict:
    # on idempotent re-runs (seed_demo skipped) ``_refs`` holds fresh random
    # UUIDs that don't match the existing cards, which would violate the
    # todos.card_id FK. A missing card simply yields an unlinked todo.
    name_to_id = {
        name: cid
        for name, cid in (
            await db.execute(
                select(Card.name, Card.id).where(Card.name.in_(["SAP S/4HANA", "Quote to Cash"]))
            )
        ).all()
    }

    now = datetime.now(timezone.utc)

    todos_data = [
        {
            "title": "Review Application Portfolio Data Quality",
            "description": "Quarterly review of application inventory data completeness and quality",
            "user_id": user.id,
            "due_date": now + timedelta(days=14),
            "recurrence_unit": "months",
            "recurrence_interval": 1,
            "is_system": False,
            "card_id": name_to_id.get("SAP S/4HANA"),
        },
        {
            "title": "Audit Process Assessment Scores",
            "description": "Validate current BPM maturity assessments",
            "user_id": user.id,
            "due_date": now + timedelta(days=7),
            "recurrence_unit": "weeks",
            "recurrence_interval": 2,
            "is_system": False,
            "card_id": name_to_id.get("Quote to Cash"),
        },
        {
            "title": "Update Risk Register & Mitigation Status",
            "description": "Refresh landscape risk register and check mitigation progress",
            "user_id": user.id,
            "due_date": now + timedelta(days=3),
            "recurrence_unit": "weeks",
            "recurrence_interval": 1,
            "is_system": False,
            "card_id": None,
        },
    ]

    todos = []
    for todo_data in todos_data:
        due = todo_data["due_date"]
        todo = Todo(
            description=todo_data["title"],
            assigned_to=todo_data["user_id"],
            created_by=todo_data["user_id"],
            due_date=due.date() if hasattr(due, "date") else due,
            recurrence_unit=todo_data.get("recurrence_unit"),
            recurrence_interval=todo_data.get("recurrence_interval"),
            is_system=todo_data.get("is_system", False),
            status="open",
        )
        if todo_data.get("card_id"):
            todo.card_id = todo_data["card_id"]
        db.add(todo)
        todos.append(todo)

    await db.commit()

    return {"recurring_todos": len(todos)}


# ===================================================================
# PHASE 2: RISK MITIGATION TASK OCCURRENCES
# ===================================================================


async def seed_risk_mitigation_occurrences(db: AsyncSession) -> dict:
    """Create risk mitigation tasks with full occurrence lifecycle."""
    user_result = await db.execute(select(User).where(User.email == "saleh@nexatech.demo").limit(1))
    user = user_result.scalar_one_or_none()
    if not user:
        return {"skipped": "risk_mitigation_occurrences"}

    # Get an existing risk from seed_demo_security
    risks = await db.execute(select(Risk).limit(1))
    risk = risks.scalar_one_or_none()
    if not risk:
        return {"skipped": "risk_mitigation_occurrences"}

    # Check idempotence
    existing = await db.execute(
        select(RiskMitigationTask).where(RiskMitigationTask.risk_id == risk.id).limit(1)
    )
    if existing.scalar_one_or_none():
        return {"skipped": "risk_mitigation_occurrences"}

    from app.services.risk_mitigation_task_service import next_task_reference

    now = datetime.now(timezone.utc)

    # Create a mitigation task
    task = RiskMitigationTask(
        reference=await next_task_reference(db),
        risk_id=risk.id,
        title="Conduct Security Assessment",
        description="Comprehensive security and compliance audit",
        owner_id=user.id,
        is_active=True,
        lead_time_days=7,
        recurrence_unit="months",
        recurrence_interval=3,
    )
    db.add(task)
    await db.flush()

    # Create occurrence history
    now_minus_6m = now - timedelta(days=180)
    now_minus_3m = now - timedelta(days=90)
    now_plus_3m = now + timedelta(days=90)

    occurrences_data = [
        {
            "sequence": 1,
            "due_date": now_minus_6m,
            "assigned_owner_id": user.id,
            "status": "done",
            "activated_at": now_minus_6m - timedelta(days=7),
            "completed_at": now_minus_6m + timedelta(days=2),
            "completed_by": user.id,
            "owner_at_completion": user.id,
            "completion_notes": "Completed - no critical findings",
        },
        {
            "sequence": 2,
            "due_date": now_minus_3m,
            "assigned_owner_id": user.id,
            "status": "done",
            "activated_at": now_minus_3m - timedelta(days=7),
            "completed_at": now_minus_3m + timedelta(days=5),
            "completed_by": user.id,
            "owner_at_completion": user.id,
            "completion_notes": "Completed - 2 medium-priority issues identified and remediated",
        },
        {
            "sequence": 3,
            "due_date": now_plus_3m,
            "assigned_owner_id": user.id,
            "status": "scheduled",
            "activated_at": None,
            "completed_at": None,
            "completed_by": None,
            "owner_at_completion": None,
            "completion_notes": None,
        },
    ]

    occurrences = []
    for occ_data in occurrences_data:
        occ_data = dict(occ_data)
        due = occ_data.get("due_date")
        if hasattr(due, "date"):
            occ_data["due_date"] = due.date()
        occ = RiskMitigationTaskOccurrence(
            task_id=task.id,
            **occ_data,
        )
        db.add(occ)
        occurrences.append(occ)

    await db.commit()

    return {
        "risk_mitigation_tasks": 1,
        "risk_mitigation_occurrences": len(occurrences),
    }


# ===================================================================
# PHASE 2: APPLICATION RATIONALIZATION (TIME MODEL)
# ===================================================================

# One curated portfolio decision per application, keyed by the real demo
# card *name* (not the in-memory ``_refs`` dict, which is only populated
# while ``seed_demo`` is actively running — empty on idempotent re-runs).
# This single list drives both the board assessment (``time`` decision +
# costs) and the per-card rationalization attributes (``status`` etc.), so
# the two stay consistent. ``successor`` is the name of the target card a
# ``migrate`` decision consolidates into (resolved to a card FK below).
RATIONALIZATION_DECISIONS: list[dict[str, Any]] = [
    # INVEST — strategic, fund the roadmap
    {
        "app": "SAP S/4HANA",
        "time": "invest",
        "status": "retain",
        "annual_cost": 2_400_000,
        "planned_savings": 0,
        "progress": 30,
        "effort": "low",
        "priority": 5,
        "target_year": 2028,
        "rationale": "Core ERP, strategic fit, active vendor investment.",
        "notes": "Continue current roadmap; monitor AI-driven enhancements.",
    },
    {
        "app": "Siemens Teamcenter",
        "time": "invest",
        "status": "retain",
        "annual_cost": 900_000,
        "planned_savings": 0,
        "progress": 20,
        "effort": "low",
        "priority": 5,
        "target_year": 2030,
        "rationale": "Industry-standard PLM, deeply integrated with engineering.",
        "notes": "Critical for product development; plan cloud migration post-2026.",
    },
    {
        "app": "NexaSCADA",
        "time": "invest",
        "status": "transform",
        "annual_cost": 600_000,
        "planned_savings": 0,
        "progress": 15,
        "effort": "high",
        "priority": 1,
        "target_year": 2027,
        "rationale": "Operational backbone; modernise for real-time analytics.",
        "notes": "Phase 1 cloud edge (2026), Phase 2 AI/ML anomaly layer (2027).",
    },
    {
        "app": "Power BI",
        "time": "invest",
        "status": "retain",
        "annual_cost": 180_000,
        "planned_savings": 0,
        "progress": 40,
        "effort": "low",
        "priority": 4,
        "target_year": 2028,
        "rationale": "Strategic BI standard; consolidation target for analytics.",
        "notes": "Designated enterprise reporting platform.",
    },
    # TOLERATE — keep as-is, stable, no near-term action
    {
        "app": "Salesforce Sales Cloud",
        "time": "tolerate",
        "status": "retain",
        "annual_cost": 320_000,
        "planned_savings": 0,
        "progress": 0,
        "effort": "low",
        "priority": 3,
        "target_year": 2029,
        "rationale": "Leading CRM SaaS; stable and well adopted.",
        "notes": "No change planned; consolidation target for marketing tooling.",
    },
    {
        "app": "SAP Ariba",
        "time": "tolerate",
        "status": "retain",
        "annual_cost": 280_000,
        "planned_savings": 0,
        "progress": 0,
        "effort": "low",
        "priority": 3,
        "target_year": 2028,
        "rationale": "Best-of-breed procurement, strong SAP integration.",
        "notes": "Stable, vendor-supported.",
    },
    {
        "app": "SAP SuccessFactors",
        "time": "tolerate",
        "status": "retain",
        "annual_cost": 350_000,
        "planned_savings": 0,
        "progress": 0,
        "effort": "low",
        "priority": 3,
        "target_year": 2029,
        "rationale": "Leading HCM SaaS; covers workforce management needs.",
        "notes": "Keep current configuration; evaluate AI features in 2027.",
    },
    {
        "app": "Confluence",
        "time": "tolerate",
        "status": "retain",
        "annual_cost": 60_000,
        "planned_savings": 0,
        "progress": 0,
        "effort": "low",
        "priority": 2,
        "target_year": 2028,
        "rationale": "Enterprise collaboration wiki; widely adopted.",
        "notes": "No change planned.",
    },
    # MIGRATE — consolidate into a strategic successor
    {
        "app": "Tableau",
        "time": "migrate",
        "status": "replace",
        "annual_cost": 140_000,
        "planned_savings": 140_000,
        "progress": 40,
        "effort": "medium",
        "priority": 2,
        "target_year": 2026,
        "successor": "Power BI",
        "initiative": "Data Warehouse Consolidation",
        "rationale": (
            "Power BI Pro is already included in every NexaTech Microsoft 365 E5 "
            "seat, while Tableau Server adds ~$70/analyst/month for a 200-analyst "
            "pool ($168k/yr sticker; $140k net after unused subs). Analyst "
            "adoption has already tilted that way — 140 published Power BI "
            "reports vs 30 Tableau workbooks in the last 12 months — and "
            "consolidating removes the parallel role model between Azure AD and "
            "Tableau Server (2 IAM audits per quarter) plus aligns with the "
            "Fabric roadmap owned by the Data & Analytics capability."
        ),
        "risk_note": (
            "~30 published workbooks need re-authoring; 4 use Tableau Prep "
            "flows that must move to Dataflows Gen2. Analyst community "
            "retraining budgeted for Q2 (partner-delivered, 3 cohorts)."
        ),
        "notes": (
            "Q1: freeze new Tableau content, migrate top-10 exec dashboards. "
            "Q2: analyst training + long-tail workbook conversion. "
            "Q3: decommission Tableau Server, cancel renewal (renewal date "
            "2026-11-30 — must be flagged with Procurement by 2026-08-31)."
        ),
    },
    {
        "app": "Jenkins",
        "time": "migrate",
        "status": "replace",
        "annual_cost": 90_000,
        "planned_savings": 90_000,
        "progress": 55,
        "effort": "medium",
        "priority": 2,
        "target_year": 2026,
        "successor": "GitHub Actions",
        "initiative": "DevOps Pipeline Modernization",
        "rationale": (
            "Every service repo already lives on GitHub Enterprise, so CI can "
            "co-locate with the code, PR review and secrets store instead of "
            "the current dual write to Jenkins Credentials. Retiring the two "
            "Jenkins masters + ~50 self-managed agents frees an estimated 1.5 "
            "Platform FTE currently on plugin patching and agent AMI baking, "
            "and shifts compute from an always-on cost centre to per-minute "
            "GitHub-hosted runners that our average pipeline (~7 min) "
            "underuses today."
        ),
        "risk_note": (
            "~40 Groovy pipelines to port to YAML; 6 use shared libraries "
            "that need a reusable-workflow equivalent. Secrets rotation "
            "planned as part of the cut-over to avoid parallel copies."
        ),
        "notes": (
            "Phased by service tier: dev/test pipelines cut over in Q1, "
            "prod-deploy pipelines follow after a 2-week shadow window on "
            "GitHub Actions. Jenkins goes read-only in Q3 2026."
        ),
    },
    {
        "app": "HubSpot Marketing",
        "time": "migrate",
        "status": "replace",
        "annual_cost": 120_000,
        "planned_savings": 120_000,
        "progress": 25,
        "effort": "medium",
        "priority": 2,
        "target_year": 2026,
        "successor": "Salesforce Sales Cloud",
        "initiative": "Digital Transformation Program",
        "rationale": (
            "Sales already runs on Salesforce, so every lead captured in "
            "HubSpot round-trips through a nightly Zapier sync that costs "
            "~4h/week of RevOps time to reconcile and produces duplicate "
            "contact records (12% dup rate on the last audit). Moving to "
            "Salesforce marketing add-ons collapses the two contact DBs, "
            "keeps attribution attached to the Opportunity object instead "
            "of stopping at the handoff, and lets the same Salesforce SSO/"
            "SoD controls cover marketing (currently exempted)."
        ),
        "risk_note": (
            "Campaign performance history must be exported before HubSpot "
            "read-only; lead-scoring rules to be re-modelled in Salesforce "
            "Einstein — expect 4–6 weeks of parallel scoring for validation."
        ),
        "notes": (
            "Migrate active campaigns and contact segments, freeze new "
            "campaigns in HubSpot after Q2. Contract renewal 2026-10-01 — "
            "target sunset before then to avoid another 12-month commit."
        ),
    },
    # ELIMINATE — decommission, function redundant
    {
        "app": "Bitbucket",
        "time": "eliminate",
        "status": "retire",
        "annual_cost": 40_000,
        "planned_savings": 40_000,
        "progress": 20,
        "effort": "low",
        "priority": 2,
        "target_year": 2026,
        "rationale": (
            "After last year's migration wave 85% of active repos are already "
            "on GitHub Enterprise; the residual 15% on Bitbucket forces the "
            "Platform team to maintain two SSO integrations, two "
            "branch-protection policies and two CI runner pools. The "
            "licence savings are real but the security win — one set of "
            "guardrails to audit and one Copilot/CodeQL rollout — is what "
            "the CISO has asked for."
        ),
        "risk_note": (
            "Some legacy repos have external contractor accounts that need "
            "GitHub Enterprise seats provisioned; a handful have "
            "Bitbucket-specific PR templates that need porting."
        ),
        "notes": (
            "Archive read-only inactive repos, migrate the residual 15% "
            "on a rolling basis, then decommission Bitbucket at contract "
            "renewal (2026-09-30)."
        ),
    },
    {
        "app": "Siemens Opcenter APS",
        "time": "eliminate",
        "status": "retire",
        "annual_cost": 200_000,
        "planned_savings": 200_000,
        "progress": 10,
        "effort": "medium",
        "priority": 3,
        "target_year": 2027,
        "rationale": (
            "Opcenter APS runs the same finite-capacity scheduler already "
            "shipped in the Opcenter Execution module NexaTech is licensed "
            "for. The two systems reading the same order book has produced "
            "three shop-floor plan divergences in the last 12 months (last "
            "one caused a half-day of unplanned downtime at the Coventry "
            "line). Consolidating removes that class of incident, drops "
            "the standalone APS licence, and cuts the twice-daily "
            "reconciliation batch job the Ops team currently monitors."
        ),
        "risk_note": (
            "Advanced sequencing rules used by 2 plants must be validated "
            "in Opcenter Execution before the APS scheduler is turned off; "
            "hold-out plan for 90 days after cut-over."
        ),
        "notes": (
            "Confirm capability parity in Q1, run parallel schedulers in "
            "Q2, then decommission APS. Coordinate with the Manufacturing "
            "Excellence programme so plant change-control aligns."
        ),
    },
]

# Legacy rationale strings from earlier releases of this seed. When the seeded
# assessment already exists, the backfill upgrades rows whose rationale still
# matches one of these to the current text — so users see the improved
# reasoning without losing any manual edits they may have made.
_LEGACY_RATIONALES: dict[str, str] = {
    # 1.63.1 → 1.63.2 upgrade: the initial rationales just restated the
    # decision ("Consolidate analytics onto the Power BI standard") instead of
    # explaining why. The strings below are the exact previous seed values,
    # keyed to the app name so the backfill can find and upgrade them.
    "Tableau": "Consolidate analytics onto the Power BI standard.",
    "Jenkins": "Move CI/CD to managed GitHub Actions; cut self-hosted ops.",
    "HubSpot Marketing": "Consolidate marketing automation into the Salesforce stack.",
    "Bitbucket": "Redundant source control; standardise on GitHub.",
    "Siemens Opcenter APS": "Scheduling overlaps with Siemens Opcenter; consolidate.",
}


async def _application_name_map(db: AsyncSession) -> dict[str, Card]:
    """Return a ``{name: Card}`` map of all Application cards."""
    rows = (await db.execute(select(Card).where(Card.type == "Application"))).scalars().all()
    return {c.name: c for c in rows}


async def _initiative_name_map(db: AsyncSession) -> dict[str, Card]:
    """Return a ``{name: Card}`` map of all Initiative cards."""
    rows = (await db.execute(select(Card).where(Card.type == "Initiative"))).scalars().all()
    return {c.name: c for c in rows}


async def seed_application_rationalization(db: AsyncSession) -> dict:
    """Stamp TIME/rationalization attributes onto the demo Application cards.

    Cards are resolved by **name** so this stays correct across idempotent
    re-runs (the old ``_refs`` lookup silently no-op'd once the demo was
    already seeded). Idempotent: skips if any app already carries a status.
    """
    by_name = await _application_name_map(db)

    existing = await db.execute(
        select(Card)
        .where(
            (Card.type == "Application") & (Card.attributes.has_key("rationalization_status"))  # noqa: W601
        )
        .limit(1)
    )
    if existing.scalar_one_or_none():
        return {"skipped": "application_rationalization"}

    updated_count = 0
    for d in RATIONALIZATION_DECISIONS:
        card = by_name.get(d["app"])
        if not card:
            continue
        attrs = dict(card.attributes or {})
        attrs.update(
            {
                "rationalization_status": d["status"],
                "rationalization_rationale": d["rationale"],
                "modernization_effort": d["effort"],
                "modernization_priority": d["priority"],
                "target_transformation_year": d["target_year"],
                "rationalization_notes": d["notes"],
            }
        )
        card.attributes = attrs
        updated_count += 1

    await db.commit()
    return {"applications_rationalized": updated_count}


async def seed_rationalization_assessment(db: AsyncSession) -> dict:
    """Create the demo 'FY26 Application Portfolio Review' board assessment.

    This is what the Application Rationalization board lists. One
    ``RationalizationAssessment`` with a TIME decision per real Application
    card (resolved by name). Idempotent on the assessment name.
    """
    name = "FY26 Application Portfolio Review"
    existing = await db.execute(
        select(RationalizationAssessment).where(RationalizationAssessment.name == name).limit(1)
    )
    existing_assessment = existing.scalar_one_or_none()
    if existing_assessment is not None:
        # Existing seeded installs pre-date the ``rationale`` column. Backfill:
        #   (a) fill rationale when the row still has NULL
        #   (b) upgrade rationale when it exactly matches a known legacy string
        #       from an earlier release (see ``_LEGACY_RATIONALES``)
        # An admin-edited rationale that isn't NULL and isn't in the legacy
        # set is preserved untouched.
        by_name = await _application_name_map(db)
        rationale_by_card_name = {
            d["app"]: d.get("rationale") for d in RATIONALIZATION_DECISIONS if d.get("rationale")
        }
        legacy_by_card_id: dict[uuid.UUID, str] = {}
        current_by_card_id: dict[uuid.UUID, str] = {}
        for app_name, rationale in rationale_by_card_name.items():
            card = by_name.get(app_name)
            if card is None:
                continue
            current_by_card_id[card.id] = rationale
            legacy = _LEGACY_RATIONALES.get(app_name)
            if legacy:
                legacy_by_card_id[card.id] = legacy
        if not current_by_card_id:
            return {"skipped": "rationalization_assessment"}

        existing_decisions = await db.execute(
            select(AssessmentDecision).where(
                AssessmentDecision.assessment_id == existing_assessment.id,
                AssessmentDecision.card_id.in_(current_by_card_id.keys()),
            )
        )
        backfilled = 0
        upgraded = 0
        for decision in existing_decisions.scalars().all():
            new_text = current_by_card_id.get(decision.card_id)
            if new_text is None:
                continue
            legacy_text = legacy_by_card_id.get(decision.card_id)
            if decision.rationale is None:
                decision.rationale = new_text
                backfilled += 1
            elif legacy_text is not None and decision.rationale.strip() == legacy_text.strip():
                decision.rationale = new_text
                upgraded += 1
        if backfilled or upgraded:
            await db.commit()
            return {
                "skipped": "rationalization_assessment",
                "backfilled_rationale": backfilled,
                "upgraded_rationale": upgraded,
            }
        return {"skipped": "rationalization_assessment"}

    by_name = await _application_name_map(db)
    initiatives_by_name = await _initiative_name_map(db)

    owner = (
        await db.execute(select(User).where(User.email == "abdulrahim@nexatech.demo").limit(1))
    ).scalar_one_or_none()

    target_savings = sum(d.get("planned_savings") or 0 for d in RATIONALIZATION_DECISIONS)
    assessment = RationalizationAssessment(
        name=name,
        description=(
            "Annual TIME-framework review of the NexaTech application portfolio: "
            "tolerate, invest, migrate, or eliminate each application to cut "
            "redundancy and fund strategic platforms."
        ),
        status="active",
        target_savings=float(target_savings),
        created_by=owner.id if owner else None,
    )
    db.add(assessment)
    await db.flush()  # assign assessment.id

    decision_count = 0
    for d in RATIONALIZATION_DECISIONS:
        card = by_name.get(d["app"])
        if not card:
            continue
        successor = by_name.get(d["successor"]) if d.get("successor") else None
        initiative = initiatives_by_name.get(d["initiative"]) if d.get("initiative") else None
        db.add(
            AssessmentDecision(
                assessment_id=assessment.id,
                card_id=card.id,
                time_decision=d["time"],
                successor_id=successor.id if successor else None,
                initiative_id=initiative.id if initiative else None,
                annual_cost=float(d["annual_cost"]) if d.get("annual_cost") is not None else None,
                planned_savings=(
                    float(d["planned_savings"]) if d.get("planned_savings") is not None else None
                ),
                rationale=d.get("rationale"),
                risk_note=d.get("risk_note"),
                notes=d.get("notes"),
                progress=int(d.get("progress") or 0),
            )
        )
        decision_count += 1

    await db.commit()
    return {"assessments": 1, "decisions": decision_count}


# ===================================================================
# PHASE 2: COMPLIANCE FINDINGS -> RISK PROMOTION
# ===================================================================


async def seed_compliance_finding_to_risk_promotion(db: AsyncSession) -> dict:
    """Link 3-5 high-severity compliance findings to promoted risks."""
    # Import compliance finding model
    try:
        from app.models.turbolens import TurboLensComplianceFinding
    except ImportError:
        return {"skipped": "compliance_to_risk"}

    # Get sample findings
    findings = await db.execute(
        select(TurboLensComplianceFinding)
        .where(TurboLensComplianceFinding.severity == "critical")
        .limit(3)
    )
    findings_list = findings.scalars().all()

    if not findings_list:
        return {"skipped": "compliance_to_risk"}

    # Check idempotence - if any finding is already linked to a risk
    for finding in findings_list:
        if finding.risk_id:
            return {"skipped": "compliance_to_risk"}

    user_result = await db.execute(
        select(User).where(User.email == "abdulrahim@nexatech.demo").limit(1)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        return {"skipped": "compliance_to_risk"}

    from app.services.risk_service import next_reference

    promoted_risks = []
    for finding in findings_list[:3]:
        # Create risk from finding
        risk = Risk(
            reference=await next_reference(db),
            title=f"Risk: {finding.requirement}",
            description=finding.evidence or "Compliance gap identified",
            category="compliance",
            source_type="compliance",
            source_ref=str(finding.id),
            initial_probability="high",
            initial_impact="high",
            initial_level="high",
            owner_id=user.id,
            target_resolution_date=(datetime.now(timezone.utc) + timedelta(days=90)).date(),
            status="identified",
        )
        db.add(risk)
        await db.flush()  # persist so the next next_reference() sees this row
        promoted_risks.append(risk)

        # Link finding to risk
        finding.risk_id = risk.id

    await db.commit()

    return {
        "compliance_findings_promoted": len(promoted_risks),
        "risks_created": len(promoted_risks),
    }


# ===================================================================
# PHASE 2: SCENARIOS (WHAT-IF ARCHITECTURE)
# ===================================================================


async def seed_scenarios(db: AsyncSession) -> dict:
    """Create sample architecture scenarios for what-if analysis."""
    # Check idempotence
    existing = await db.execute(
        select(Scenario).where(Scenario.name == "Cloud Migration Target State (2027)").limit(1)
    )
    if existing.scalar_one_or_none():
        return {"skipped": "scenarios"}

    scenarios_data = [
        {
            "name": "Cloud Migration Target State (2027)",
            "description": (
                "Post-SAP, multi-cloud deployment target state with ~60% workload on cloud.\n"
                "Cloud allocation: 60%, On-premise: 40%. Primary: Azure, Secondary: AWS.\n"
                "Key initiatives: SAP S/4 Cloud, Data Lake on Azure, Multi-cloud backbone."
            ),
            "status": "review",
            "changes": [
                {
                    "op": "add",
                    "card_type": "Application",
                    "name": "Azure Data Lake",
                    "payload": {
                        "description": "Cloud-native enterprise data lake on Azure Data Lake Storage Gen2.",
                        "attributes": {"businessCriticality": "businessCritical"},
                    },
                },
                {
                    "op": "modify",
                    "target": "SAP S/4HANA",
                    "payload": {
                        "description": "Re-platformed to SAP S/4HANA Cloud (private edition) on Azure.",
                        "attributes": {"hostingType": "cloud"},
                    },
                },
                {"op": "retire", "target": "Bitbucket"},
                {"op": "retire", "target": "Tableau"},
            ],
        },
        {
            "name": "AI/ML Capability Center Maturity (2028)",
            "description": (
                "Full data science platform with enterprise ML Ops and governance.\n"
                "Capability maturity: Level 4 (Managed). Expected production models: 15. Team size: 25.\n"
                "Key initiatives: AI Center of Excellence, MLOps Automation, Data Governance."
            ),
            "status": "draft",
            "changes": [
                {
                    "op": "add",
                    "card_type": "Application",
                    "name": "MLOps Platform",
                    "payload": {
                        "description": "Enterprise MLOps platform for model training, registry, and deployment.",
                        "attributes": {"businessCriticality": "businessOperational"},
                    },
                },
                {
                    "op": "add",
                    "card_type": "BusinessCapability",
                    "name": "AI/ML Engineering",
                    "payload": {
                        "description": "Capability to build, deploy, and operate machine-learning models at scale.",
                    },
                },
                {
                    "op": "modify",
                    "target": "NexaSCADA",
                    "payload": {
                        "description": "Extended with a real-time ML inference layer for predictive maintenance.",
                    },
                },
            ],
        },
    ]

    owner = (
        await db.execute(select(User).where(User.email == "abdulrahim@nexatech.demo").limit(1))
    ).scalar_one_or_none()
    by_name = {
        c.name: c
        for c in (
            await db.execute(
                select(Card).where(Card.type.in_(["Application", "BusinessCapability"]))
            )
        )
        .scalars()
        .all()
    }

    scenarios = []
    change_count = 0
    for scenario_data in scenarios_data:
        scenario = Scenario(
            name=scenario_data["name"],
            description=scenario_data["description"],
            status=scenario_data["status"],
            created_by=owner.id if owner else None,
        )
        db.add(scenario)
        await db.flush()  # assign scenario.id
        scenarios.append(scenario)

        for ch in scenario_data.get("changes", []):
            op = ch["op"]
            target = by_name.get(ch["target"]) if ch.get("target") else None
            if op in ("modify", "retire") and target is None:
                continue  # named card not in this dataset — skip rather than seed a dangling change
            db.add(
                ScenarioChange(
                    scenario_id=scenario.id,
                    op=op,
                    card_type=(target.type if target else ch.get("card_type")),
                    target_card_id=(target.id if target else None),
                    name=(ch.get("name") or (target.name if target else None)),
                    payload=ch.get("payload", {}),
                )
            )
            change_count += 1

    await db.commit()

    return {"scenarios": len(scenarios), "changes": change_count}


# ===================================================================
# PHASE 2: TECHNOLOGY ROADMAPS
# ===================================================================


async def seed_roadmaps(db: AsyncSession) -> dict:
    """Create multi-year technology and application roadmaps."""
    # Check idempotence
    existing = await db.execute(
        select(Roadmap).where(Roadmap.name == "Application Modernization Roadmap").limit(1)
    )
    if existing.scalar_one_or_none():
        return {"skipped": "roadmaps"}

    roadmaps_data = [
        {
            "name": "Application Modernization Roadmap",
            "description": "3-year plan to modernize legacy applications and adopt cloud-native architecture",
            "config": {
                "start_year": 2026,
                "end_year": 2028,
                "type": "application_modernization",
                "status": "active",
                "phases": [
                    {
                        "phase": "Phase 1",
                        "quarter": "2026 Q3-Q4",
                        "title": "Containerize Legacy .NET Apps",
                        "description": "Package 3 legacy .NET applications into Docker containers",
                        "deliverables": [
                            "Containerized Billing App",
                            "Containerized Workflow Engine",
                            "Registry Setup",
                        ],
                        "effort_months": 6,
                        "budget_usd": 400000,
                    },
                    {
                        "phase": "Phase 2",
                        "quarter": "2027 Q1-Q2",
                        "title": "Microservices Split of ERP",
                        "description": "Decompose monolithic custom ERP into 5-7 microservices",
                        "deliverables": [
                            "Finance Service",
                            "Procurement Service",
                            "Inventory Service",
                            "API Gateway",
                        ],
                        "effort_months": 9,
                        "budget_usd": 1200000,
                    },
                    {
                        "phase": "Phase 3",
                        "quarter": "2027 Q4 - 2028 Q2",
                        "title": "Full Cloud Deployment",
                        "description": "Deploy all modernized applications to Kubernetes on Azure",
                        "deliverables": [
                            "AKS Cluster Setup",
                            "CI/CD Pipeline",
                            "Monitoring & Logging",
                            "Disaster Recovery",
                        ],
                        "effort_months": 8,
                        "budget_usd": 800000,
                    },
                ],
            },
        },
        {
            "name": "Data & Analytics Roadmap",
            "description": "Build enterprise data lakehouse and AI-ready analytics platform",
            "config": {
                "start_year": 2026,
                "end_year": 2028,
                "type": "data_analytics",
                "status": "active",
                "phases": [
                    {
                        "phase": "Phase 1",
                        "quarter": "2026 Q4",
                        "title": "Data Lake Foundation",
                        "description": "Build Azure Data Lake Gen 2 with initial staging and bronze zones",
                        "deliverables": [
                            "Azure Data Lake Storage",
                            "Security & Access Control",
                            "Partition Strategy",
                        ],
                        "effort_months": 4,
                        "budget_usd": 300000,
                    },
                    {
                        "phase": "Phase 2",
                        "quarter": "2027 Q1-Q2",
                        "title": "Real-Time Ingestion Pipeline",
                        "description": "Build Kafka-based streaming and batch ingestion from 20+ source systems",
                        "deliverables": [
                            "Kafka Cluster",
                            "Azure Data Factory Pipelines",
                            "Ingestion Framework",
                        ],
                        "effort_months": 8,
                        "budget_usd": 600000,
                    },
                    {
                        "phase": "Phase 3",
                        "quarter": "2027 Q3-Q4",
                        "title": "BI & Visualization Platform",
                        "description": "Deploy Tableau and Power BI for enterprise analytics and dashboards",
                        "deliverables": [
                            "Tableau Server",
                            "Power BI Premium",
                            "Data Models",
                            "Self-Service Portal",
                        ],
                        "effort_months": 6,
                        "budget_usd": 400000,
                    },
                ],
            },
        },
    ]

    roadmaps = []
    for roadmap_data in roadmaps_data:
        roadmap = Roadmap(
            name=roadmap_data["name"],
            description=roadmap_data["description"],
            config=roadmap_data["config"],
        )
        db.add(roadmap)
        roadmaps.append(roadmap)

    await db.commit()

    return {"roadmaps": len(roadmaps)}


# ===================================================================
# PHASE 2: TECHNOLOGY STANDARDS (RADAR + EXCEPTIONS)
# ===================================================================


async def seed_tech_standards(db: AsyncSession) -> dict:
    """Seed the Technology Standards radar + a few time-boxed exceptions.

    Two passes: create every standard, then wire ``replacement_id`` by name
    (sunset/prohibited standards point at their preferred successor). A small
    exception register links real Application cards to standards they deviate
    from. Idempotent on the catalogue's presence.
    """
    existing = await db.execute(select(TechStandard).limit(1))
    if existing.scalar_one_or_none():
        return {"skipped": "tech_standards"}

    owner = (
        await db.execute(select(User).where(User.email == "talal@nexatech.demo").limit(1))
    ).scalar_one_or_none()
    approver = (
        await db.execute(select(User).where(User.email == "abdulrahim@nexatech.demo").limit(1))
    ).scalar_one_or_none()

    # (name, category, status, replacement_name, description, rationale)
    standards_data = [
        # data
        (
            "PostgreSQL",
            "data",
            "preferred",
            None,
            "Primary relational database for new services.",
            "Open-source, strong JSON support, low TCO.",
        ),
        (
            "Microsoft SQL Server",
            "data",
            "allowed",
            None,
            "Permitted where Windows/.NET integration is required.",
            "Existing licensing and skills.",
        ),
        (
            "Oracle Database",
            "data",
            "sunset",
            "PostgreSQL",
            "Legacy RDBMS; migrate workloads to PostgreSQL.",
            "High licensing cost; consolidate.",
        ),
        (
            "MongoDB",
            "data",
            "tolerated",
            None,
            "Allowed for document-oriented workloads only.",
            "Niche fit; avoid as default.",
        ),
        # cloud
        (
            "Microsoft Azure",
            "cloud",
            "preferred",
            None,
            "Primary public cloud platform.",
            "Strategic vendor; enterprise agreement in place.",
        ),
        (
            "Amazon Web Services",
            "cloud",
            "allowed",
            None,
            "Secondary cloud for specific managed services.",
            "Avoid lock-in; multi-cloud posture.",
        ),
        (
            "Kubernetes (AKS)",
            "cloud",
            "preferred",
            None,
            "Standard container orchestration on Azure.",
            "Portability and elasticity.",
        ),
        (
            "On-prem VMware",
            "cloud",
            "sunset",
            "Kubernetes (AKS)",
            "Legacy virtualization; exit by 2028.",
            "Shift CAPEX to cloud elasticity.",
        ),
        # integration
        (
            "REST / OpenAPI",
            "integration",
            "preferred",
            None,
            "Default synchronous integration style.",
            "Ubiquitous, well-tooled, documented contracts.",
        ),
        (
            "Apache Kafka",
            "integration",
            "preferred",
            None,
            "Standard for event streaming and async integration.",
            "Scalable, durable event backbone.",
        ),
        (
            "SOAP / XML",
            "integration",
            "tolerated",
            None,
            "Only for legacy partner interfaces.",
            "Heavyweight; avoid for new builds.",
        ),
        (
            "Flat-file FTP",
            "integration",
            "prohibited",
            "REST / OpenAPI",
            "No new file-drop integrations.",
            "Brittle, insecure, hard to monitor.",
        ),
        # security
        (
            "OAuth 2.1 / OIDC",
            "security",
            "preferred",
            None,
            "Standard for authn/authz across services.",
            "Modern, interoperable, MFA-ready.",
        ),
        (
            "SAML 2.0",
            "security",
            "allowed",
            None,
            "Permitted for enterprise SSO with legacy IdPs.",
            "Widely supported by SaaS.",
        ),
        (
            "Basic Auth",
            "security",
            "prohibited",
            "OAuth 2.1 / OIDC",
            "Disallowed for all service-to-service calls.",
            "Credentials in headers; no token scoping.",
        ),
        # technology
        (
            ".NET 8",
            "technology",
            "preferred",
            None,
            "Primary backend stack for enterprise services.",
            "LTS, cross-platform, strong ecosystem.",
        ),
        (
            "React 18",
            "technology",
            "preferred",
            None,
            "Standard SPA framework for web front-ends.",
            "Component model, large talent pool.",
        ),
        (
            "AngularJS (v1)",
            "technology",
            "prohibited",
            "React 18",
            "End-of-life; no new development.",
            "Unsupported upstream; security risk.",
        ),
    ]

    by_name: dict[str, TechStandard] = {}
    for i, (name, cat, status, _repl, desc, rat) in enumerate(standards_data):
        std = TechStandard(
            name=name,
            category=cat,
            status=status,
            description=desc,
            rationale=rat,
            owner_id=owner.id if owner else None,
            sort_order=i,
        )
        db.add(std)
        by_name[name] = std
    await db.flush()  # assign ids before wiring replacements

    for name, _cat, _status, repl, _desc, _rat in standards_data:
        if repl and repl in by_name:
            by_name[name].replacement_id = by_name[repl].id

    # Exception register — real apps deviating from a standard, time-boxed.
    apps = await _application_name_map(db)
    inits = {
        c.name: c
        for c in (await db.execute(select(Card).where(Card.type == "Initiative"))).scalars().all()
    }
    exceptions_data = [
        (
            "Oracle Database",
            "PTC Windchill",
            "Legacy PLM Retirement",
            "approved",
            "Windchill requires Oracle until the PLM platform is retired.",
            "Network isolation + quarterly DBA security review.",
            date(2027, 6, 30),
        ),
        (
            "SOAP / XML",
            "SAP S/4HANA",
            "SAP S/4HANA Migration",
            "approved",
            "Partner EDI gateway still consumes SOAP services.",
            "Gateway behind WAF; scheduled migration to REST in 2027.",
            date(2027, 12, 31),
        ),
        (
            "On-prem VMware",
            "NexaSCADA",
            None,
            "requested",
            "OT workload not yet certified for AKS.",
            "Segmented OT network; compensating monitoring in place.",
            date(2028, 3, 31),
        ),
    ]
    exc_count = 0
    for std_name, app_name, init_name, status, justification, controls, expiry in exceptions_data:
        std = by_name.get(std_name)
        card = apps.get(app_name)
        if not std or not card:
            continue
        db.add(
            StandardException(
                standard_id=std.id,
                card_id=card.id,
                initiative_id=inits[init_name].id if init_name and init_name in inits else None,
                justification=justification,
                compensating_controls=controls,
                status=status,
                expiry_date=expiry,
                approver_id=(approver.id if approver and status == "approved" else None),
                created_by=owner.id if owner else None,
            )
        )
        exc_count += 1

    await db.commit()
    return {"tech_standards": len(standards_data), "exceptions": exc_count}


# ===================================================================
# PHASE 2: ARCHITECTURE REVIEW BOARD
# ===================================================================


async def seed_arb_reviews(db: AsyncSession) -> dict:
    """Seed Architecture Review Board decisions over real subject cards.

    Idempotent on the presence of any ARB review.
    """
    existing = await db.execute(select(ArbReview).limit(1))
    if existing.scalar_one_or_none():
        return {"skipped": "arb_reviews"}

    reviewer = (
        await db.execute(select(User).where(User.email == "abdulrahim@nexatech.demo").limit(1))
    ).scalar_one_or_none()
    by_name = {
        c.name: c
        for c in (
            await db.execute(select(Card).where(Card.type.in_(["Application", "Initiative"])))
        )
        .scalars()
        .all()
    }
    now = datetime.now(timezone.utc)

    # (title, subject_name, status, summary, decision_notes, decided_days_ago)
    reviews_data = [
        (
            "Adopt Power BI as the enterprise BI standard",
            "Power BI",
            "approved",
            "Standardise enterprise reporting on Power BI; designate as preferred BI tool.",
            "Approved. Power BI becomes the strategic BI platform; new dashboards target Power BI.",
            21,
        ),
        (
            "Retire Tableau and consolidate to Power BI",
            "Tableau",
            "approved",
            "Decommission Tableau and migrate dashboards to Power BI to remove tool overlap.",
            "Approved with condition: migrate all production workbooks before licence renewal.",
            14,
        ),
        (
            "Migrate CI/CD from Jenkins to GitHub Actions",
            "Jenkins",
            "approved",
            "Move pipelines to managed GitHub Actions; retire self-hosted Jenkins.",
            "Approved. Reduces self-hosted runner ops and aligns with the DevOps roadmap.",
            10,
        ),
        (
            "SAP S/4HANA Cloud migration target architecture",
            "SAP S/4HANA Migration",
            "scheduled",
            "Review the proposed private-cloud landing zone and integration topology for S/4HANA.",
            None,
            None,
        ),
        (
            "NexaSCADA real-time analytics modernization",
            "NexaSCADA",
            "deferred",
            "Add a real-time ML inference layer for predictive maintenance.",
            "Deferred pending OT security assessment and a cost/benefit refinement.",
            7,
        ),
        (
            "Decommission Bitbucket source control",
            "Bitbucket",
            "rejected",
            "Proposal to retire Bitbucket immediately and migrate all repos to GitHub.",
            "Rejected for now: migration plan lacks a repo inventory and cutover window. Resubmit.",
            5,
        ),
    ]

    count = 0
    for title, subject_name, status, summary, notes, decided_days_ago in reviews_data:
        subject = by_name.get(subject_name)
        decided_at = (
            now - timedelta(days=decided_days_ago) if decided_days_ago is not None else None
        )
        db.add(
            ArbReview(
                title=title,
                subject_card_id=subject.id if subject else None,
                summary=summary,
                status=status,
                decision_notes=notes,
                reviewer_id=reviewer.id if reviewer and decided_at else None,
                decided_at=decided_at,
                created_by=reviewer.id if reviewer else None,
            )
        )
        count += 1

    await db.commit()
    return {"arb_reviews": count}


# ===================================================================
# MAIN SEED ENTRY POINT
# ===================================================================


async def seed_demo_extended(db: AsyncSession) -> dict:
    """Master seed function for all extended demo data.

    Returns a summary dict of all seeded data.
    """
    results = {}

    # PHASE 1: Quick Wins
    results["sample_users"] = await seed_sample_users(db)
    results["calculations"] = await seed_calculations(db)
    results["user_favorites"] = await seed_user_favorites(db)
    results["user_bookmarks"] = await seed_user_bookmarks(db)
    results["notifications"] = await seed_notifications(db)
    results["documents"] = await seed_documents_and_attachments(db)

    # PHASE 2: Medium Complexity
    results["recurring_todos"] = await seed_recurring_todos(db)
    results["risk_mitigation"] = await seed_risk_mitigation_occurrences(db)
    results["application_rationalization"] = await seed_application_rationalization(db)
    results["rationalization_assessment"] = await seed_rationalization_assessment(db)
    results["compliance_to_risk"] = await seed_compliance_finding_to_risk_promotion(db)
    results["scenarios"] = await seed_scenarios(db)
    results["roadmaps"] = await seed_roadmaps(db)
    results["tech_standards"] = await seed_tech_standards(db)
    results["arb_reviews"] = await seed_arb_reviews(db)

    return results
