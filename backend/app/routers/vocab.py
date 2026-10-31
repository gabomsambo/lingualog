"""Vocabulary progress, notebook lists, export and the optional placement check."""

import logging
from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field

import placement as placement_check
import vocab_export
from app.services import stats_service, vocab_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["vocabulary"])


class PlacementAnswer(BaseModel):
    """The sample words the learner says they know."""

    known: List[str] = Field(default_factory=list, max_length=200)


def _user_id(request: Request) -> str:
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not provided")
    return user_id


@router.get("/vocabulary/progress")
async def get_vocabulary_progress(request: Request, language: Optional[str] = None):
    """Everything the Progress page shows: notebook, review health, encounters, the week."""
    user_id = _user_id(request)
    try:
        return stats_service.get_vocab_progress(user_id, language)
    except Exception as exc:
        logger.error("Could not build vocabulary progress for %s %s: %s", user_id, language, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not load your progress"
        ) from exc


@router.get("/vocabulary/lists")
async def get_vocabulary_lists(request: Request, language: Optional[str] = None):
    """The notebook's lists with counts: smart lists, tags, per-entry and per-book."""
    user_id = _user_id(request)
    try:
        return vocab_service.get_lists(user_id, language)
    except Exception as exc:
        logger.error("Could not build vocabulary lists for %s %s: %s", user_id, language, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not load your lists"
        ) from exc


@router.get("/vocabulary/export")
async def export_vocabulary(
    request: Request,
    format: Literal["csv", "apkg"] = "csv",
    language: Optional[str] = None,
    list_id: Optional[str] = Query(None, alias="list"),
    tag: Optional[str] = None,
    entry_id: Optional[str] = None,
    book_id: Optional[str] = None,
    item_status: Optional[str] = Query(None, alias="status"),
    source: Optional[str] = None,
):
    """Download the notebook (or one list) as CSV or as an Anki deck, with sentence and source."""
    user_id = _user_id(request)
    try:
        selector = vocab_service.selector_from(
            list_id, tag, entry_id, book_id, item_status, source
        )
        rows = vocab_service.export_rows(user_id, language, selector)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Could not export vocabulary for %s: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not export your words"
        ) from exc

    if format == "csv":
        content = vocab_export.rows_to_csv(rows).encode("utf-8")
        media_type = "text/csv; charset=utf-8"
    else:
        content = vocab_export.rows_to_apkg(rows)
        media_type = "application/octet-stream"
    return Response(
        content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="lingualog-vocabulary.{format}"'},
    )


@router.get("/placement/{language}")
async def get_placement_check(language: str, request: Request):
    """The words of the placement check for one language, and the last stored result."""
    user_id = _user_id(request)
    if not placement_check.has_samples(language):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No placement check for this language yet"
        )
    result = None
    for row in vocab_service.load_profiles(user_id):
        if row.get("l2") == language:
            result = row.get("placement")
            break
    return {
        "language": language,
        "words": placement_check.sample_words(language),
        "bands": [list(band) for band in placement_check.band_samples(language)],
        "result": result,
    }


@router.post("/placement/{language}")
async def post_placement_check(language: str, answer: PlacementAnswer, request: Request):
    """Score one placement check. The result is an estimate, never a score."""
    user_id = _user_id(request)
    if not placement_check.has_samples(language):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No placement check for this language yet"
        )
    result = vocab_service.placement_result(language, answer.known)
    try:
        vocab_service.save_placement(user_id, language, result)
    except Exception as exc:  # The estimate is still returned when the profile row is missing.
        logger.warning("Could not store placement for %s %s: %s", user_id, language, exc)
    return result
