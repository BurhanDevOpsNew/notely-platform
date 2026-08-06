import pytest
from fastapi.testclient import TestClient

from app.main import _notes, app

@pytest.fixture
def client():
    _notes.clear()  # Clear the notes dictionary before each test
    with TestClient(app) as c:
        yield c