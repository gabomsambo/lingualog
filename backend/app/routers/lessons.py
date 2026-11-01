"""Curated mini-lessons and no-model sentence drills."""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from app.services import lesson_service
from database import create_supabase_client

logger = logging.getLogger(__name__)
router = APIRouter(tags=["lessons"])


def _user_id(request: Request) -> str:
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not provided")
    return user_id


@router.post("/lessons/offers/{entry_id}")
def offer_lesson(entry_id: UUID, request: Request):
    """Check the saved entry and offer one recurring Spanish tag inline."""
    try:
        offer = lesson_service.offer_for_entry(
            create_supabase_client(), _user_id(request), str(entry_id)
        )
        return {"offer": offer}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Could not check lesson offers for entry %s: %s", entry_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not check your lesson offers",
        ) from exc


@router.post("/lessons/offers/{l2}/{tag}/seen")
def mark_lesson_seen(l2: str, tag: str, request: Request):
    """Record that the learner opened a previously offered lesson."""
    try:
        changed = lesson_service.mark_seen(create_supabase_client(), _user_id(request), l2, tag)
        if not changed:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson offer not found")
        return {"seen": True}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Could not mark lesson %s as seen: %s", tag, exc)
        raise HTTPException(status_code=500, detail="Could not update this lesson") from exc


@router.post("/lessons/offers/{l2}/{tag}/snooze")
def snooze_lesson(l2: str, tag: str, request: Request):
    """Set a seven-day snooze for a previously offered lesson."""
    try:
        until = lesson_service.snooze(create_supabase_client(), _user_id(request), l2, tag)
        if not until:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson offer not found")
        return {"snoozed_until": until}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Could not snooze lesson %s: %s", tag, exc)
        raise HTTPException(status_code=500, detail="Could not snooze this lesson") from exc


@router.get("/lessons/offers/{l2}/{tag}/drill")
def get_lesson_drill(l2: str, tag: str, entry_id: UUID, request: Request):
    """Build cloze items from the learner's own corrected Spanish sentences."""
    try:
        items = lesson_service.drill_for_entry(
            create_supabase_client(), _user_id(request), l2, tag, str(entry_id)
        )
        return {"items": items}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Could not build lesson drill for %s: %s", tag, exc)
        raise HTTPException(status_code=500, detail="Could not prepare this practice") from exc
