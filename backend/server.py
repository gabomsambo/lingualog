"""
Main FastAPI application for the LinguaLog backend.

This module defines the FastAPI application and routes for handling journal entries
and generating AI feedback for language learning.
"""
import logging
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Add current directory to path to make imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from fastapi import FastAPI, HTTPException, Query, status, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from models import (
    AnalyzeEntryRequest,
    JournalEntryRequest,
    FeedbackResponse,
    LoginRequest,
    UserVocabularyItemCreate,
    UserVocabularyItemPatch,
    UserVocabularyItemResponse,
    LookupRequest,
    LookupResponse,
    Rubric,
    Suggestion,
    Word,
)
from app.models import JournalEntry, User, UserUpdate, UserSettings, UserSettingsUpdate, LanguageProfile # Corrected import for JournalEntry

# Import new language policy and prompt builder modules
from learning_policy import LearningPolicy, is_same_language, resolve_policy
from review_scheduler import MAX_RETENTION, MIN_RETENTION
from prompt_builder import build_messages, build_user_message, extract_snapshot_data
from database import (
    save_entry,
    fetch_entries,
    sign_in_with_magic_link,
    fetch_single_entry,
    delete_entry,
    update_entry_analysis,
    save_vocabulary_item,
    fetch_user_vocabulary,
    delete_vocabulary_item,
    fetch_vocabulary_item_by_term,
    fetch_vocabulary_item_by_id_and_user,
    update_vocabulary_item,
    count_word_encounters,
    fetch_lookup_cache,
    fetch_word_encounter,
    get_daily_new_word_usage,
    link_word_encounters,
    save_word_encounter,
    init_db_schema,
    fetch_language_profile,
    list_language_profiles,
    save_user_settings,
)

# Gemini tutor adapter
from ai.schemas import GeminiJournalFeedback, JournalFeedback
from ai.gemini import (
    generate_structured,
    mock_generate_structured,
    GeminiError,
    GEMINI_MODEL_FEEDBACK,
    AI_PROVIDER,
)
from ai.word_card import card_policy_snapshot, generate_word_card
from word_bank import clean_target_word_uses

from app.routers import books, entry_translation, level_suggestions, review, support_events, vocab, word_bank
from app.services import book_service, review_service, vocab_service, word_bank_service
from app.services.stats_service import get_user_stats_service
from app.schemas.stats_schemas import UserStatsResponse
from app.services.entry_translation_service import split_sentences

# Configure logger
# Ensure basicConfig is called to set up the root logger handler and level
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG) # Output to stdout, set level to DEBUG

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG) # Set our specific logger to DEBUG as well
logger.propagate = True # Ensure messages go to the root logger

# Test log to see if basicConfig is working on startup
logger.debug("Root logger configured, LinguaLog API logger set to DEBUG.")

def _parse_cors_origins() -> List[str]:
    origins = os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:3010")
    return [origin.strip() for origin in origins.split(",") if origin.strip()]


def _language_profiles_for_user(user_id: str) -> list:
    """Load per-language profiles. A failed read raises; it is never reported as no profiles."""
    profiles = []
    for row in list_language_profiles(user_id) or []:
        try:
            profiles.append(
                LanguageProfile(
                    l2=row["l2"],
                    immersion_level=row.get("immersion_level", 1),
                    proficiency=row.get("proficiency") or "A2",
                    active=row.get("active") is not False,
                    daily_new_words=row.get("daily_new_words"),
                    desired_retention=row.get("desired_retention"),
                )
            )
        except Exception as exc:
            logger.warning("Skipping invalid language profile %s: %s", row, exc)
    return profiles


def _validated_language_profile(profile: dict) -> dict:
    """Check one language profile row without writing it."""
    from learning_policy import PROFICIENCY_LEVELS

    l2 = profile.get("l2")
    if not l2 or not isinstance(l2, str):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Language profile needs an l2 code")
    immersion = profile.get("immersion_level", 1)
    if immersion is None or not (0 <= int(immersion) <= 3):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="immersion_level must be 0-3",
        )
    proficiency = profile.get("proficiency") or "A2"
    if proficiency not in PROFICIENCY_LEVELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"proficiency must be one of {', '.join(PROFICIENCY_LEVELS)}",
        )
    validated = {
        "l2": l2,
        "immersion_level": int(immersion),
        "proficiency": proficiency,
        "active": profile.get("active") is not False,
    }
    # Review settings are written only when the request carries them.
    daily_new_words = profile.get("daily_new_words")
    if daily_new_words is not None:
        if not 1 <= int(daily_new_words) <= 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="daily_new_words must be 1-100"
            )
        validated["daily_new_words"] = int(daily_new_words)
    desired_retention = profile.get("desired_retention")
    if desired_retention is not None:
        if not MIN_RETENTION <= float(desired_retention) <= MAX_RETENTION:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"desired_retention must be {MIN_RETENTION}-{MAX_RETENTION}",
            )
        validated["desired_retention"] = float(desired_retention)
    return validated


def _studied_languages(user_id: str, profile_rows: Optional[list] = None) -> dict:
    """l2 -> active for the saved profiles, with this request's rows applied on top."""
    studied: dict = {}
    for row in list_language_profiles(user_id) or []:
        if row.get("l2"):
            studied[row["l2"]] = row.get("active") is not False
    for row in profile_rows or []:
        studied[row["l2"]] = row["active"]
    return studied


def _detected_language(value: Optional[str]) -> Optional[str]:
    """The tutor's language report as an ISO 639-1 code, or None when it is unclear."""
    code = (value or "").strip().lower().replace("_", "-").split("-")[0]
    return code if re.fullmatch(r"[a-z]{2}", code) else None


def _apply_explanation_choice(update_data: dict) -> None:
    """Only a mode the learner picks overrides the level; ``level`` clears that choice."""
    from learning_policy import EXPLANATION_MODE_FOLLOW_LEVEL, EXPLANATION_MODE_TO_FLAG

    if "explanation_mode" not in update_data:
        return
    mode = update_data["explanation_mode"]
    if mode == EXPLANATION_MODE_FOLLOW_LEVEL:
        del update_data["explanation_mode"]
        update_data["explanation_mode_explicit"] = False
    elif mode in EXPLANATION_MODE_TO_FLAG:
        update_data["explanation_mode_explicit"] = True
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"explanation_mode must be one of {EXPLANATION_MODE_FOLLOW_LEVEL}, "
            f"{', '.join(EXPLANATION_MODE_TO_FLAG)}",
        )


def _validate_choice_fields(update_data: dict) -> None:
    """Reject strictness and formality values the database would refuse, before any write."""
    from learning_policy import FORMALITY_LEVELS, STRICTNESS_LEVELS

    for field, allowed in (("strictness", STRICTNESS_LEVELS), ("formality", FORMALITY_LEVELS)):
        if field in update_data and update_data[field] not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field} must be one of {', '.join(allowed)}",
            )


async def fetch_user_profile_settings(user_id: Optional[str]) -> Optional[dict]:
    """
    Fetch user profile settings for language policy resolution.
    
    Args:
        user_id: User ID to fetch settings for
        
    Returns:
        Dictionary of user settings or None if not found/authenticated
    """
    if not user_id:
        logger.info("No user_id provided, using default settings")
        return None
    
    try:
        from database import create_supabase_client
        supabase = create_supabase_client()
        
        # Get user settings from user_settings table
        response = supabase.table('user_settings').select('*').eq('user_id', user_id).execute()
        
        if response.data:
            settings_data = response.data[0]
            logger.info(f"Fetched user settings for user {user_id}")
            return settings_data
        else:
            logger.info(f"No settings found for user {user_id}, will use defaults")
            return None
            
    except Exception as e:
        logger.warning(f"Failed to fetch user settings for {user_id}: {str(e)}")
        return None


def _learner_note(suggestion) -> str:
    """Keep the legacy `note` field filled from the language-specific slots."""
    if suggestion.note and suggestion.note.strip():
        return suggestion.note
    parts = [part for part in (suggestion.note_l2, suggestion.note_l1) if part and part.strip()]
    return "\n".join(parts)


def _action_reason(action) -> str:
    """Resolve the learner-facing reason from language-specific slots."""
    if action.reason and action.reason.strip():
        return action.reason
    parts = [part for part in (action.reason_l2, action.reason_l1) if part and part.strip()]
    return "\n".join(parts)


def _validate_sentence_mapping(result: JournalFeedback, original_text: str) -> tuple[list[dict], list[dict], str]:
    """Validate model indexes against the exact sentences shown by the UI.

    Returns the persisted mapping, the action explanations (always present when the
    mapping is accepted), and the status string. ``invalid_no_explanation`` is a
    separate status from ``invalid`` so the UI can distinguish a mapping the model
    got structurally wrong from one it explained badly - the latter is the
    contract violation that drops the mapping but still surfaces a warning.
    """
    source_count = len(split_sentences(original_text))
    corrected_count = len(split_sentences(result.corrected))
    mapping = [item.model_dump() for item in result.sentence_mapping]
    source_indexes = [item["source_sentence"] for item in mapping]

    reason = None
    if source_indexes != list(range(source_count)):
        reason = f"source coverage {source_indexes} does not match 0..{source_count - 1}"
    else:
        target_indexes = [index for item in mapping for index in item["corrected_sentences"]]
        if any(index < 0 or index >= corrected_count for index in target_indexes):
            reason = f"corrected index out of range for {corrected_count} sentences"
        elif any(
            len(item["corrected_sentences"]) != len(set(item["corrected_sentences"]))
            for item in mapping
        ):
            reason = "corrected sentence indexes are duplicated within a source sentence"
        elif set(target_indexes) != set(range(corrected_count)):
            reason = f"corrected coverage {sorted(set(target_indexes))} does not match 0..{corrected_count - 1}"
        elif target_indexes != sorted(target_indexes):
            reason = "corrected sentence indexes are not monotonic across source sentences"

    if reason:
        logger.warning("Rejecting Gemini sentence mapping; rows will be shown unaligned: %s", reason)
        return [], [], "invalid"

    # A corrected sentence is owned by the first source that references it
    # (same rule the side-by-side UI uses), so any subsequent source that
    # only points at already-owned indexes is "merged into" that neighbour.
    owner: dict[int, int] = {}
    for item in mapping:
        for target_index in item["corrected_sentences"]:
            owner.setdefault(target_index, item["source_sentence"])

    required_indexes: set[int] = set()
    actions_by_index = {action.source_sentence: action for action in result.sentence_actions}

    actions: list[dict] = []
    for item in mapping:
        source_index = item["source_sentence"]
        corrected_indexes = item["corrected_sentences"]
        if not corrected_indexes:
            expected = "removed"
        elif all(owner.get(idx) != source_index for idx in corrected_indexes):
            expected = "merged"
        else:
            continue
        required_indexes.add(source_index)
        action = actions_by_index.get(source_index)
        if action is None:
            logger.warning(
                "Gemini %s source sentence %d without an explanation; dropping mapping",
                expected,
                source_index,
            )
            return [], [], "invalid_no_explanation"
        if action.action != expected:
            logger.warning(
                "Gemini action %r for source sentence %d does not match mapping kind %r; dropping mapping",
                action.action,
                source_index,
                expected,
            )
            return [], [], "invalid_no_explanation"
        if not _action_reason(action).strip():
            logger.warning(
                "Gemini gave an empty explanation for source sentence %d (%s); dropping mapping",
                source_index,
                action.action,
            )
            return [], [], "invalid_no_explanation"
        payload = action.model_dump()
        payload["reason"] = _action_reason(action)
        actions.append(payload)

    return mapping, actions, "valid"


def _build_feedback_response(
    result: JournalFeedback,
    original_text: str,
    targets: Optional[List[dict]] = None,
    language: str = "",
) -> FeedbackResponse:
    """Convert the Gemini structured output to the API response model.

    ``targets`` are the word-bank words the learner chose. Only the tutor's claims about them
    that the entry text backs up are kept.
    """
    suggestions = []
    for suggestion in result.grammar_suggestions:
        payload = suggestion.model_dump()
        payload["note"] = _learner_note(suggestion)
        suggestions.append(Suggestion(**payload))
    sentence_mapping, sentence_actions, sentence_mapping_status = _validate_sentence_mapping(
        result, original_text
    )
    return FeedbackResponse(
        corrected=result.corrected,
        rewritten=result.rewrite,
        score=result.score,
        tone=result.tone,
        translation="",
        explanation=result.explanation,
        rubric=Rubric(**result.rubric.model_dump()),
        grammar_suggestions=suggestions,
        new_words=[
            Word(**word.model_dump())
            for word in result.new_words
        ],
        is_mock=result.is_mock,
        intended_meaning=result.intended_meaning or None,
        ambiguities=[item.model_dump() for item in result.ambiguities] or None,
        rewrite_idioms=[item.model_dump() for item in result.rewrite_idioms] or None,
        sentence_mapping=sentence_mapping or None,
        sentence_mapping_status=sentence_mapping_status,
        sentence_actions=sentence_actions or None,
        detected_language=_detected_language(result.detected_language),
        target_word_uses=(
            clean_target_word_uses(result.target_word_uses, targets, original_text, language) if targets else None
        ),
    )


def _rubric_column(feedback_response: FeedbackResponse) -> Optional[dict]:
    """Scores plus the tutor fields that have no column of their own."""
    if feedback_response.rubric is None:
        return None
    payload = feedback_response.rubric.model_dump()
    if feedback_response.intended_meaning:
        payload["intended_meaning"] = feedback_response.intended_meaning
    if feedback_response.ambiguities:
        payload["ambiguities"] = feedback_response.ambiguities
    if feedback_response.rewrite_idioms:
        payload["rewrite_idioms"] = feedback_response.rewrite_idioms
    return payload


def _policy_for_request(user_id: str, profile_settings: Optional[dict], overrides: dict) -> LearningPolicy:
    """Resolve one policy. A missing language-profile table must not block feedback."""
    l2 = overrides.get("target_language") or overrides.get("language")
    if not l2 and profile_settings:
        l2 = profile_settings.get("default_target_lang")
    language_profile = None
    if user_id and l2:
        try:
            language_profile = fetch_language_profile(user_id, l2)
        except Exception as exc:
            logger.warning("Language profile lookup failed for %s/%s: %s", user_id, l2, exc)
            language_profile = None
    return resolve_policy(
        user_id,
        l2,
        overrides,
        settings=profile_settings,
        language_profile=language_profile,
    )


def _snapshot_columns(policy: LearningPolicy) -> dict:
    """Legacy snapshot columns plus the whole policy object."""
    snapshot = extract_snapshot_data(policy)
    snapshot["policy_snapshot"] = policy.to_dict()
    return snapshot


def _analysis_columns(feedback_response: FeedbackResponse) -> dict:
    """Status columns stored alongside a successful (or mock) analysis."""
    if feedback_response.is_mock:
        return {"analysis_status": "mock", "analysis_model": "mock", "analysis_error_code": None}
    return {"analysis_status": "ok", "analysis_model": GEMINI_MODEL_FEEDBACK, "analysis_error_code": None}


def _target_words_for_request(user_id: str, language: str, word_ids: List[str]) -> List[dict]:
    """The learner's own word-bank words behind these ids. A lookup failure must not block feedback."""
    if not word_ids:
        return []
    try:
        return word_bank_service.load_target_words(user_id, language, word_ids)
    except Exception as exc:
        logger.error("Could not load word-bank words for %s: %s", user_id, exc)
        return []


def _target_word_columns(targets: List[dict], challenge_ids: set) -> List[dict]:
    """What an entry remembers of the words it was written with, so a retry can use them."""
    return [
        {
            "word_id": target["word_id"],
            "lemma": target["lemma"],
            "term": target["term"],
            "challenge": target["word_id"] in challenge_ids,
        }
        for target in targets
    ]


def _record_target_word_uses(
    user_id: str,
    entry_id: str,
    entry_created_at: Optional[str],
    feedback_response: FeedbackResponse,
    challenge_ids: set,
    replace_word_ids: Optional[List[str]] = None,
) -> None:
    """Write the entry's checked uses into the notebook, then keep what they did on the entry.

    ``replace_word_ids`` are the entry's words on a re-analysis: whatever the entry recorded
    for them before is replaced, even for a word the tutor now says nothing usable about.
    The entry and its feedback are already saved, so a failure here is logged and never turns
    into a failed submission. Sample feedback from the offline provider proves nothing, so it
    is shown but never counted.
    """
    uses = feedback_response.target_word_uses or []
    if feedback_response.is_mock or not (uses or replace_word_ids):
        return
    try:
        outcomes = word_bank_service.record_uses(
            user_id, entry_id, uses, challenge_ids, entry_created_at, replace_word_ids=replace_word_ids or ()
        )
        merged = [{**use, **outcomes.get(use["word_id"], {})} for use in uses]
        update_entry_analysis(entry_id, user_id, {"target_word_uses": merged})
        feedback_response.target_word_uses = merged
    except Exception as exc:
        logger.error("Could not record word-bank uses for entry %s: %s", entry_id, exc)


async def _analyze_with_provider(
    text: str, effective: LearningPolicy, targets: Optional[List[dict]] = None
) -> JournalFeedback:
    """Run the journal tutor (Gemini or mock) using the resolved policy prompt."""
    target_terms = [target["lemma"] or target["term"] for target in targets or []]
    system_prompt, _user_payload = build_messages(text, effective, target_terms)
    user_message = build_user_message(text, effective, target_terms)

    if AI_PROVIDER == "mock":
        return await mock_generate_structured(
            system_prompt, user_message, JournalFeedback, entry_text=text, target_words=target_terms
        )
    result = await generate_structured(
        system_prompt, user_message, GeminiJournalFeedback, timeout=30.0
    )
    return JournalFeedback.model_validate({**result.model_dump(), "is_mock": False})


app = FastAPI(
    title="LinguaLog API",
    description="API for language learning journal with AI feedback",
    version="0.1.0"
)

# TODO: Tighten CORS origins once Vercel/Railway deployment domains are known
# Currently using permissive settings for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(entry_translation.router)
app.include_router(support_events.router)
app.include_router(level_suggestions.router)
app.include_router(review.router)
app.include_router(word_bank.router)
app.include_router(books.router)
app.include_router(vocab.router)


@app.post("/login", status_code=status.HTTP_200_OK)
async def login(login_request: LoginRequest):
    """
    Send a magic link to the user's email for passwordless authentication.
    
    Args:
        login_request: User's email
        
    Returns:
        Success message if the magic link was sent successfully
        
    Raises:
        HTTPException: If there's an error during authentication
    """
    try:
        result = sign_in_with_magic_link(login_request.email)
        return result
    except Exception as e:
        logger.error(f"Error during login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during login: {str(e)}"
        )


@app.post("/log-entry", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def create_log_entry(entry: JournalEntryRequest, request: Request):
    """
    Process a journal entry and generate AI feedback using language policy resolution.

    Args:
        entry: The journal entry request with text and optional language overrides
        request: The request object containing user info (if available)

    Returns:
        FeedbackResponse with grammar correction, rewriting, and other feedback dimensions

    Raises:
        HTTPException: If there's an error processing the request
    """
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not provided",
        )

    # Fetch user profile settings
    profile_settings = await fetch_user_profile_settings(user_id)

    # Build request overrides from entry fields
    request_overrides = {}
    if entry.target_language:
        request_overrides['target_language'] = entry.target_language
    if entry.language:
        request_overrides['language'] = entry.language
    if entry.ui_language:
        request_overrides['ui_language'] = entry.ui_language
    if entry.explanation_mode:
        request_overrides['explanation_mode'] = entry.explanation_mode
    if entry.strictness:
        request_overrides['strictness'] = entry.strictness
    if entry.formality:
        request_overrides['formality'] = entry.formality
    if entry.immersion_level is not None:
        request_overrides['immersion_level'] = entry.immersion_level

    # One policy object. Per-entry overrides beat the saved explanation mode.
    effective_settings = _policy_for_request(user_id, profile_settings, request_overrides)
    snapshot_data = _snapshot_columns(effective_settings)

    targets = _target_words_for_request(
        user_id, effective_settings.l2, [str(word_id) for word_id in entry.target_word_ids]
    )
    challenge_ids = {str(word_id) for word_id in entry.challenge_word_ids} & {t["word_id"] for t in targets}
    target_columns = (
        {"target_words": _target_word_columns(targets, challenge_ids)} if targets else {}
    )

    try:
        result = await _analyze_with_provider(entry.text, effective_settings, targets)
        feedback_response = _build_feedback_response(result, entry.text, targets, effective_settings.l2)
    except GeminiError as e:
        logger.error(f"AI feedback failed ({e.code}): {e.message}")
        # Keep the entry so the learner can retry later.
        failed_entry = {
            "user_id": user_id,
            "original_text": entry.text,
            "title": entry.title,
            "language": entry.language or effective_settings.l2,
            "analysis_status": "failed",
            "analysis_model": GEMINI_MODEL_FEEDBACK,
            "analysis_error_code": e.code,
            **target_columns,
            **snapshot_data,
        }
        entry_id = None
        try:
            entry_id = save_entry(failed_entry).get("id")
            logger.info(f"Entry saved without feedback: {entry_id}")
        except Exception as save_error:
            logger.error(f"Failed to persist entry after AI failure: {save_error}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": e.code,
                "entry_id": entry_id,
                "message": e.message,
            },
        ) from e

    # Save entry and feedback to Supabase with language snapshots
    entry_data = {
        "user_id": user_id,
        "original_text": entry.text,
        "title": entry.title,
        "language": entry.language or effective_settings.l2,
        "corrected": feedback_response.corrected,
        "rewrite": feedback_response.rewritten,
        "score": feedback_response.score,
        "tone": feedback_response.tone,
        "translation": feedback_response.translation,
        "explanation": feedback_response.explanation,
        "rubric": _rubric_column(feedback_response),
        "grammar_suggestions": [sugg.model_dump() for sugg in feedback_response.grammar_suggestions] if feedback_response.grammar_suggestions else [],
        "new_words": [word.model_dump() for word in feedback_response.new_words] if feedback_response.new_words else [],
        "sentence_mapping": feedback_response.sentence_mapping,
        "sentence_mapping_status": feedback_response.sentence_mapping_status,
        "sentence_actions": feedback_response.sentence_actions,
        "detected_language": feedback_response.detected_language,
        **_analysis_columns(feedback_response),
        **target_columns,
        **({"target_word_uses": feedback_response.target_word_uses or []} if targets else {}),
        **snapshot_data,
    }

    saved_entry = save_entry(entry_data)
    logger.info(f"Entry saved with ID: {saved_entry.get('id')} and language snapshots")

    feedback_response.id = saved_entry.get("id")
    feedback_response.entry_id = feedback_response.id
    _record_target_word_uses(
        user_id, feedback_response.id, saved_entry.get("created_at"), feedback_response, challenge_ids
    )
    return feedback_response


@app.get("/entries", status_code=status.HTTP_200_OK)
async def get_entries(request: Request, language: Optional[str] = None):
    """
    Retrieve journal entries for the authenticated user, optionally filtered by language.

    Args:
        request: The request object containing user info (if available)
        language: Optional language filter (e.g., 'es', 'fr', 'ja') to show only entries in that language

    Returns:
        List of journal entries with their feedback

    Raises:
        HTTPException: If there's an error retrieving entries
    """
    try:
        user_id = request.headers.get("X-User-ID")
        if not user_id:
            # If no X-User-ID, it could be an unauthenticated request or error.
            # For now, let's return an empty list or an error.
            # Depending on desired behavior, you might allow fetching all if admin, etc.
            logger.warning("Attempted to fetch entries without X-User-ID header.")
            # Option 1: Return empty list
            return []
            # Option 2: Raise an error
            # raise HTTPException(
            #     status_code=status.HTTP_401_UNAUTHORIZED,
            #     detail="User ID not provided"
            # )

        entries = fetch_entries(user_id=user_id, language=language)
        return entries
    except Exception as e:
        logger.error(f"Error fetching entries: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching entries: {str(e)}"
        )


@app.get("/entries/{entry_id}", response_model=JournalEntry)
async def get_single_entry(entry_id: str, request: Request):
    print("!!!!!!!!!! (PRINT) ENTERING get_single_entry FUNCTION !!!!!!!!!!", file=sys.stderr) # Prominent entry print
    logger.info("!!!!!!!!!! (LOGGER.INFO) ENTERING get_single_entry FUNCTION !!!!!!!!!!") # Prominent entry log
    
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        print("!!!!!!!!!! (PRINT) User ID not provided in get_single_entry !!!!!!!!!!", file=sys.stderr)
        logger.error("User ID not provided in get_single_entry")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not provided")
    
    entry_data_dict = None
    try:
        print(f"!!!!!!!!!! (PRINT) Fetching entry: {entry_id} for user: {user_id} !!!!!!!!!!", file=sys.stderr)
        logger.info(f"Fetching entry data for entry_id: {entry_id} by user_id: {user_id}")
        entry_data_dict = fetch_single_entry(entry_id, user_id)
        
        if not entry_data_dict:
            print(f"!!!!!!!!!! (PRINT) Entry not found in DB: id {entry_id} for user {user_id} !!!!!!!!!!", file=sys.stderr)
            logger.warning(f"Entry not found in DB: id {entry_id} for user {user_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
        
        print("!!!!!!!!!! (PRINT) REACHED DETAILED LOGGING BLOCK !!!!!!!!!!", file=sys.stderr)
        logger.info("!!!!!!!!!! (LOGGER.INFO) REACHED DETAILED LOGGING BLOCK !!!!!!!!!!")
        
        logger.debug(f"Raw entry_data_dict from DB: {entry_data_dict}") # Changed to debug for potentially large output

        if 'ai_feedback' in entry_data_dict and entry_data_dict['ai_feedback'] is not None:
            ai_feedback_data = entry_data_dict['ai_feedback']
            logger.info(f"ai_feedback type: {type(ai_feedback_data)}")
            logger.info(f"ai_feedback raw content: {ai_feedback_data}")
            if isinstance(ai_feedback_data, dict):
                logger.info(f"ai_feedback keys: {list(ai_feedback_data.keys())}")
                for key, value in ai_feedback_data.items():
                    logger.info(f"ai_feedback field - {key}: {value} (type: {type(value)})")
            elif isinstance(ai_feedback_data, str):
                logger.warning(f"ai_feedback is a STRING: '{ai_feedback_data}'. Expected a dict/JSON object.")
            else:
                logger.warning(f"ai_feedback is of unexpected type: {type(ai_feedback_data)}. Content: {ai_feedback_data}")
        else:
            logger.info(f"No 'ai_feedback' field in entry_data_dict or it is None. Keys: {list(entry_data_dict.keys()) if isinstance(entry_data_dict, dict) else 'entry_data_dict is not a dict'}")
        
        print("!!!!!!!!!! (PRINT) Attempting Pydantic model creation... !!!!!!!!!!", file=sys.stderr)
        logger.info("Attempting Pydantic model creation for JournalEntry...")
        journal_entry = JournalEntry(**entry_data_dict)
        print("!!!!!!!!!! (PRINT) Pydantic model JournalEntry CREATED. !!!!!!!!!!", file=sys.stderr)
        logger.info("Pydantic model JournalEntry created successfully.")
        return journal_entry
        
    except ValidationError as e:
        print(f"!!!!!!!!!! (PRINT) Pydantic VALIDATION ERROR for entry {entry_id} !!!!!!!!!!", file=sys.stderr)
        logger.error(f"Pydantic validation error for entry {entry_id}: {e.errors()}") # Log detailed errors
        logger.error(f"Raw entry data causing validation error: {entry_data_dict}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Data validation error processing entry. Details: {e.errors()}" # Send errors to client
        )
    except HTTPException:
        print("!!!!!!!!!! (PRINT) Re-raising HTTPException !!!!!!!!!!", file=sys.stderr)
        raise
    except Exception as e:
        print(f"!!!!!!!!!! (PRINT) UNEXPECTED ERROR in get_single_entry for {entry_id}: {type(e).__name__} - {e} !!!!!!!!!!", file=sys.stderr)
        logger.error(f"Unexpected error in get_single_entry for entry {entry_id}: {type(e).__name__} - {e}")
        raw_data_info = entry_data_dict if entry_data_dict is not None else "Raw data not fetched or available."
        logger.error(f"Raw entry data at point of unexpected error: {raw_data_info}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error while fetching entry: {type(e).__name__} - {e}"
        )


@app.post("/entries/{entry_id}/analyze", response_model=FeedbackResponse)
async def analyze_existing_entry(
    entry_id: str,
    request: Request,
    body: Optional[AnalyzeEntryRequest] = None,
):
    """
    Retry AI analysis for an existing journal entry.

    The entry must belong to the authenticated user. Without a body the entry
    keeps its language and stored policy snapshot. With ``target_language`` set
    to another studied language (the "did you mean…?" switch), the entry moves to
    that language and is analysed with the learner's current policy for it.
    """
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not provided",
        )

    entry = fetch_single_entry(entry_id, user_id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entry not found",
        )

    profile_settings = await fetch_user_profile_settings(user_id)
    current_l2 = entry.get("target_language") or entry.get("language")
    switch_to = body.target_language if body and body.target_language else None
    if switch_to == current_l2:
        switch_to = None
    stored_policy = entry.get("policy_snapshot")
    if switch_to:
        try:
            studied = _studied_languages(user_id)
        except Exception as exc:
            logger.error(f"Could not list language profiles for {user_id}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "profiles_unavailable",
                    "message": "Your languages could not be loaded. Try again in a moment.",
                },
            )
        if not studied.get(switch_to):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "language_not_studied",
                    "message": "Add this language to the languages you are learning in Settings first.",
                },
            )
        effective_settings = _policy_for_request(user_id, profile_settings, {"target_language": switch_to})
    elif isinstance(stored_policy, dict) and stored_policy.get("l2"):
        # History stays on the policy that was resolved when the entry was written.
        effective_settings = LearningPolicy.from_dict(stored_policy)
    else:
        overrides = {
            "target_language": entry.get("target_language") or entry.get("language"),
        }
        effective_settings = _policy_for_request(user_id, profile_settings, overrides)

    # The words the entry was written with, unless it is moving to a language they do not belong to.
    stored_targets = entry.get("target_words") or []
    targets = [] if switch_to else _target_words_for_request(
        user_id, effective_settings.l2, [item["word_id"] for item in stored_targets if item.get("word_id")]
    )
    challenge_ids = {
        item["word_id"] for item in stored_targets if item.get("challenge") and item.get("word_id")
    } & {t["word_id"] for t in targets}

    try:
        result = await _analyze_with_provider(entry["content"], effective_settings, targets)
    except GeminiError as e:
        logger.error(f"Retry analysis failed for {entry_id} ({e.code}): {e.message}")
        if entry.get("analysis_status") not in ("ok", "mock", "legacy"):
            try:
                update_entry_analysis(
                    entry_id,
                    user_id,
                    {"analysis_status": "failed", "analysis_error_code": e.code},
                )
            except Exception as update_error:
                logger.error(f"Failed to record retry failure for {entry_id}: {update_error}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": e.code,
                "entry_id": entry_id,
                "message": e.message,
            },
        ) from e

    feedback_response = _build_feedback_response(result, entry["content"], targets, effective_settings.l2)
    update_data = {
        "corrected": feedback_response.corrected,
        "rewrite": feedback_response.rewritten,
        "score": feedback_response.score,
        "tone": feedback_response.tone,
        "translation": feedback_response.translation,
        "explanation": feedback_response.explanation,
        "rubric": _rubric_column(feedback_response),
        "grammar_suggestions": [sugg.model_dump() for sugg in feedback_response.grammar_suggestions] if feedback_response.grammar_suggestions else [],
        "new_words": [word.model_dump() for word in feedback_response.new_words] if feedback_response.new_words else [],
        "sentence_mapping": feedback_response.sentence_mapping,
        "sentence_mapping_status": feedback_response.sentence_mapping_status,
        "sentence_actions": feedback_response.sentence_actions,
        "detected_language": feedback_response.detected_language,
        **_analysis_columns(feedback_response),
        **_snapshot_columns(effective_settings),
    }
    if stored_targets:
        update_data["target_words"] = _target_word_columns(targets, challenge_ids)
        update_data["target_word_uses"] = feedback_response.target_word_uses or []
    if switch_to:
        # Translations of the old rewrite and notes no longer match the new analysis.
        update_data.update(
            {
                "language": switch_to,
                "meaning_translations_cache": {},
                "detected_language_kept": False,
            }
        )
    update_entry_analysis(entry_id, user_id, update_data)

    feedback_response.id = entry_id
    if stored_targets and not targets:
        try:
            word_bank_service.clear_entry_uses(user_id, entry_id)
        except Exception as exc:
            logger.error("Could not clear word-bank uses for entry %s: %s", entry_id, exc)
    _record_target_word_uses(
        user_id, entry_id, entry.get("created_at"), feedback_response, challenge_ids,
        replace_word_ids=[target["word_id"] for target in targets],
    )
    return feedback_response


@app.post("/entries/{entry_id}/keep-language", status_code=status.HTTP_204_NO_CONTENT)
async def keep_entry_language(entry_id: str, request: Request):
    """The learner answered "keep" to the did-you-mean prompt; stop asking for this entry."""
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not provided")
    if not fetch_single_entry(entry_id, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    update_entry_analysis(entry_id, user_id, {"detected_language_kept": True})


@app.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry_route(entry_id: str, request: Request):
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not provided")
    
    try:
        success = delete_entry(entry_id=entry_id, user_id=user_id)
        if not success:
            # This case might indicate the entry didn't exist or didn't belong to the user
            # delete_entry should ideally raise a specific exception or return a more detailed status
            logger.warning(f"Attempt to delete entry {entry_id} for user {user_id} was not successful (entry not found or no permission).")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found or user does not have permission to delete.")
        logger.info(f"Entry {entry_id} deleted successfully for user {user_id}.")
        try:
            word_bank_service.clear_entry_uses(user_id, entry_id)
        except Exception as exc:
            logger.error(f"Could not clear word-bank uses of deleted entry {entry_id}: {exc}")
        return # FastAPI handles the 204 No Content response
    except HTTPException: # Re-raise HTTPExceptions directly
        raise
    except Exception as e:
        logger.error(f"Error deleting entry {entry_id} for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting entry: {str(e)}"
        )


# --- Vocabulary Endpoints ---

@app.post("/lookup", response_model=LookupResponse)
async def lookup_word_route(payload: LookupRequest, request: Request):
    """Build or reuse a context-aware card and always record the encounter."""
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not provided")
    text = payload.text.strip()
    sentence = (payload.sentence or text).strip()
    policy = resolve_policy(user_id, payload.language)
    snapshot = card_policy_snapshot(policy)
    if payload.source == "entry" and payload.source_id:
        if not fetch_single_entry(str(payload.source_id), user_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    reading_session = None
    if payload.source == "book_session":
        reading_session = (
            book_service.fetch_session_for_user(user_id, str(payload.source_id)) if payload.source_id else None
        )
        if not reading_session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reading session not found")
        if reading_session.get("ended_at"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "session_ended", "message": "This reading session has ended"},
            )
        try:
            book_language = book_service.get_book(user_id, reading_session["book_id"])["language"]
        except book_service.BookNotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found") from exc
        if book_language != payload.language:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Lookup language does not match the book"
            )
    cached = fetch_lookup_cache(
        user_id, payload.language, text, sentence, snapshot.get("vocab_def")
    )
    card_data: Optional[Dict[str, Any]] = None
    card_status = "failed"
    lemma, sense = text, ""
    if cached:
        card_data = cached.get("card")
        lemma = cached.get("lemma") or text
        sense = cached.get("sense") or ""
        card_status = "ok"
    else:
        try:
            card = await generate_word_card(text, sentence, policy)
            card_data = card.model_dump(by_alias=True)
            lemma, sense, card_status = card.lemma, card.sense_in_context, "ok"
        except GeminiError as exc:
            logger.error("Lookup card failed (%s): %s", exc.code, exc.message)

    saved = fetch_vocabulary_item_by_term(user_id, lemma, payload.language)
    encounter_data = {
        "word_id": saved.get("id") if saved else None,
        "language": payload.language,
        "lemma": lemma,
        "sense": sense or None,
        "surface": text,
        "sentence": sentence,
        "kind": "read" if reading_session else payload.kind,
        "source_type": payload.source,
        "source_id": str(payload.source_id) if payload.source_id else None,
        "card": card_data,
        "card_policy": snapshot if card_data else None,
        "card_status": card_status,
    }
    if reading_session:
        encounter = book_service.record_book_lookup(
            user_id, reading_session, text, payload.page, encounter_data
        )
    else:
        encounter = save_word_encounter(encounter_data, user_id)
    return {
        "encounter_id": encounter["id"],
        "text": text,
        "language": payload.language,
        "lemma": lemma,
        "sense": sense,
        "card": card_data,
        "card_status": card_status,
        "card_policy": snapshot,
        "seen_count": count_word_encounters(user_id, payload.language, lemma),
        "saved_item": saved,
    }

@app.post("/vocabulary", response_model=UserVocabularyItemResponse, status_code=status.HTTP_201_CREATED)
async def add_vocabulary_item_route(item: UserVocabularyItemCreate, request: Request):
    """Save a word and build its policy-aware card with one structured call."""
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not provided"
        )
    try:
        existing = fetch_vocabulary_item_by_term(user_id, item.term, item.language)
        if existing and existing.get("card_status") == "ok" and existing.get("card"):
            return existing

        item_data = {**item.model_dump(exclude={"encounter_id"}), "status": "new"}
        policy = resolve_policy(user_id, item.language)
        card_fields: Dict[str, Any] = {}
        encounter = fetch_word_encounter(item.encounter_id, user_id) if item.encounter_id else None
        if item.encounter_id and not encounter:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lookup encounter not found")
        snapshot = card_policy_snapshot(policy) if encounter else {}
        if encounter and encounter.get("language") != item.language:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Lookup encounter language mismatch"
            )
        if (
            encounter
            and encounter.get("card_status") == "ok"
            and encounter.get("card")
            and (encounter.get("card_policy") or {}).get("vocab_def") == snapshot.get("vocab_def")
        ):
            cached_card = encounter["card"]
            if encounter["lemma"] != item.term:
                lemma_row = fetch_vocabulary_item_by_term(user_id, encounter["lemma"], item.language)
                if lemma_row:
                    if lemma_row.get("card_status") == "ok" and lemma_row.get("card"):
                        return lemma_row
                    existing = lemma_row
            card_fields = {
                "term": encounter["lemma"],
                "lemma": encounter["lemma"],
                "sense": encounter.get("sense"),
                "part_of_speech": cached_card.get("part_of_speech"),
                "definition": encounter.get("sense"),
                "card": cached_card,
                "card_status": "ok",
                "card_policy": snapshot,
            }
            item_data["example_sentence"] = encounter.get("sentence") or item.example_sentence
        else:
            try:
                card = await generate_word_card(item.term, item.example_sentence or "", policy)
                card_fields = {
                    "term": card.lemma,
                    "lemma": card.lemma,
                    "sense": card.sense_in_context,
                    "part_of_speech": item.part_of_speech or card.part_of_speech,
                    "definition": item.definition or card.sense_in_context,
                    "card": card.model_dump(by_alias=True),
                    "card_status": "ok",
                    "card_policy": card_policy_snapshot(policy),
                }
                if card.lemma != item.term:
                    lemma_row = fetch_vocabulary_item_by_term(user_id, card.lemma, item.language)
                    if lemma_row:
                        existing = lemma_row
                        if lemma_row.get("card_status") == "ok" and lemma_row.get("card"):
                            return lemma_row
            except GeminiError as exc:
                logger.error("Vocabulary card failed (%s): %s", exc.code, exc.message)
                card_fields = {"card_status": "failed"}

        if existing:
            if existing.get("part_of_speech"):
                card_fields.pop("part_of_speech", None)
            if existing.get("definition"):
                card_fields.pop("definition", None)
            saved_item = update_vocabulary_item(existing["id"], user_id, card_fields)
        else:
            item_data.update(card_fields)
            item_data.setdefault("lemma", item.term)
            saved_item = save_vocabulary_item(item_data=item_data, user_id=user_id)
        if not saved_item:
            raise RuntimeError("Vocabulary item was not saved")
        if encounter:
            link_word_encounters(
                user_id, item.language, saved_item.get("lemma") or item.term, saved_item["id"]
            )
        if saved_item.get("status") == "learning":
            review_service.sync_word_cards(user_id, saved_item)
        return saved_item
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding vocabulary item for user {user_id}: {str(e)}")
        if "unique constraint" in str(e):
             raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Vocabulary item '{item.term}' in {item.language} already exists for this user."
            ) # This might be redundant if upsert handles it, but good for clarity.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save vocabulary item: {str(e)}"
        )


@app.post("/vocabulary/{item_id}/card", response_model=UserVocabularyItemResponse)
async def retry_vocabulary_card_route(item_id: str, request: Request):
    """Retry a failed card without replacing a card that is already good."""
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not provided")
    item = fetch_vocabulary_item_by_id_and_user(item_id, user_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vocabulary item not found")
    if item.get("card_status") == "ok" and item.get("card"):
        return item

    policy = resolve_policy(user_id, item["language"])
    try:
        card = await generate_word_card(
            item["term"],
            item.get("example_sentence") or "",
            policy,
        )
    except GeminiError as exc:
        update_vocabulary_item(item_id, user_id, {"card_status": "failed"})
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": exc.code, "message": exc.message},
        ) from exc

    updated = update_vocabulary_item(
        item_id,
        user_id,
        {
            "term": card.lemma,
            "lemma": card.lemma,
            "sense": card.sense_in_context,
            "part_of_speech": item.get("part_of_speech") or card.part_of_speech,
            "definition": item.get("definition") or card.sense_in_context,
            "card": card.model_dump(by_alias=True),
            "card_status": "ok",
            "card_policy": card_policy_snapshot(policy),
        },
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vocabulary item not found")
    return updated

@app.get("/vocabulary", status_code=status.HTTP_200_OK)
async def get_user_vocabulary_route(
    request: Request,
    language: Optional[str] = None,
    list_id: Optional[str] = Query(None, alias="list"),
    tag: Optional[str] = None,
    entry_id: Optional[str] = None,
    book_id: Optional[str] = None,
    item_status: Optional[str] = Query(None, alias="status"),
    source: Optional[str] = None,
):
    """
    Fetch vocabulary items for the authenticated user, filtered by language, list or tag.
    """
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not provided"
        )
    try:
        selector = vocab_service.selector_from(list_id, tag, entry_id, book_id, item_status, source)
        if selector:
            items = vocab_service.fetch_items(user_id, language, selector)
        else:
            items = fetch_user_vocabulary(user_id=user_id, language=language)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as e:
        logger.error(f"Error fetching vocabulary for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not fetch vocabulary: {str(e)}",
        ) from e
    try:
        return review_service.attach_review_state(user_id, items)
    except Exception as e:
        # The notebook is still useful without review progress.
        logger.error(f"Could not attach review state for user {user_id}: {str(e)}")
        return items


@app.patch("/vocabulary/{item_id}", response_model=UserVocabularyItemResponse)
async def patch_vocabulary_item_route(
    item_id: str,
    patch: UserVocabularyItemPatch,
    request: Request,
):
    """Update a learner's note, tags, or notebook state with an ownership filter."""
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not provided")
    changes = patch.model_dump(exclude_unset=True)
    if changes.get("tags", []) is None or changes.get("status", "new") is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="tags and status cannot be null",
        )
    if "tags" in changes:
        changes["tags"] = list(dict.fromkeys(tag.strip() for tag in changes["tags"] if tag.strip()))
    if changes.get("status") == "learning":
        current = fetch_vocabulary_item_by_id_and_user(item_id, user_id)
        if not current:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vocabulary item not found")
    else:
        current = None
    if current and current.get("status") != "learning":
        used, cap = get_daily_new_word_usage(user_id, current["language"])
        if used >= cap:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "daily_new_words_cap", "used": used, "cap": cap},
            )
        changes["study_started_at"] = datetime.now(timezone.utc).isoformat()
    updated = update_vocabulary_item(item_id, user_id, changes)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vocabulary item with id {item_id} not found or not owned by user.",
        )
    if "status" in changes:
        try:
            review_service.sync_word_cards(user_id, updated)
        except Exception as e:
            logger.error(f"Card sync failed for vocabulary item {item_id}: {str(e)}")
    return updated

@app.delete("/vocabulary/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vocabulary_item_route(item_id: str, request: Request):
    """
    Delete a specific vocabulary item for the authenticated user.
    """
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not provided"
        )
    
    try:
        success = delete_vocabulary_item(item_id=item_id, user_id=user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vocabulary item with id {item_id} not found or not owned by user."
            )
        return # Returns 204 No Content by default
    except HTTPException: # Re-raise HTTPExceptions directly
        raise
    except Exception as e:
        logger.error(f"Error deleting vocabulary item {item_id} for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not delete vocabulary item: {str(e)}"
        )


# TODO: Add user authentication middleware/dependencies

@app.post("/log-entry-atomic", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def create_log_entry_atomic(entry: JournalEntryRequest, request: Request):
    """
    Legacy alias of ``/log-entry``.

    Shares the Gemini journal-feedback path, including honest 503 failures,
    ``analysis_status`` tracking, and the ``is_mock`` flag.
    """
    return await create_log_entry(entry, request)


# User Profile and Stats Endpoints

@app.get("/user/profile", response_model=User, status_code=status.HTTP_200_OK)
async def get_user_profile(request: Request):
    """
    Get the current user's profile information.
    """
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="User ID not provided"
        )
    
    try:
        # Get user from Supabase auth users table
        from database import create_supabase_client
        supabase = create_supabase_client()
        
        # Get user profile from auth.users
        response = supabase.auth.admin.get_user_by_id(user_id)
        if not response.user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user = response.user
        
        # Get additional profile data from users table if it exists
        profile_response = supabase.table('users').select('*').eq('id', user_id).execute()
        profile_data = profile_response.data[0] if profile_response.data else {}
        
        return User(
            id=uuid.UUID(user.id),
            email=user.email or "",
            full_name=profile_data.get('username') or user.user_metadata.get('full_name'),
            is_active=True,
            is_superuser=False,
            created_at=user.created_at,
            updated_at=user.updated_at or user.created_at
        )
        
    except Exception as e:
        logger.error(f"Error fetching user profile for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not fetch user profile: {str(e)}"
        )

@app.put("/user/profile", response_model=User, status_code=status.HTTP_200_OK)
async def update_user_profile(user_update: UserUpdate, request: Request):
    """
    Update the current user's profile information.
    """
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="User ID not provided"
        )
    
    try:
        from database import create_supabase_client
        supabase = create_supabase_client()
        
        # Update user metadata in auth.users if needed
        update_data = {}
        if user_update.email:
            update_data['email'] = user_update.email
        if user_update.full_name:
            update_data['user_metadata'] = {'full_name': user_update.full_name}
        
        if update_data:
            supabase.auth.admin.update_user_by_id(user_id, update_data)
        
        # Update username in users table (only username, never email)
        if user_update.full_name:
            # Use UPDATE instead of UPSERT to avoid setting email to null
            update_response = supabase.table('users').update({
                'username': user_update.full_name
            }).eq('id', user_id).execute()
            
            # If no rows were updated, the user doesn't exist in users table
            # Create the record with email from auth.users
            if not update_response.data:
                auth_user = supabase.auth.admin.get_user_by_id(user_id)
                if auth_user.user and auth_user.user.email:
                    supabase.table('users').insert({
                        'id': user_id,
                        'email': auth_user.user.email,
                        'username': user_update.full_name
                    }).execute()
        
        # Fetch and return updated user profile
        return await get_user_profile(request)
        
    except Exception as e:
        logger.error(f"Error updating user profile for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not update user profile: {str(e)}"
        )

@app.get("/user/stats", response_model=UserStatsResponse, status_code=status.HTTP_200_OK)
async def get_user_stats(request: Request):
    """
    Get comprehensive statistics for the current user.
    """
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="User ID not provided"
        )
    
    try:
        from database import create_supabase_client
        supabase = create_supabase_client()
        
        # Use the existing stats service
        stats = await get_user_stats_service(supabase, user_id)
        return stats
        
    except Exception as e:
        logger.error(f"Error fetching user stats for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not fetch user stats: {str(e)}"
        )

@app.get("/user/policy", status_code=status.HTTP_200_OK)
async def get_user_policy(request: Request, l2: Optional[str] = None):
    """
    The learner's current LearningPolicy for one target language.

    Entries written before policy snapshots existed render with this policy.
    """
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not provided",
        )
    profile_settings = await fetch_user_profile_settings(user_id)
    overrides = {"target_language": l2} if l2 else {}
    return _policy_for_request(user_id, profile_settings, overrides).to_dict()


# User Settings Endpoints

@app.get("/user/settings", response_model=UserSettings, status_code=status.HTTP_200_OK)
async def get_user_settings(request: Request):
    """
    Get the current user's settings.
    """
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="User ID not provided"
        )
    
    try:
        from database import create_supabase_client
        supabase = create_supabase_client()
        
        # Get user settings from user_settings table
        response = supabase.table('user_settings').select('*').eq('user_id', user_id).execute()
        
        if not response.data:
            # Create default settings for new user
            default_settings = {
                'user_id': user_id,
                'native_language': 'en',
                'target_languages': ['es'],
                'email_notifications': True,
                'push_notifications': True,
                'daily_reminders': True,
                'weekly_progress': True,
                'reminder_time': '09:00',
                'theme': 'system',
                'app_language': 'en',
                'sound_effects': True,
                'animations': True,
                'difficulty_level': 'intermediate',
                'daily_goal': 100,
                'weekly_goal': 700,
                'auto_save': True,
                'show_hints': True,
                'public_profile': False,
                'share_progress': False,
                'analytics_opt_in': True
            }
            
            create_response = supabase.table('user_settings').insert(default_settings).execute()
            if create_response.data:
                settings_data = create_response.data[0]
            else:
                raise Exception("Failed to create default settings")
        else:
            settings_data = response.data[0]
        
        return UserSettings(
            id=uuid.UUID(settings_data['id']),
            user_id=uuid.UUID(settings_data['user_id']),
            native_language=settings_data['native_language'],
            target_languages=settings_data['target_languages'],
            email_notifications=settings_data['email_notifications'],
            push_notifications=settings_data['push_notifications'],
            daily_reminders=settings_data['daily_reminders'],
            weekly_progress=settings_data['weekly_progress'],
            reminder_time=settings_data['reminder_time'],
            theme=settings_data['theme'],
            app_language=settings_data['app_language'],
            sound_effects=settings_data['sound_effects'],
            animations=settings_data['animations'],
            difficulty_level=settings_data['difficulty_level'],
            daily_goal=settings_data['daily_goal'],
            weekly_goal=settings_data['weekly_goal'],
            auto_save=settings_data['auto_save'],
            show_hints=settings_data['show_hints'],
            public_profile=settings_data['public_profile'],
            share_progress=settings_data['share_progress'],
            analytics_opt_in=settings_data['analytics_opt_in'],
            created_at=settings_data['created_at'],
            updated_at=settings_data['updated_at'],
            # New multilingual fields from migration
            interface_lang=settings_data.get('interface_lang', 'en'),
            native_lang=settings_data.get('native_lang', 'en'),
            default_target_lang=settings_data.get('default_target_lang'),
            explanation_mode=settings_data.get('explanation_mode', 'bilingual'),
            explanation_mode_explicit=bool(settings_data.get('explanation_mode_explicit', False)),
            immersion_level=settings_data.get('immersion_level', 1),
            strictness=settings_data.get('strictness', 'medium'),
            formality=settings_data.get('formality', 'neutral'),
            language_profiles=_language_profiles_for_user(user_id),
        )
        
    except Exception as e:
        logger.error(f"Error fetching user settings for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not fetch user settings: {str(e)}"
        )

@app.put("/user/settings", response_model=UserSettings, status_code=status.HTTP_200_OK)
async def update_user_settings(settings_update: UserSettingsUpdate, request: Request):
    """
    Update the current user's settings.
    """
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="User ID not provided"
        )
    
    try:
        from database import create_supabase_client
        supabase = create_supabase_client()
        
        # Prepare update data, only including non-None fields.
        # language_profiles is its own table; it is not a user_settings column.
        update_data = {}
        for field, value in settings_update.model_dump(exclude_none=True).items():
            update_data[field] = value

        profiles = update_data.pop("language_profiles", None)
        _apply_explanation_choice(update_data)
        _validate_choice_fields(update_data)
        profile_rows = (
            [_validated_language_profile(profile) for profile in profiles] if profiles is not None else None
        )

        if not update_data and profile_rows is None:
            # If no fields to update, just return current settings
            return await get_user_settings(request)

        existing = supabase.table('user_settings').select(
            'default_target_lang,immersion_level'
        ).eq('user_id', user_id).limit(1).execute()
        existing_row = existing.data[0] if existing.data else {}
        default_l2 = update_data.get('default_target_lang') or existing_row.get('default_target_lang') or 'es'

        if profile_rows is not None or 'default_target_lang' in update_data:
            studied = _studied_languages(user_id, profile_rows)
            if studied.get(default_l2) is False:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="The default language must be one you are learning; pick another default first",
                )
            if default_l2 not in studied:
                # Choosing a default adds it to the studied list.
                profile_rows = (profile_rows or []) + [
                    _validated_language_profile(
                        {"l2": default_l2, "immersion_level": existing_row.get("immersion_level", 1)}
                    )
                ]

        if profile_rows is not None:
            for row in profile_rows:
                if row["l2"] == default_l2:
                    update_data["immersion_level"] = row["immersion_level"]
        elif update_data.get("immersion_level") is not None:
            # The legacy account-wide slider still updates the default language.
            current = fetch_language_profile(user_id, default_l2)
            proficiency = (current or {}).get("proficiency") or "A2"
            profile_rows = [
                _validated_language_profile(
                    {
                        "l2": default_l2,
                        "immersion_level": update_data["immersion_level"],
                        "proficiency": proficiency,
                    }
                )
            ]

        save_user_settings(user_id, update_data, profile_rows)

        # Return updated settings
        return await get_user_settings(request)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user settings for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not update user settings: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=3011, reload=True)
