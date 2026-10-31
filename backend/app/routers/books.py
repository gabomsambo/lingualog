"""Book mode: the reading companion. Books, sessions, mark-only capture, page photos and the glossary."""

import logging
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field

from ai.gemini import GeminiError
from app.services import book_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["books"])

Page = Field(None, ge=1, le=20000)


class BookCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    author: Optional[str] = Field(None, max_length=200)
    language: str = Field(..., min_length=2, max_length=35)


class BookPatch(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    author: Optional[str] = Field(None, max_length=200)
    status: Optional[Literal["reading", "finished", "paused"]] = None


class SessionStart(BaseModel):
    page_from: Optional[int] = Page


class MarkCreate(BaseModel):
    word: str = Field(..., min_length=1, max_length=200)
    sentence: Optional[str] = Field(None, max_length=2000)
    page: Optional[int] = Page


class SessionEnd(BaseModel):
    page_to: Optional[int] = Page


class MarksSkip(BaseModel):
    encounter_ids: list[UUID] = Field(..., min_length=1, max_length=200)


def _user_id(request: Request) -> str:
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not provided")
    return user_id


def _not_found(exc: Exception) -> HTTPException:
    detail = "Reading session not found" if isinstance(exc, book_service.SessionNotFound) else "Book not found"
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _closed() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"code": "session_ended", "message": "This reading session has ended"},
    )


@router.post("/books", status_code=status.HTTP_201_CREATED)
async def create_book(payload: BookCreate, request: Request):
    user_id = _user_id(request)
    try:
        return book_service.create_book(user_id, payload.title, payload.author, payload.language)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/books")
async def list_books(request: Request, language: Optional[str] = None):
    return book_service.list_books(_user_id(request), language)


@router.get("/books/{book_id}")
async def get_book(book_id: UUID, request: Request):
    try:
        return book_service.book_detail(_user_id(request), str(book_id))
    except book_service.BookNotFound as exc:
        raise _not_found(exc) from exc


@router.patch("/books/{book_id}")
async def patch_book(book_id: UUID, patch: BookPatch, request: Request):
    user_id = _user_id(request)
    changes = patch.model_dump(exclude_unset=True)
    if changes.get("title", "x") is None or changes.get("status", "reading") is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="title and status cannot be null"
        )
    try:
        return book_service.update_book(user_id, str(book_id), changes)
    except book_service.BookNotFound as exc:
        raise _not_found(exc) from exc


@router.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(book_id: UUID, request: Request):
    user_id = _user_id(request)
    try:
        book_service.delete_book(user_id, str(book_id))
    except book_service.BookNotFound as exc:
        raise _not_found(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/books/{book_id}/sessions", status_code=status.HTTP_201_CREATED)
async def start_session(book_id: UUID, payload: SessionStart, request: Request):
    """Start reading, or resume the book's open session."""
    user_id = _user_id(request)
    try:
        session = book_service.open_session(user_id, str(book_id), payload.page_from)
    except book_service.BookNotFound as exc:
        raise _not_found(exc) from exc
    return book_service.session_summary(session, len(book_service.session_marks(user_id, session["id"])))


@router.post("/books/{book_id}/sessions/{session_id}/marks", status_code=status.HTTP_201_CREATED)
async def add_mark(book_id: UUID, session_id: UUID, payload: MarkCreate, request: Request, response: Response):
    """Mark a word and keep reading. No model call: the card is built when the session ends."""
    user_id = _user_id(request)
    try:
        book = book_service.get_book(user_id, str(book_id))
        session = book_service.get_session(user_id, str(book_id), str(session_id))
        mark = book_service.add_mark(user_id, book, session, payload.word, payload.sentence, payload.page)
    except (book_service.BookNotFound, book_service.SessionNotFound) as exc:
        raise _not_found(exc) from exc
    except book_service.SessionClosed as exc:
        raise _closed() from exc
    if not mark["created"]:
        response.status_code = status.HTTP_200_OK
    return mark


@router.delete(
    "/books/{book_id}/sessions/{session_id}/marks/{mark_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_mark(book_id: UUID, session_id: UUID, mark_id: UUID, request: Request):
    """Undo a mark made by mistake while the session is open."""
    user_id = _user_id(request)
    try:
        removed = book_service.remove_mark(user_id, str(book_id), str(session_id), str(mark_id))
    except book_service.SessionNotFound as exc:
        raise _not_found(exc) from exc
    except book_service.SessionClosed as exc:
        raise _closed() from exc
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mark not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/books/{book_id}/sessions/{session_id}/end")
async def end_session(book_id: UUID, session_id: UUID, payload: SessionEnd, request: Request):
    user_id = _user_id(request)
    try:
        return book_service.end_session(user_id, str(book_id), str(session_id), payload.page_to)
    except (book_service.BookNotFound, book_service.SessionNotFound) as exc:
        raise _not_found(exc) from exc


@router.post("/books/{book_id}/sessions/{session_id}/cards")
async def build_cards(book_id: UUID, session_id: UUID, request: Request):
    """Build the cards for this session's marks in one batch, then return the choices to make."""
    user_id = _user_id(request)
    try:
        book = book_service.get_book(user_id, str(book_id))
        book_service.get_session(user_id, str(book_id), str(session_id))
        return await book_service.build_session_cards(user_id, book, str(session_id))
    except (book_service.BookNotFound, book_service.SessionNotFound) as exc:
        raise _not_found(exc) from exc


@router.get("/books/{book_id}/sessions/{session_id}/triage")
async def get_triage(book_id: UUID, session_id: UUID, request: Request):
    user_id = _user_id(request)
    try:
        book_service.get_session(user_id, str(book_id), str(session_id))
    except book_service.SessionNotFound as exc:
        raise _not_found(exc) from exc
    return book_service.triage(user_id, str(book_id), str(session_id))


@router.post("/books/{book_id}/marks/skip")
async def skip_marks(book_id: UUID, payload: MarksSkip, request: Request):
    user_id = _user_id(request)
    try:
        book_service.get_book(user_id, str(book_id))
    except book_service.BookNotFound as exc:
        raise _not_found(exc) from exc
    return {"skipped": book_service.skip_marks(user_id, str(book_id), [str(i) for i in payload.encounter_ids])}


@router.get("/books/{book_id}/glossary")
async def get_glossary(book_id: UUID, request: Request):
    try:
        return book_service.glossary(_user_id(request), str(book_id))
    except book_service.BookNotFound as exc:
        raise _not_found(exc) from exc


@router.get("/books/{book_id}/progress")
async def get_progress(book_id: UUID, request: Request):
    try:
        return book_service.progress(_user_id(request), str(book_id))
    except book_service.BookNotFound as exc:
        raise _not_found(exc) from exc


@router.get("/books/{book_id}/writing-words")
async def get_writing_words(book_id: UUID, request: Request, days: int = Query(7, ge=1, le=60)):
    """This week's words from the book, to pre-fill "write about what you read"."""
    try:
        return book_service.writing_words(_user_id(request), str(book_id), days)
    except book_service.BookNotFound as exc:
        raise _not_found(exc) from exc


async def _read_limited_body(request: Request, limit: int) -> bytes:
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > limit:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail={"code": "photo_too_large"})
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > limit:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail={"code": "photo_too_large"}
            )
    return bytes(body)


@router.post("/books/{book_id}/page-photo")
async def read_page_photo(book_id: UUID, request: Request):
    """Transcribe a photographed page and pre-highlight words to mark.

    The body is the raw JPEG, PNG or WebP image. It is held in memory for the call and never stored.
    """
    user_id = _user_id(request)
    try:
        book = book_service.get_book(user_id, str(book_id))
    except book_service.BookNotFound as exc:
        raise _not_found(exc) from exc
    image = await _read_limited_body(request, book_service.MAX_PHOTO_BYTES)
    mime_type = book_service.sniff_image(image)
    if not mime_type:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail={"code": "photo_unsupported"}
        )
    try:
        return await book_service.read_page(user_id, book, image, mime_type)
    except book_service.PhotoRefused as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code}) from exc
    except GeminiError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
