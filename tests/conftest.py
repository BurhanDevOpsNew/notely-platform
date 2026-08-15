import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://notely:notely@localhost:5432/notely_test",
)

# Schutz gegen stille Umgebungsübernahme: ein bereits gesetztes DATABASE_URL gewinnt
# oben durch setdefault. Ohne diese Zusicherung würde das TRUNCATE weiter unten auf
# der Entwicklungsdatenbank landen, wenn jemand sie in derselben Shell exportiert hat.
assert os.environ["DATABASE_URL"].endswith("_test"), (
    "Refusing to run tests against a non-test database: "
    f"{os.environ['DATABASE_URL']}"
)

from app.db import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def migrated_database():
    """Schema einmal pro Testlauf über Alembic aufbauen, nicht über create_all.

    Damit prüft die Testsuite die Migrationen mit — eine kaputte Migration fällt
    hier auf und nicht erst beim Deploy.
    """
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    command.upgrade(config, "head")


@pytest.fixture
def client(migrated_database):
    with SessionLocal() as session:
        session.execute(text("TRUNCATE TABLE notes"))
        session.commit()
    with TestClient(app) as c:
        yield c