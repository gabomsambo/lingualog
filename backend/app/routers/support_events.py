"""Support event telemetry (reveal / rescue taps)."""

import logging
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from database import create_supabase_client, fetch_single_entry
from prompts import get_prompt

logger = logging.getLogger(__name__)

router = APIRouter(tags=["support-events"])

SUPPORT_EVENTS_TABLE = "support_events"


class SupportEventCreate(BaseModel):
    kind: Literal[
        "reveal_meaning",
        "rescue_note",
        "reveal_rewrite_gloss",
        "reveal_example",
        "reveal_gloss",
        "prompt_selected",
    ]
    entry_id: Optional[str] = Field(None, description="Journal entry id when applicable")
    immersion_level: Optional[int] = Field(None, ge=0, le=3)
    l2: Optional[str] = Field(None, description="Target language code for the entry")
    prompt_id: Optional[str] = Field(None, min_length=1, max_length=100)


@router.post("/events", status_code=status.HTTP_201_CREATED)
async def create_support_event(body: SupportEventCreate, request: Request):
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not provided",
        )

    entry_id = body.entry_id
    if body.kind == "prompt_selected":
        if not body.l2 or not body.prompt_id or not get_prompt(body.l2, body.prompt_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A valid prompt_id and l2 are required for prompt usage events",
            )
    if entry_id:
        try:
            if not fetch_single_entry(entry_id, user_id):
                entry_id = None
        except Exception as exc:
            logger.warning("Could not verify entry %s for support event: %s", entry_id, exc)
            entry_id = None

    row = {
        "user_id": user_id,
        "entry_id": entry_id,
        "immersion_level": body.immersion_level,
        "l2": body.l2,
        "kind": body.kind,
        "prompt_id": body.prompt_id,
    }
    try:
        supabase = create_supabase_client()
        response = supabase.table(SUPPORT_EVENTS_TABLE).insert(row).execute()
        if response.data:
            return {"id": response.data[0].get("id"), "ok": True}
        return {"ok": True}
    except Exception as exc:
        logger.error("Failed to record support event: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record event",
        )
