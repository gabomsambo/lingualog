"""
Supabase integration for LinguaLog.

This module handles all interactions with Supabase for database operations
and user authentication.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union
import uuid # Added import for uuid

# Import Supabase client
from supabase import create_client, Client

# Import environment variables
from config import SUPABASE_URL, SUPABASE_SERVICE_KEY

# Configure logger
logger = logging.getLogger(__name__)

# Table name constant
JOURNAL_ENTRIES_TABLE = "journal_entries"
ANALYSIS_STATUSES = frozenset({"ok", "failed", "mock"})
USER_VOCABULARY_TABLE = "user_vocabulary"

# Table name for users (assuming it's 'users')
USERS_TABLE = "users"

def create_supabase_client() -> Client:
    """
    Create and configure a Supabase client instance.
    
    Returns:
        Configured Supabase client
        
    Raises:
        ValueError: If Supabase credentials are missing
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise ValueError(
            "Supabase credentials not found. "
            "Please set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables."
        )
    
    client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    
    # Initialize database schema
    try:
        init_db_schema(client)
    except Exception as e:
        logger.warning(f"Error initializing database schema: {str(e)}")
    
    return client


def init_db_schema(client: Client) -> None:
    """
    Initialize database schema if it doesn't exist.
    
    Args:
        client: Configured Supabase client
    """
    try:
        # Check and initialize journal_entries table
        try:
            client.table(JOURNAL_ENTRIES_TABLE).select("*").limit(1).execute()
            logger.info(f"Table {JOURNAL_ENTRIES_TABLE} already exists")
        except Exception as e:
            if "relation" in str(e) and "does not exist" in str(e):
                logger.info(f"Table {JOURNAL_ENTRIES_TABLE} does not exist. Attempting to create (manual creation recommended).")
                # Note: Supabase Python client doesn't directly support DDL.
                # This is a placeholder to inform the user.
                # Ideally, migrations or Supabase Studio should be used.
                logger.warning(f"Please create the table '{JOURNAL_ENTRIES_TABLE}' manually in Supabase Studio with the following schema if it does not exist:")
                logger.info(f"""
                CREATE TABLE IF NOT EXISTS public.{JOURNAL_ENTRIES_TABLE} (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID, -- Add foreign key to users table if you have one: REFERENCES auth.users(id) ON DELETE CASCADE
                    title VARCHAR(255),
                    language VARCHAR(50),
                    original_text TEXT NOT NULL,
                    corrected TEXT,
                    rewrite TEXT,
                    score INTEGER,
                    tone VARCHAR(50),
                    translation TEXT,
                    explanation TEXT, -- Added from previous work
                    rubric JSONB, -- Added from previous work
                    grammar_suggestions JSONB, -- Added from previous work
                    new_words JSONB, -- Added from previous work
                    sentence_mapping JSONB,
                    sentence_mapping_status TEXT,
                    sentence_actions JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
                """)
            else:
                # Different error, re-raise
                logger.warning(f"Error checking table {JOURNAL_ENTRIES_TABLE}: {str(e)}. It might already exist or another issue occurred.")

        # Check and initialize user_vocabulary table
        try:
            client.table(USER_VOCABULARY_TABLE).select("*").limit(1).execute()
            logger.info(f"Table {USER_VOCABULARY_TABLE} already exists")
        except Exception as e:
            if "relation" in str(e) and "does not exist" in str(e):
                logger.info(f"Table {USER_VOCABULARY_TABLE} does not exist. Attempting to create (manual creation recommended).")
                logger.warning(f"Please create the table '{USER_VOCABULARY_TABLE}' manually in Supabase Studio with the following schema if it does not exist:")
                logger.info(f"""
                CREATE TABLE IF NOT EXISTS public.{USER_VOCABULARY_TABLE} (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL, -- Add foreign key: REFERENCES auth.users(id) ON DELETE CASCADE
                    entry_id UUID REFERENCES public.{JOURNAL_ENTRIES_TABLE}(id) ON DELETE SET NULL,
                    term TEXT NOT NULL,
                    lemma TEXT NOT NULL,
                    language VARCHAR(50) NOT NULL,
                    part_of_speech VARCHAR(50),
                    definition TEXT,
                    reading TEXT, -- e.g., Furigana for Japanese
                    example_sentence TEXT,
                    status VARCHAR(50) DEFAULT 'new',
                    sense TEXT,
                    card JSONB,
                    card_status TEXT NOT NULL DEFAULT 'pending',
                    card_policy JSONB,
                    note TEXT,
                    tags TEXT[] NOT NULL DEFAULT '{{}}',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    CONSTRAINT unique_user_lemma_language UNIQUE (user_id, lemma, language)
                );
                COMMENT ON COLUMN public.{USER_VOCABULARY_TABLE}.entry_id IS 'Original entry where the word was encountered, if any.';
                COMMENT ON COLUMN public.{USER_VOCABULARY_TABLE}.reading IS 'Pronunciation aid, e.g., Furigana for Japanese, Pinyin for Chinese.';
                COMMENT ON COLUMN public.{USER_VOCABULARY_TABLE}.status IS 'Learning status of the vocabulary item.';
                """)
            else:
                logger.warning(f"Error checking table {USER_VOCABULARY_TABLE}: {str(e)}. It might already exist or another issue occurred.")
            
    except Exception as e:
        logger.error(f"Error during init_db_schema: {str(e)}")
        # Do not raise here, as the app should still try to run
        # Errors in table creation are logged for manual intervention.


def save_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Insert a journal entry dict into journal_entries table.
    
    Args:
        entry: Dictionary containing entry data with keys:
            - user_id (optional): The ID of the user who created the entry
            - original_text: The journal entry text
            - corrected: Grammar-corrected version
            - rewrite: Native-like rewrite
            - score: Fluency score (0-100)
            - tone: Detected emotional tone
            - translation: Direct translation
            
    Returns:
        The saved entry record with id and created_at
        
    Raises:
        Exception: If the database operation fails
    """
    if entry.get("analysis_status") not in ANALYSIS_STATUSES:
        raise ValueError(
            f"analysis_status must be one of {sorted(ANALYSIS_STATUSES)}, got {entry.get('analysis_status')!r}"
        )

    try:
        # Create Supabase client
        supabase = create_supabase_client()
        
        # Insert the entry into the journal_entries table
        response = supabase.table(JOURNAL_ENTRIES_TABLE).insert(entry).execute()
        
        # Extract the inserted record
        if response.data and len(response.data) > 0:
            return response.data[0]
        else:
            raise Exception(f"No data returned from insert operation: {response}")
            
    except Exception as e:
        logger.error(f"Error saving entry to Supabase: {str(e)}")
        raise


def fetch_entries(user_id: Optional[str] = None, language: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Return journal entries filtered by user_id and optionally by language, ordered by newest first.

    Args:
        user_id: The ID of the user whose entries to fetch (None for all entries)
        language: Filter by target_language (e.g., 'es', 'fr', 'ja') - None for all languages
        limit: Maximum number of entries to return (default 20)

    Returns:
        List of journal entry records with feedback

    Raises:
        Exception: If the database operation fails
    """
    try:
        # Create Supabase client
        supabase = create_supabase_client()

        # Build the query
        query = supabase.table(JOURNAL_ENTRIES_TABLE).select("*")

        # Filter by user_id if provided
        if user_id:
            query = query.eq("user_id", user_id)

        # Filter by language if provided
        if language:
            query = query.eq("target_language", language)
            
        # Apply limit
        query = query.limit(limit)
        
        # Execute the query
        response = query.execute()
        
        # Manually sort the results by created_at in descending order
        results = response.data
        results.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return results
    except Exception as e:
        logger.error(f"Error fetching entries from Supabase: {str(e)}")
        raise Exception(f"Error fetching entries: {str(e)}")


def fetch_language_profile(user_id: str, l2: str) -> Optional[Dict[str, Any]]:
    """Return the learner's immersion and proficiency for one target language."""
    supabase = create_supabase_client()
    response = (
        supabase.table("user_language_profiles")
        .select("*")
        .eq("user_id", user_id)
        .eq("l2", l2)
        .limit(1)
        .execute()
    )
    if response.data:
        return response.data[0]
    return None


def list_language_profiles(user_id: str) -> List[Dict[str, Any]]:
    """Return every per-language learning profile for a user."""
    supabase = create_supabase_client()
    response = (
        supabase.table("user_language_profiles")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )
    rows = response.data or []
    rows.sort(key=lambda row: row.get("l2") or "")
    return rows


SAVE_USER_SETTINGS_RPC = "save_user_settings"


def save_user_settings(
    user_id: str,
    settings: Dict[str, Any],
    profiles: Optional[List[Dict[str, Any]]],
) -> None:
    """Write user_settings and per-language profiles in one transaction."""
    supabase = create_supabase_client()
    supabase.rpc(
        SAVE_USER_SETTINGS_RPC,
        {
            "p_user_id": user_id,
            "p_settings": settings,
            "p_profiles": profiles or [],
        },
    ).execute()


def shape_entry_for_api(flat_entry_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Turn a flat journal_entries row into the GET /entries/{id} payload.

    Corrected text, the rewrite, analysis status, and the policy snapshot stay
    on the entry itself. The same feedback fields are also nested under
    ai_feedback for the existing entry page.
    """
    ai_feedback_fields = [
        "corrected", "rewrite", "score", "tone",
        "translation", "explanation", "rubric",
        "grammar_suggestions", "new_words",
        "sentence_mapping", "sentence_mapping_status",
        "sentence_actions",
    ]
    restructured_entry: Dict[str, Any] = {}
    ai_feedback_payload: Dict[str, Any] = {}

    for key, value in flat_entry_data.items():
        if key in ai_feedback_fields:
            ai_feedback_payload[key] = value
        elif key == "original_text":
            restructured_entry["content"] = value
        else:
            restructured_entry[key] = value

    restructured_entry["ai_feedback"] = ai_feedback_payload
    if "content" not in restructured_entry:
        restructured_entry["content"] = flat_entry_data.get("original_text")

    # Top-level copies the entry page and the LearningPolicy contract both read.
    restructured_entry["corrected"] = flat_entry_data.get("corrected")
    restructured_entry["rewrite"] = flat_entry_data.get("rewrite")
    restructured_entry["rewritten"] = flat_entry_data.get("rewrite")
    restructured_entry["analysis_status"] = flat_entry_data.get("analysis_status")
    restructured_entry["analysis_error_code"] = flat_entry_data.get("analysis_error_code")
    restructured_entry["policy_snapshot"] = flat_entry_data.get("policy_snapshot")
    return restructured_entry


def fetch_single_entry(entry_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a single journal entry by its ID and user_id.
    It now restructures the flat AI feedback fields from the database
    into a nested 'ai_feedback' dictionary to match the Pydantic model expectation.

    Args:
        entry_id: The ID of the entry to fetch.
        user_id: The ID of the user who owns the entry.

    Returns:
        The entry record with a nested 'ai_feedback' dictionary if found, else None.

    Raises:
        Exception: If the database operation fails.
    """
    try:
        supabase = create_supabase_client()
        response = (
            supabase.table(JOURNAL_ENTRIES_TABLE)
            .select("*")
            .eq("id", entry_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )

        if response.data:
            flat_entry_data = response.data
            logger.debug(f"Raw flat_entry_data from DB for {entry_id}: {flat_entry_data}")
            restructured_entry = shape_entry_for_api(flat_entry_data)
            logger.debug(f"Restructured entry for {entry_id} before Pydantic: {restructured_entry}")
            return restructured_entry
        else:
            logger.info(f"No entry found with id {entry_id} for user_id {user_id}")
            return None

    except Exception as e:
        if "PGRST116" in str(e) or "multiple (or no) rows returned" in str(e):
            logger.info(f"No entry found with id {entry_id} for user_id {user_id} (PostgREST .single() error indicative of 0 rows).")
            return None
        logger.error(f"Error fetching single entry from Supabase (id: {entry_id}, user: {user_id}): {str(e)}")
        raise


def update_entry_analysis(entry_id: str, user_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update the AI feedback columns for a journal entry.

    Args:
        entry_id: The ID of the entry to update.
        user_id: The ID of the user who owns the entry.
        update_data: Dictionary of columns to update.

    Returns:
        The updated entry record.

    Raises:
        Exception: If the database operation fails or the entry is not found.
    """
    try:
        supabase = create_supabase_client()
        response = (
            supabase.table(JOURNAL_ENTRIES_TABLE)
            .update(update_data)
            .eq("id", entry_id)
            .eq("user_id", user_id)
            .execute()
        )
        if response.data and len(response.data) > 0:
            return response.data[0]
        raise Exception(f"Entry {entry_id} not found or not owned by user {user_id}")
    except Exception as e:
        logger.error(f"Error updating entry analysis (id: {entry_id}, user: {user_id}): {str(e)}")
        raise


def delete_entry(entry_id: str, user_id: str) -> bool:
    """
    Delete a journal entry by its ID and user_id.

    Args:
        entry_id: The ID of the entry to delete.
        user_id: The ID of the user who owns the entry.

    Returns:
        True if the deletion was successful, False otherwise.

    Raises:
        Exception: If the database operation fails.
    """
    try:
        supabase = create_supabase_client()
        response = (
            supabase.table(JOURNAL_ENTRIES_TABLE)
            .delete()
            .eq("id", entry_id)
            .eq("user_id", user_id)
            .execute()
        )
        
        # Check if any rows were affected (Supabase delete typically returns data if rows were deleted)
        # For delete, response.data might be a list of the deleted rows or an empty list if no match.
        # The count of affected rows is more reliable if available, or check if data is not empty.
        if response.data and len(response.data) > 0:
            logger.info(f"Successfully deleted entry with id {entry_id} for user_id {user_id}")
            return True
        else:
            # This could mean the entry didn't exist or didn't belong to the user.
            # Or, if RLS is very strict, it might also lead to 0 rows affected without error.
            logger.warning(f"No entry found to delete with id {entry_id} for user_id {user_id}, or deletion was prevented.")
            return False

    except Exception as e:
        logger.error(f"Error deleting entry from Supabase (id: {entry_id}, user: {user_id}): {str(e)}")
        raise


def sign_in_with_magic_link(email: str) -> Dict[str, Any]:
    """
    Send a magic link to the provided email for passwordless authentication.
    
    Args:
        email: User's email address
        
    Returns:
        Response data from Supabase auth API
        
    Raises:
        Exception: If the authentication operation fails
    """
    try:
        # Create Supabase client
        supabase = create_supabase_client()
        
        # Send the magic link (OTP) email
        response = supabase.auth.sign_in_with_otp({"email": email})
        
        # Return the response data
        return {"success": True, "message": "Magic link sent to your email"}
            
    except Exception as e:
        logger.error(f"Error sending magic link with Supabase: {str(e)}")
        raise 

# TODO: Add a function to update an entry (e.g., mark as favorite)

# --- Vocabulary Functions ---

def save_vocabulary_item(item_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Save a new vocabulary item for a user or update if it exists (based on unique constraint).

    Args:
        item_data: Dictionary containing vocabulary item data.
                   Expected keys: term, language, part_of_speech, definition, 
                                  reading, example_sentence, status, entry_id (optional).
        user_id: The ID of the user.

    Returns:
        The saved or updated vocabulary item record.

    Raises:
        Exception: If the database operation fails.
    """
    try:
        supabase = create_supabase_client()
        
        item_data = {**item_data, "user_id": user_id}
        item_data["lemma"] = item_data.get("lemma") or item_data["term"]
        
        # Upsert based on the canonical lemma for this user and language.
        # Supabase `upsert` uses the primary key or unique constraints for conflict resolution.
        response = (
            supabase.table(USER_VOCABULARY_TABLE)
            .upsert(item_data, on_conflict="user_id,lemma,language")
            .execute()
        )
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        else:
            logger.error(f"No data returned from save_vocabulary_item operation: {response}")
            # This case should ideally not be hit with upsert if data is valid.
            raise Exception("Failed to save or update vocabulary item: No data returned")
            
    except Exception as e:
        logger.error(f"Error saving vocabulary item to Supabase for user {user_id}: {str(e)}")
        # Check for unique constraint violation if upsert somehow didn't handle it or if it was a different issue
        if "unique constraint" in str(e) and "unique_user_term_language" in str(e):
             logger.warning(f"Attempted to save a duplicate vocabulary item for user {user_id}, term '{item_data.get('term')}', language '{item_data.get('language')}'. This should have been an upsert.")
             # Optionally, try to fetch the existing item here if upsert isn't behaving as expected
        raise

def delete_vocabulary_item(item_id: str, user_id: str) -> bool:
    """
    Delete a vocabulary item by its ID for a specific user.

    Args:
        item_id: The ID of the vocabulary item to delete.
        user_id: The ID of the user who owns the item.

    Returns:
        True if deletion was successful, False otherwise.

    Raises:
        Exception: If the database operation fails.
    """
    try:
        supabase = create_supabase_client()
        response = (
            supabase.table(USER_VOCABULARY_TABLE)
            .delete()
            .eq("id", item_id)
            .eq("user_id", user_id) # Ensure user owns the item
            .execute()
        )
        
        if response.data and len(response.data) > 0:
            logger.info(f"Successfully deleted vocabulary item with id {item_id} for user {user_id}")
            return True
        else:
            logger.warning(f"No vocabulary item found to delete with id {item_id} for user {user_id}, or deletion was prevented.")
            return False
            
    except Exception as e:
        logger.error(f"Error deleting vocabulary item {item_id} for user {user_id}: {str(e)}")
        raise

def fetch_user_vocabulary(user_id: str, language: Optional[str] = None, limit: int = 500) -> List[Dict[str, Any]]:
    """
    Fetch all vocabulary items for a user, optionally filtered by language.

    Args:
        user_id: The ID of the user.
        language: Optional language to filter by.
        limit: Maximum number of items to return.

    Returns:
        A list of vocabulary item records.

    Raises:
        Exception: If the database operation fails.
    """
    try:
        supabase = create_supabase_client()
        query = supabase.table(USER_VOCABULARY_TABLE).select("*").eq("user_id", user_id)
        
        if language:
            query = query.eq("language", language)
            
        response = query.order("created_at", desc=True).limit(limit).execute()
        
        return response.data if response.data else []
        
    except Exception as e:
        logger.error(f"Error fetching vocabulary for user {user_id}: {str(e)}")
        raise

def fetch_vocabulary_item_by_term(user_id: str, term: str, language: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a specific vocabulary item for a user by term and language.

    Args:
        user_id: The ID of the user.
        term: The vocabulary term.
        language: The language of the term.

    Returns:
        The vocabulary item record if found, else None.

    Raises:
        Exception: If the database operation fails.
    """
    try:
        supabase = create_supabase_client()
        term_response = (
            supabase.table(USER_VOCABULARY_TABLE)
            .select("*")
            .eq("user_id", user_id)
            .eq("term", term)
            .eq("language", language)
            .maybe_single()
            .execute()
        )
        if term_response.data:
            return term_response.data
        lemma_response = (
            supabase.table(USER_VOCABULARY_TABLE)
            .select("*")
            .eq("user_id", user_id)
            .eq("lemma", term)
            .eq("language", language)
            .maybe_single()
            .execute()
        )
        return lemma_response.data
    except Exception as e:
        logger.error(f"Error fetching vocabulary item {term} for user {user_id} in language {language}: {str(e)}")
        return None

def fetch_vocabulary_item_by_id_and_user(item_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetches a single vocabulary item by its ID, ensuring it belongs to the specified user.

    Args:
        item_id: The ID of the vocabulary item.
        user_id: The ID of the user (must be UUID).

    Returns:
        A dictionary representing the vocabulary item if found and owned by the user, else None.
    """
    supabase = create_supabase_client()
    try:
        response = (
            supabase.table(USER_VOCABULARY_TABLE)
            .select("*")
            .eq("id", str(item_id))
            .eq("user_id", str(user_id))
            .maybe_single()
            .execute()
        )
        if response.data:
            logger.info(f"Successfully fetched vocabulary item {item_id} for user {user_id}.")
            return response.data
        else:
            logger.warning(f"Vocabulary item {item_id} not found for user {user_id} or does not exist.")
            return None
    except Exception as e:
        logger.error(f"Error fetching vocabulary item {item_id} for user {user_id}: {str(e)}")
        return None

def update_vocabulary_item(item_id: str, user_id: str, changes: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update one vocabulary row only when it belongs to ``user_id``."""
    if not changes:
        return fetch_vocabulary_item_by_id_and_user(item_id, user_id)
    supabase = create_supabase_client()
    response = (
        supabase.table(USER_VOCABULARY_TABLE)
        .update(changes)
        .eq("id", str(item_id))
        .eq("user_id", str(user_id))
        .execute()
    )
    return response.data[0] if response.data else None


def fetch_lookup_cache(
    user_id: str, language: str, text: str, sentence: str, vocab_def: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Return a successful lookup for this surface in the same sense-bearing context."""
    supabase = create_supabase_client()
    for column in ("surface", "lemma"):
        query = (
            supabase.table("word_encounters").select("*")
            .eq("user_id", user_id)
            .eq("language", language)
            .eq("card_status", "ok")
            .eq(column, text)
        )
        if vocab_def:
            query = query.eq("card_policy->>vocab_def", vocab_def)
        if sentence:
            query = query.eq("sentence", sentence)
        # Encounters that only record a use in the learner's entry carry no card.
        query = query.not_.is_("card", "null")
        response = query.order("created_at", desc=True).limit(1).execute()
        if response.data:
            return response.data[0]
    return None


def save_word_encounter(data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    response = (
        create_supabase_client().table("word_encounters")
        .insert({**data, "user_id": user_id}).execute()
    )
    if not response.data:
        raise RuntimeError("Word encounter was not recorded")
    return response.data[0]


def save_word_encounters(rows: List[Dict[str, Any]], user_id: str) -> List[Dict[str, Any]]:
    """Insert several encounters for one learner in a single request."""
    if not rows:
        return []
    response = (
        create_supabase_client().table("word_encounters")
        .insert([{**row, "user_id": user_id} for row in rows]).execute()
    )
    return response.data or []


def fetch_entry_encounters(
    user_id: str, entry_id: str, kinds: List[str], word_ids: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """The learner's encounters of these kinds that came from one entry."""
    query = (
        create_supabase_client().table("word_encounters").select("id, word_id, kind")
        .eq("user_id", user_id).eq("source_type", "entry").eq("source_id", entry_id).in_("kind", kinds)
    )
    if word_ids is not None:
        query = query.in_("word_id", word_ids)
    return query.execute().data or []


def delete_entry_encounters(
    user_id: str, entry_id: str, kinds: List[str], word_ids: Optional[List[str]] = None
) -> None:
    """Remove the learner's encounters of these kinds that came from one entry."""
    query = (
        create_supabase_client().table("word_encounters").delete()
        .eq("user_id", user_id).eq("source_type", "entry").eq("source_id", entry_id).in_("kind", kinds)
    )
    if word_ids is not None:
        query = query.in_("word_id", word_ids)
    query.execute()


def fetch_word_encounter(encounter_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    response = (
        create_supabase_client().table("word_encounters").select("*")
        .eq("id", encounter_id).eq("user_id", user_id).maybe_single().execute()
    )
    return response.data


def link_word_encounters(user_id: str, language: str, lemma: str, word_id: str) -> None:
    (
        create_supabase_client().table("word_encounters").update({"word_id": word_id})
        .eq("user_id", user_id).eq("language", language).eq("lemma", lemma).execute()
    )


def count_word_encounters(user_id: str, language: str, lemma: str) -> int:
    response = (
        create_supabase_client().table("word_encounters").select("id", count="exact")
        .eq("user_id", user_id).eq("language", language).eq("lemma", lemma).execute()
    )
    return response.count or len(response.data or [])


def get_daily_new_word_usage(user_id: str, language: str) -> tuple[int, int]:
    """Return today's study starts and the per-language cap."""
    supabase = create_supabase_client()
    profile = (
        supabase.table("user_language_profiles").select("daily_new_words")
        .eq("user_id", user_id).eq("l2", language).maybe_single().execute()
    )
    cap = int((profile.data or {}).get("daily_new_words", 10))
    today = datetime.now(timezone.utc).date().isoformat()
    starts = (
        supabase.table(USER_VOCABULARY_TABLE).select("id", count="exact")
        .eq("user_id", user_id).eq("language", language)
        .gte("study_started_at", today).execute()
    )
    return starts.count or len(starts.data or []), cap

async def get_user_by_email(db_client: Client, email: str) -> Optional['app.models.User']:
    """
    Fetch a user from the database by email.

    Args:
        db_client: The Supabase client instance.
        email: The email of the user to fetch.

    Returns:
        A User model instance if found, otherwise None.
    """
    # Need to import User model here to avoid circular dependency if database.py is imported by models.py
    # This is a common pattern. Alternatively, pass the model as an arg or use a string reference.
    from app.models import User  # Import the Pydantic User model

    try:
        response = (
            db_client.table(USERS_TABLE)
            .select("id, email, full_name, is_active, is_superuser, created_at, updated_at") # Select fields matching User model
            .eq("email", email)
            .maybe_single()  # Expects one or zero rows
            .execute()
        )
        if response.data:
            # Ensure all required fields for User model are present or have defaults
            user_data = response.data
            # Pydantic will validate and convert types (e.g., string to datetime)
            return User(**user_data)
        return None
    except Exception as e:
        logger.error(f"Error fetching user by email {email}: {str(e)}")
        return None
