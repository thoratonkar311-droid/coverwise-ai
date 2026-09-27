from pathlib import Path
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
import sqlalchemy as sa

from app.db.session import Base
import app.models  # Register all models


def test_alembic_models_registered_in_metadata() -> None:
    """Verify that all core MVP tables are defined and registered in Base.metadata."""
    expected_tables = {
        "policies",
        "treatments",
        "policy_analyses",
        "coverage_rules",
        "simulations",
        "evidence_references",
    }
    actual_tables = set(Base.metadata.tables.keys())
    assert expected_tables.issubset(actual_tables), f"Missing tables: {expected_tables - actual_tables}"


def test_alembic_migration_script_integrity() -> None:
    """Verify Alembic configuration discovers migration revisions correctly."""
    backend_dir = Path(__file__).resolve().parent.parent
    alembic_ini_path = backend_dir / "alembic.ini"

    assert alembic_ini_path.exists(), "alembic.ini not found"

    alembic_cfg = Config(str(alembic_ini_path))
    alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))

    script = ScriptDirectory.from_config(alembic_cfg)
    heads = script.get_heads()

    assert len(heads) == 1, f"Expected exactly 1 migration head, got: {heads}"
    head_revision = script.get_revision(heads[0])
    assert head_revision is not None
    assert "initial_schema" in head_revision.doc


def test_alembic_migration_execution_and_downgrade(tmp_path: Path) -> None:
    """Verify executing Alembic upgrade and downgrade against a safe test database."""
    backend_dir = Path(__file__).resolve().parent.parent
    alembic_ini_path = backend_dir / "alembic.ini"
    test_db_file = tmp_path / "test_migration.db"
    test_db_url = f"sqlite:///{test_db_file}"

    alembic_cfg = Config(str(alembic_ini_path))
    alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", test_db_url)

    # 1. Upgrade to head
    command.upgrade(alembic_cfg, "head")

    engine = sa.create_engine(test_db_url)
    inspector = sa.inspect(engine)
    created_tables = set(inspector.get_table_names())

    expected_tables = {
        "policies",
        "treatments",
        "policy_analyses",
        "coverage_rules",
        "simulations",
        "evidence_references",
        "alembic_version",
    }
    assert expected_tables.issubset(created_tables), f"Missing tables after migration: {expected_tables - created_tables}"

    # 2. Downgrade to base
    command.downgrade(alembic_cfg, "base")

    inspector_after = sa.inspect(engine)
    remaining_tables = set(inspector_after.get_table_names())
    # Only alembic_version table remains after full downgrade
    assert "policies" not in remaining_tables
    assert "simulations" not in remaining_tables
    engine.dispose()
