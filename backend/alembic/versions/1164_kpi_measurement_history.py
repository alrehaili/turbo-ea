"""One KPI measurement history; KPI target ratification; metricKey uniqueness.

Decisions D-19, D-17a and D-26 (approved 2026-10-25):

* ``kpi_measurements`` replaces ``kpi_snapshots``. Every snapshot row becomes
  four ``daily`` observations (one per dashboard series) with the value, date
  and capture time it already had, so the dashboard trend reads exactly what it
  read before. ``kpi_snapshots`` is then dropped; ``downgrade`` rebuilds it from
  those observations.
* ``kpi_target_ratifications`` records targets ratified by an authorized KPI
  target approver.
* ``uq_cards_kpi_metric_key``: one ACTIVE KPI card per ``metricKey``. No card
  carries the field yet, so the index cannot fail on existing data.

Both new tables declare server defaults on their timestamp columns (see the
``created_at`` / ``updated_at`` rule in CLAUDE.md).

[FORK]

Revision ID: 1164
Revises: 1163
Create Date: 2026-10-25
"""

from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "1164"
down_revision: Union[str, None] = "1163"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None

#: Metric keys the four legacy snapshot columns become.
LEGACY_SERIES = ("total_cards", "avg_data_quality", "approved_count", "broken_count")
LEGACY_PREFIX = "dashboard."
LEGACY_VERSION = "dashboard@1"


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "kpi_measurements",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("kind", sa.String(8), nullable=False),
        sa.Column("metric_key", sa.String(64), nullable=True),
        sa.Column(
            "kpi_card_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cards.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("period_type", sa.String(16), nullable=False),
        sa.Column("period_key", sa.String(16), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("observed_on", sa.Date(), nullable=True),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("numerator", sa.Float(), nullable=True),
        sa.Column("denominator", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(32), nullable=True),
        sa.Column("calculation_version", sa.String(32), nullable=True),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column(
            "recorded_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "verified_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "supersedes_id",
            UUID(as_uuid=True),
            sa.ForeignKey("kpi_measurements.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("correction_reason", sa.Text(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "metric_key IS NOT NULL OR kpi_card_id IS NOT NULL", name="ck_kpi_measurements_subject"
        ),
        sa.CheckConstraint("kind IN ('daily', 'period')", name="ck_kpi_measurements_kind"),
    )
    op.create_index(
        "uq_kpi_measurements_daily",
        "kpi_measurements",
        ["metric_key", "period_key"],
        unique=True,
        postgresql_where=sa.text("kind = 'daily'"),
    )
    op.create_index(
        "uq_kpi_measurements_card_period",
        "kpi_measurements",
        ["kpi_card_id", "period_key"],
        unique=True,
        postgresql_where=sa.text(
            "kind = 'period' AND status <> 'superseded' AND kpi_card_id IS NOT NULL"
        ),
    )
    op.create_index(
        "uq_kpi_measurements_metric_period",
        "kpi_measurements",
        ["metric_key", "period_key"],
        unique=True,
        postgresql_where=sa.text(
            "kind = 'period' AND status <> 'superseded' AND kpi_card_id IS NULL"
        ),
    )
    op.create_index("ix_kpi_measurements_card", "kpi_measurements", ["kpi_card_id"])

    # Every snapshot row → four daily observations, keeping its date and capture time.
    for column in LEGACY_SERIES:
        op.execute(
            sa.text(
                "INSERT INTO kpi_measurements (id, kind, metric_key, period_type, period_key, "
                "period_start, period_end, value, calculation_version, source, status, "
                "recorded_at, created_at, updated_at) "
                "SELECT gen_random_uuid(), 'daily', :metric, 'day', "
                "to_char(snapshot_date, 'YYYY-MM-DD'), snapshot_date, snapshot_date, "
                f"{column}::double precision, :version, 'system', 'observed', "
                "created_at, created_at, updated_at FROM kpi_snapshots"
            ).bindparams(metric=LEGACY_PREFIX + column, version=LEGACY_VERSION)
        )

    op.drop_index("ix_kpi_snapshots_snapshot_date", table_name="kpi_snapshots")
    op.drop_table("kpi_snapshots")

    op.create_table(
        "kpi_target_ratifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "kpi_card_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cards.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("target_value", sa.Float(), nullable=False),
        sa.Column("target_date", sa.String(10), nullable=True),
        sa.Column("baseline_value", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(64), nullable=True),
        sa.Column("direction", sa.String(32), nullable=True),
        sa.Column(
            "ratified_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "ratified_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("note", sa.Text(), nullable=True),
        *_timestamps(),
    )
    op.create_index(
        "ix_kpi_target_ratifications_kpi_card_id", "kpi_target_ratifications", ["kpi_card_id"]
    )

    op.create_index(
        "uq_cards_kpi_metric_key",
        "cards",
        [sa.text("(attributes ->> 'metricKey')")],
        unique=True,
        postgresql_where=sa.text(
            "type = 'KPI' AND status = 'ACTIVE' AND (attributes ->> 'metricKey') IS NOT NULL "
            "AND (attributes ->> 'metricKey') <> ''"
        ),
    )


def downgrade() -> None:
    op.drop_index("uq_cards_kpi_metric_key", table_name="cards")
    op.drop_index("ix_kpi_target_ratifications_kpi_card_id", table_name="kpi_target_ratifications")
    op.drop_table("kpi_target_ratifications")

    op.create_table(
        "kpi_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("total_cards", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_data_quality", sa.Float(), nullable=False, server_default="0"),
        sa.Column("approved_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("broken_count", sa.Integer(), nullable=False, server_default="0"),
        *_timestamps(),
        sa.UniqueConstraint("snapshot_date", name="uq_kpi_snapshots_snapshot_date"),
    )
    op.create_index("ix_kpi_snapshots_snapshot_date", "kpi_snapshots", ["snapshot_date"])
    # The dashboard series back into one row per day; everything else recorded
    # in the history has no place in the old table and is dropped with it.
    op.execute(
        sa.text(
            "INSERT INTO kpi_snapshots (id, snapshot_date, total_cards, avg_data_quality, "
            "approved_count, broken_count, created_at, updated_at) "
            "SELECT gen_random_uuid(), period_start, "
            "COALESCE(MAX(value) FILTER (WHERE metric_key = 'dashboard.total_cards'), 0)::int, "
            "COALESCE(MAX(value) FILTER (WHERE metric_key = 'dashboard.avg_data_quality'), 0), "
            "COALESCE(MAX(value) FILTER (WHERE metric_key = 'dashboard.approved_count'), 0)::int, "
            "COALESCE(MAX(value) FILTER (WHERE metric_key = 'dashboard.broken_count'), 0)::int, "
            "MIN(recorded_at), MAX(updated_at) "
            "FROM kpi_measurements WHERE kind = 'daily' AND metric_key LIKE 'dashboard.%' "
            "GROUP BY period_start"
        )
    )
    op.drop_index("ix_kpi_measurements_card", table_name="kpi_measurements")
    op.drop_index("uq_kpi_measurements_metric_period", table_name="kpi_measurements")
    op.drop_index("uq_kpi_measurements_card_period", table_name="kpi_measurements")
    op.drop_index("uq_kpi_measurements_daily", table_name="kpi_measurements")
    op.drop_table("kpi_measurements")
