"""Suggested immersion-level changes. Owner-only. Never applied unless accepted."""

import logging

from fastapi import APIRouter, HTTPException, Request, status

from app.services.level_suggestion_service import (
    NoLevelSuggestion,
    accept_level_suggestion,
    current_suggestions,
    dismiss_level_suggestion,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["level-suggestions"])


def _user_id(request: Request) -> str:
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not provided")
    return user_id


@router.get("/user/level-suggestions")
async def get_level_suggestions(request: Request):
    """The learner's current step-up or step-down suggestion for each language, if any."""
    user_id = _user_id(request)
    try:
        return {"suggestions": current_suggestions(user_id)}
    except Exception as exc:
        logger.error("Could not load level suggestions for %s: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not load level suggestions",
        ) from exc


@router.post("/user/level-suggestions/{l2}/accept")
async def accept_suggestion(l2: str, request: Request):
    """Set this language's immersion to the suggested level. One tap, no other change."""
    user_id = _user_id(request)
    try:
        return accept_level_suggestion(user_id, l2)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except NoLevelSuggestion as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No level suggestion for this language",
        ) from exc
    except Exception as exc:
        logger.error("Could not accept level suggestion for %s %s: %s", user_id, l2, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not update immersion level",
        ) from exc


@router.post("/user/level-suggestions/{l2}/dismiss")
async def dismiss_suggestion(l2: str, request: Request):
    """Hide this language's suggestion for the configured snooze window."""
    user_id = _user_id(request)
    try:
        return dismiss_level_suggestion(user_id, l2)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except NoLevelSuggestion as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No level suggestion for this language",
        ) from exc
    except Exception as exc:
        logger.error("Could not dismiss level suggestion for %s %s: %s", user_id, l2, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not dismiss level suggestion",
        ) from exc
