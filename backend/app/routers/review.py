"""Vocabulary review with FSRS: a session of cards, a two-button answer, and what is waiting."""

import logging
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from app.services import review_service
from review_scheduler import SESSION_SIZE

logger = logging.getLogger(__name__)

router = APIRouter(tags=["review"])


class ReviewAnswer(BaseModel):
    rating: Literal["again", "got_it"]
    reps: Optional[int] = Field(
        None, ge=0, description="The card's reps when it was served; a mismatch means it was already reviewed"
    )
    duration_ms: Optional[int] = Field(None, ge=0, le=3_600_000)


def _user_id(request: Request) -> str:
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not provided")
    return user_id


@router.get("/review/session")
async def get_review_session(
    request: Request,
    language: str,
    mode: Literal["normal", "catchup"] = "normal",
    limit: int = Query(SESSION_SIZE, ge=1, le=50),
):
    """The next cards to review in one language. Catch-up serves reviews only, a few a day."""
    user_id = _user_id(request)
    try:
        return review_service.get_session(user_id, language, mode, limit)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Could not build review session for %s %s: %s", user_id, language, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not load your review"
        ) from exc


@router.get("/review/summary")
async def get_review_summary(request: Request):
    """Reviews waiting per studied language, for the dashboard."""
    user_id = _user_id(request)
    try:
        return review_service.get_summary(user_id)
    except Exception as exc:
        logger.error("Could not load review summary for %s: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not load your review"
        ) from exc


@router.post("/review/{card_id}")
async def answer_review_card(card_id: UUID, answer: ReviewAnswer, request: Request):
    """Record "Again" or "Got it" for one of the caller's cards and schedule it."""
    user_id = _user_id(request)
    try:
        return review_service.submit_review(
            user_id, str(card_id), answer.rating, answer.reps, answer.duration_ms
        )
    except review_service.ReviewNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review card not found") from exc
    except review_service.CardSuspended as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "card_suspended", "message": "This word is not being studied"},
        ) from exc
    except review_service.StaleReview as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "stale_review", "message": "This card was already reviewed"},
        ) from exc
    except Exception as exc:
        logger.error("Could not record review for %s card %s: %s", user_id, card_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not record your review"
        ) from exc
