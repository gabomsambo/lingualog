"""Read the learner's level-sized, curated writing prompts."""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request, status

from learning_policy import resolve_policy
from prompts import list_prompts

logger = logging.getLogger(__name__)
router = APIRouter(tags=["prompts"])


@router.get("/prompts")
async def get_prompts(
    request: Request,
    l2: Optional[str] = Query(None, pattern=r"^[a-z]{2}(-[A-Z]{2})?$"),
    level: Optional[str] = Query(None, pattern=r"^(A1|A2|B1|B2|C1|C2)$"),
    topic: Optional[str] = Query(None, min_length=1, max_length=60),
    exclude: List[str] = Query(default_factory=list, max_length=60),
):
    """Return prompt ideas, sentence frames and an optional L1 gloss for this learner."""
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not provided")
    try:
        policy = resolve_policy(user_id, l2)
        result = list_prompts(
            policy.l2,
            level or policy.proficiency,
            topic,
            exclude,
            meaning=policy.meaning,
            l1=policy.l1,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Could not load prompts for %s %s: %s", user_id, l2, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not load writing prompts",
        ) from exc
