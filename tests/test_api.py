def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_readyz(client):
    assert client.get("/readyz").status_code == 200


def test_list_notes_is_empty_initially(client):
    assert client.get("/notes").json() == []


def test_create_and_get_note(client):
    r = client.post("/notes", json={"title": "Erste Notiz", "body": "Hallo"})
    assert r.status_code == 201
    note = r.json()
    assert note["title"] == "Erste Notiz"

    r = client.get(f"/notes/{note['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == note["id"]


def test_get_unknown_note_returns_404(client):
    r = client.get("/notes/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


def test_delete_note(client):
    note = client.post("/notes", json={"title": "Weg damit"}).json()
    assert client.delete(f"/notes/{note['id']}").status_code == 204
    assert client.get(f"/notes/{note['id']}").status_code == 404


def test_create_note_rejects_empty_title(client):
    assert client.post("/notes", json={"title": ""}).status_code == 422

def test_patch_archives_note(client):
    note = client.post("/notes", json={"title": "Zu archivieren"}).json()
    assert note["archived"] is False

    r = client.patch(f"/notes/{note['id']}", json={"archived": True})
    assert r.status_code == 200
    assert r.json()["archived"] is True


def test_patch_keeps_unmentioned_fields(client):
    note = client.post(
        "/notes", json={"title": "Bleibt", "body": "Auch das bleibt"}
    ).json()

    r = client.patch(f"/notes/{note['id']}", json={"archived": True})
    assert r.status_code == 200

    updated = r.json()
    assert updated["title"] == "Bleibt"
    assert updated["body"] == "Auch das bleibt"
    assert updated["archived"] is True


def test_patch_rejects_empty_title(client):
    note = client.post("/notes", json={"title": "Gültig"}).json()
    r = client.patch(f"/notes/{note['id']}", json={"title": ""})
    assert r.status_code == 422


def test_patch_unknown_note_returns_404(client):
    r = client.patch(
        "/notes/00000000-0000-0000-0000-000000000000", json={"archived": True}
    )
    assert r.status_code == 404

def test_metrics_endpoint(client):
    client.get("/healthz")

    r = client.get("/metrics")
    assert r.status_code == 200
    assert "http_requests_total" in r.text
    assert 'path="/healthz"' in r.text