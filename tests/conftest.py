import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://notely:notely@localhost:5432/notely_test",
)

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def client():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        session.execute(text("TRUNCATE TABLE notes"))
        session.commit()
    with TestClient(app) as c:
        yield c