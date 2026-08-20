"""Statistik-Dienst: fragt notely über dessen HTTP-API ab und liefert Kennzahlen."""

import os

import httpx
from fastapi import FastAPI, HTTPException

# In-Cluster-DNS: Service "notely", Port 80 -> kein Port im URL nötig.
NOTELY_URL = os.environ.get("NOTELY_URL", "http://notely")

app = FastAPI()


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.get("/readyz")
def readyz() -> dict:
    # notely ist unsere fremde Abhängigkeit -> gehört in Readiness, nie in Liveness.
    try:
        r = httpx.get(f"{NOTELY_URL}/healthz", timeout=2)
        r.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="notely unreachable") from exc
    return {"status": "ready"}


@app.get("/stats")
def stats() -> dict:
    try:
        r = httpx.get(f"{NOTELY_URL}/notes", timeout=5)
        r.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="notely unreachable") from exc
    notes = r.json()
    return {
        "total": len(notes),
        "archived": sum(1 for n in notes if n.get("archived")),
    }