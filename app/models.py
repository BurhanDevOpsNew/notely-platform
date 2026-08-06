from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

class NoteCreate(BaseModel):
        title: str = Field(min_length=1, max_length=200)
        body: str = Field(default="", max_length=10_000)

class Note(BaseModel):
        id: UUID = Field(default_factory=uuid4)
        title: str = Field(min_length=1, max_length=200)
        body: str = Field(default="", max_length=10_000)
        created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))