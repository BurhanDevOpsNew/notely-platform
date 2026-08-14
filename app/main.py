import os
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import Base, engine, get_session
from app.models import Note, NoteCreate, NoteRead

APP_VERSION = os.getenv("APP_VERSION", "dev")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Notely", version=APP_VERSION, lifespan=lifespan)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "version": APP_VERSION}


@app.get("/readyz")
def readyz(session: Session = Depends(get_session)) -> dict[str, str]:
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database unavailable",
        )
    return {"status": "ready"}


@app.get("/notes", response_model=list[NoteRead])
def list_notes(session: Session = Depends(get_session)) -> list[Note]:
    return list(session.scalars(select(Note).order_by(Note.created_at)))


@app.post("/notes", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
def create_note(payload: NoteCreate, session: Session = Depends(get_session)) -> Note:
    note = Note(**payload.model_dump())
    session.add(note)
    session.commit()
    return note


@app.get("/notes/{note_id}", response_model=NoteRead)
def get_note(note_id: UUID, session: Session = Depends(get_session)) -> Note:
    note = session.get(Note, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@app.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: UUID, session: Session = Depends(get_session)) -> None:
    note = session.get(Note, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    session.delete(note)
    session.commit()