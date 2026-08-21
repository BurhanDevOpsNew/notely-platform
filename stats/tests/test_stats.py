"""Tests für den stats-Dienst — notely wird durch ein Test-Doppel ersetzt."""

import httpx
from fastapi.testclient import TestClient

from stats.app.main import app

client = TestClient(app)


class FakeResponse:
    """Minimales Doppel für httpx.Response — nur was der Code wirklich benutzt."""

    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_healthz_needs_no_upstream():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_metrics_endpoint_exists():
    # Die Scrape-Annotation im Deployment verspricht diesen Endpunkt (Etappe 31 D).
    r = client.get("/metrics")
    assert r.status_code == 200
    assert b"python_gc_objects_collected_total" in r.content


def test_stats_counts_notes(monkeypatch):
    notes = [{"archived": True}, {"archived": False}, {"archived": True}]
    monkeypatch.setattr(httpx, "get", lambda url, timeout: FakeResponse(notes))
    r = client.get("/stats")
    assert r.status_code == 200
    assert r.json() == {"total": 3, "archived": 2}


def test_stats_reports_dead_upstream_as_502(monkeypatch):
    def boom(url, timeout):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "get", boom)
    r = client.get("/stats")
    assert r.status_code == 502


def test_readyz_reports_dead_upstream_as_503(monkeypatch):
    def boom(url, timeout):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "get", boom)
    r = client.get("/readyz")
    assert r.status_code == 503