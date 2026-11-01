"""Paste class material, confirm its practice chips, and continue into the editor."""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from ai.class_note import (
    MAX_CLASS_NOTE_CHARS,
    MAX_CLASS_NOTE_PHRASES,
    MAX_CLASS_NOTE_TASKS,
    MAX_CLASS_NOTE_WORDS,
    ClassNoteWord,
    ClassPracticeTask,
)
from ai.gemini import GeminiError
from app.services import class_note_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["class-notes"])


class ClassNoteCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_CLASS_NOTE_CHARS)
    language: str = Field(..., pattern=r"^[a-z]{2}(-[A-Z]{2})?$", max_length=5)


class ClassNoteConfirmation(BaseModel):
    words: List[ClassNoteWord] = Field(default_factory=list, max_length=MAX_CLASS_NOTE_WORDS)
    grammar_focus: Optional[str] = Field(None, max_length=200)
    phrases: List[str] = Field(default_factory=list, max_length=MAX_CLASS_NOTE_PHRASES)
    tasks: List[ClassPracticeTask] = Field(default_factory=list, max_length=MAX_CLASS_NOTE_TASKS)
    level: Optional[str] = Field(None, pattern=r"^(A1|A2|B1|B2|C1|C2)$")
    length_hint: Optional[str] = Field(None, max_length=80)
    grammar_scope: Optional[str] = Field(None, max_length=300)


def _user_id(request: Request) -> str:
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not provided")
    return user_id


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class note not found")


@router.post("/class-notes", status_code=status.HTTP_201_CREATED)
async def create_class_note(payload: ClassNoteCreate, request: Request):
    """Extract words, a grammar focus, phrases, and three tasks from pasted text."""
    user_id = _user_id(request)
    try:
        return await class_note_service.create_class_note(user_id, payload.language, payload.text)
    except class_note_service.ClassNoteRefused as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": "You have reached today's class-note limit."},
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except GeminiError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": exc.code, "message": "Class material could not be processed just now."},
        ) from exc
    except Exception as exc:
        logger.error("Could not extract class note for %s: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not prepare your class material",
        ) from exc


@router.get("/class-notes/waiting")
async def get_waiting_class_note(
    request: Request,
    language: str = Query(..., pattern=r"^[a-z]{2}(-[A-Z]{2})?$", max_length=5),
):
    """Return the newest class note that does not yet have a journal entry."""
    try:
        return class_note_service.get_waiting_class_note(_user_id(request), language)
    except Exception as exc:
        logger.error("Could not load a waiting class note: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not load your class note",
        ) from exc


@router.get("/class-notes/{note_id}")
async def get_class_note(note_id: UUID, request: Request):
    try:
        return class_note_service.get_class_note(_user_id(request), str(note_id))
    except class_note_service.ClassNoteNotFound as exc:
        raise _not_found() from exc
    except Exception as exc:
        logger.error("Could not load class note %s: %s", note_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not load your class note",
        ) from exc


@router.post("/class-notes/{note_id}/confirm")
async def confirm_class_note(note_id: UUID, payload: ClassNoteConfirmation, request: Request):
    """Save the learner's edited chips and create cached class-note encounters."""
    try:
        return class_note_service.confirm_class_note(
            _user_id(request), str(note_id), payload.model_dump(exclude_none=True)
        )
    except class_note_service.ClassNoteNotFound as exc:
        raise _not_found() from exc
    except class_note_service.ClassNoteRefused as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": "This class note can no longer be changed."},
        ) from exc
    except Exception as exc:
        logger.error("Could not confirm class note %s: %s", note_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save your class-note choices",
        ) from exc
