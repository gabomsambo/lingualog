"""The word bank beside the editor: a few of the learner's own words to write with."""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.services import word_bank_service
from word_bank import DEFAULT_BANK_SIZE, MAX_BANK_SIZE

logger = logging.getLogger(__name__)

router = APIRouter(tags=["word-bank"])


@router.get("/word-bank")
async def get_word_bank(
    request: Request,
    language: str,
    count: int = Query(DEFAULT_BANK_SIZE, ge=1, le=MAX_BANK_SIZE),
    exclude: List[UUID] = Query(default_factory=list, max_length=50),
):
    """Words to use in today's entry: due or at-risk ones first, then words never used yet.

    ``exclude`` lists words already on screen, so a shuffle offers different ones.
    """
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not provided")
    try:
        return word_bank_service.get_bank(user_id, language, count, [str(word_id) for word_id in exclude])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Could not build the word bank for %s %s: %s", user_id, language, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not load your word bank"
        ) from exc
