"""The migration history must have exactly one head.

The backend resolves ``head`` at startup (``app.main._migrate_and_seed``);
with two heads Alembic raises ``MultipleHeads`` and the container exits before
serving a request. That happened when upstream's 166/167 and the fork's 1178
both branched from 165 — merged in 1179.
"""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND = Path(__file__).resolve().parents[2]


def _script() -> ScriptDirectory:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    return ScriptDirectory.from_config(cfg)


def test_migration_history_has_a_single_head():
    heads = _script().get_heads()
    assert len(heads) == 1, f"Multiple Alembic heads {heads}: add a merge migration"


def test_head_includes_fork_and_upstream_session_branches():
    script = _script()
    ancestors = {rev.revision for rev in script.walk_revisions("base", script.get_current_head())}
    assert {"1178", "166", "167"} <= ancestors
