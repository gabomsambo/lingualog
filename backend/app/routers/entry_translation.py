"""On-demand entry meaning translations."""

import logging

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.services.entry_translation_service import translate_entry_part

logger = logging.getLogger(__name__)

router = APIRouter(tags=["entry-translation"])


class EntryTranslateRequest(BaseModel):
    part: str = Field(
        ...,
        description="original | rewrite | note:<grammar_note_id>",
        examples=["original"],
    )
    target_lang: str = Field(
        ...,
        description="Learner native language ISO code (L1)",
        examples=["en"],
    )


@router.post("/entries/{entry_id}/translate")
async def translate_entry(
    entry_id: str,
    body: EntryTranslateRequest,
    request: Request,
):
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not provided",
        )

    try:
        result = await translate_entry_part(
            entry_id=entry_id,
            user_id=user_id,
            part=body.part,
            target_lang=body.target_lang,
        )
        return result
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.error("Translation failed for entry %s: %s", entry_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Translation failed",
        )
