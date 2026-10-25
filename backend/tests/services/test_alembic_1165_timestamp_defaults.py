"""Exercise the corrective DDL against isolated PostgreSQL tables, not create_all."""

import importlib.util
import uuid
from datetime import datetime
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

from tests.services.test_alembic_timestamp_defaults import _REPAIRED

_PATH = Path(__file__).resolve().parents[2] / "alembic/versions/1165_fork_timestamp_defaults.py"
_SPEC = importlib.util.spec_from_file_location("mig1165", _PATH)
mig = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(mig)


def test_repair_registry_and_revision():
    assert set(mig.REPAIRED_MIGRATIONS) == _REPAIRED
    assert mig.revision == "1165"
    assert mig.down_revision == "1164"


async def test_repair_preserves_rows_and_custom_defaults_and_allows_inserts(db):
    connection = await db.connection()

    def exercise(conn):
        schema = f"timestamp_repair_{uuid.uuid4().hex}"
        conn.execute(sa.schema.CreateSchema(schema))
        # Transaction-local and restored before returning to the shared fixture.
        conn.execute(sa.text(f'SET LOCAL search_path TO "{schema}"'))
        try:
            metadata = sa.MetaData()
            tables = []
            for index, name in enumerate(mig.REPAIRED_MIGRATIONS.values()):
                table = sa.Table(
                    name,
                    metadata,
                    sa.Column("id", sa.Integer, primary_key=True),
                    sa.Column("created_at", sa.DateTime, nullable=False),
                    sa.Column(
                        "updated_at",
                        sa.DateTime,
                        nullable=False,
                        server_default=sa.text("'2001-01-01'::timestamp") if index == 0 else None,
                    ),
                )
                table.create(conn)
                conn.execute(
                    table.insert().values(
                        id=1, created_at=datetime(2000, 1, 1), updated_at=datetime(2000, 1, 2)
                    )
                )
                tables.append(table)
            with Operations.context(MigrationContext.configure(conn)):
                mig.upgrade()
                mig.upgrade()  # Fresh/defaulted installations are a no-op.
                mig.downgrade()  # The repair remains safe after a downgrade.
            for index, table in enumerate(tables):
                columns = {c["name"]: c for c in sa.inspect(conn).get_columns(table.name)}
                assert all(columns[c]["default"] for c in mig.TIMESTAMP_COLUMNS)
                old = conn.execute(sa.select(table).where(table.c.id == 1)).one()
                assert old.created_at == datetime(2000, 1, 1)
                assert old.updated_at == datetime(2000, 1, 2)
                conn.execute(table.insert().values(id=2))
                new = conn.execute(sa.select(table).where(table.c.id == 2)).one()
                assert new.created_at is not None and new.updated_at is not None
                if index == 0:
                    assert new.updated_at == datetime(2001, 1, 1)
        finally:
            conn.execute(sa.text("SET LOCAL search_path TO public"))
            conn.execute(sa.schema.DropSchema(schema, cascade=True))

    await connection.run_sync(exercise)
