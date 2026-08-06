import os
from uuid import UUID

from fastapi import FastAPI, HTTPException, status

from app.models import Note, NoteCreate

APP_VERSION = os.getenv("APP_VERSION", "dev")

app = FastAPI(title="Notely", version=APP_VERSION)

_notes: dict[UUID, Note] = {}


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "version": APP_VERSION}


@app.get("/readyz")
def readyz() -> dict[str, str]:
    return {"status": "ready"}


@app.get("/notes", response_model=list[Note])
def list_notes() -> list[Note]:
    return list(_notes.values())


@app.post("/notes", response_model=Note, status_code=status.HTTP_201_CREATED)
def create_note(payload: NoteCreate) -> Note:
    note = Note(**payload.model_dump())
    _notes[note.id] = note
    return note


@app.get("/notes/{note_id}", response_model=Note)
def get_note(note_id: UUID) -> Note:
    note = _notes.get(note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@app.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: UUID) -> None:
    if _notes.pop(note_id, None) is None:
        raise HTTPException(status_code=404, detail="Note not found")