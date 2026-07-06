"""AI-assisted NORA authoring ([FORK] — noraPlan.md WP5.5).

Uses the existing TurboLens AI plumbing to draft NORA-flavoured improvement
opportunities from live landscape signals. Suggestions are **advisory only** —
they are returned for human review and, when accepted, land as ``proposed``
records (governance approval stays a human decision, per the plan).

Arabic output is supported by switching the prompt's target language.
"""

from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import Card
from app.models.improvement_opportunity import OPPORTUNITY_DOMAINS, OPPORTUNITY_PRIORITIES
from app.models.relation import Relation
from app.services.turbolens_ai import call_ai, get_ai_config, is_ai_configured, parse_json

log = logging.getLogger(__name__)

_LANG = {"ar": "Arabic", "en": "English"}
_MAX_SUGGESTIONS = 8


async def _landscape_signals(db: AsyncSession) -> list[str]:
    """Compact, human-readable signal lines the model reasons over. Every query
    is best-effort so a sparse landscape still yields a useful prompt."""
    signals: list[str] = []

    async def _safe(coro):
        try:
            return await coro
        except Exception as e:  # noqa: BLE001
            log.warning("nora authoring signal failed: %s", e)
            try:
                await db.rollback()
            except Exception:
                pass
            return None

    # Business capabilities with no supporting application.
    async def _uncovered_caps():
        supported = select(Relation.source_id).union(select(Relation.target_id)).subquery()
        rows = await db.execute(
            select(Card.name)
            .where(
                Card.type == "BusinessCapability",
                Card.status != "ARCHIVED",
                ~Card.id.in_(select(supported.c.source_id)),
            )
            .limit(15)
        )
        return [n for (n,) in rows.all()]

    caps = await _safe(_uncovered_caps()) or []
    if caps:
        signals.append(
            f"Business capabilities with no linked cards (coverage gaps): {', '.join(caps)}"
        )

    # Low data-quality applications.
    async def _low_quality():
        rows = await db.execute(
            select(Card.name)
            .where(
                Card.type == "Application",
                Card.status != "ARCHIVED",
                Card.data_quality < 50,
            )
            .limit(15)
        )
        return [n for (n,) in rows.all()]

    lowq = await _safe(_low_quality()) or []
    if lowq:
        signals.append(f"Applications with weak data quality (<50%): {', '.join(lowq)}")

    # Target/changed cards with no delivering initiative (untraceable changes).
    async def _untraceable():
        init_ids = (
            select(Relation.source_id)
            .join(Card, Card.id == Relation.target_id)
            .where(Card.type == "Initiative")
            .union(
                select(Relation.target_id)
                .join(Card, Card.id == Relation.source_id)
                .where(Card.type == "Initiative")
            )
            .subquery()
        )
        rows = await db.execute(
            select(Card.name)
            .where(
                Card.status != "ARCHIVED",
                Card.architecture_state.in_(("target", "transition")),
                ~Card.id.in_(select(init_ids.c.source_id)),
            )
            .limit(15)
        )
        return [n for (n,) in rows.all()]

    untraceable = await _safe(_untraceable()) or []
    if untraceable:
        signals.append(
            f"Target/transition cards not linked to any initiative (untraceable): "
            f"{', '.join(untraceable)}"
        )

    # Landscape size context.
    async def _counts():
        rows = await db.execute(
            select(Card.type, func.count()).where(Card.status != "ARCHIVED").group_by(Card.type)
        )
        return {t: c for t, c in rows.all()}

    counts = await _safe(_counts()) or {}
    if counts:
        top = ", ".join(f"{t}: {c}" for t, c in sorted(counts.items(), key=lambda x: -x[1])[:8])
        signals.append(f"Landscape composition — {top}")

    return signals


def _build_prompt(signals: list[str], locale: str, focus: str | None) -> tuple[str, str]:
    lang = _LANG.get(locale, "English")
    system = (
        "You are an enterprise-architecture advisor working within Saudi Arabia's NORA "
        "(National Overall Reference Architecture) methodology. You propose concrete, "
        "governable improvement opportunities that feed a transition plan. You never invent "
        "cards or facts beyond the signals provided."
    )
    signal_block = (
        "\n".join(f"- {s}" for s in signals)
        or "- (no strong signals; propose general NORA-aligned improvements)"
    )
    focus_line = f"\nFocus area requested by the user: {focus}\n" if focus else ""
    prompt = (
        f"Landscape signals:\n{signal_block}\n{focus_line}\n"
        f"Propose up to {_MAX_SUGGESTIONS} improvement opportunities. Write ALL text "
        f"(title and description) in {lang}. Return ONLY a JSON array; each item:\n"
        '{"title": str, "description": str, '
        '"domain": one of ["BA","AA","DA","TA"], '
        '"priority": one of ["low","medium","high"]}\n'
        "Titles concise; descriptions 1-3 sentences explaining the opportunity and its NORA "
        "rationale. Domain = the architecture domain most affected (BA business, AA application, "
        "DA data, TA technology)."
    )
    return system, prompt


def _clean(items: object, locale: str) -> list[dict]:
    out: list[dict] = []
    if not isinstance(items, list):
        return out
    for it in items:
        if not isinstance(it, dict):
            continue
        title = str(it.get("title") or "").strip()[:300]
        if not title:
            continue
        domain = it.get("domain") if it.get("domain") in OPPORTUNITY_DOMAINS else "BA"
        priority = it.get("priority") if it.get("priority") in OPPORTUNITY_PRIORITIES else "medium"
        out.append(
            {
                "title": title,
                "description": str(it.get("description") or "").strip()[:2000],
                "domain": domain,
                "priority": priority,
                "source": "ai",
            }
        )
        if len(out) >= _MAX_SUGGESTIONS:
            break
    return out


async def suggest_opportunities(
    db: AsyncSession, locale: str = "en", focus: str | None = None
) -> list[dict]:
    """Return AI-drafted improvement-opportunity suggestions (not persisted)."""
    config = await get_ai_config(db)
    if not is_ai_configured(config):
        raise ValueError("AI_NOT_CONFIGURED")

    signals = await _landscape_signals(db)
    system, prompt = _build_prompt(signals, locale, focus)
    result = await call_ai(db, prompt, max_tokens=2048, system_prompt=system)
    parsed = parse_json(result.get("text", ""))
    return _clean(parsed, locale)
