"""
Supabase integration for LinguaLog.

This module handles all interactions with Supabase for database operations
and user authentication.
"""
import logging
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
USER_VOCABULARY_TABLE = "user_vocabulary"
WORD_AI_CACHE_TABLE = "word_ai_cache" # New table name constant

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
                    language VARCHAR(50) NOT NULL,
                    part_of_speech VARCHAR(50),
                    definition TEXT,
                    reading TEXT, -- e.g., Furigana for Japanese
                    example_sentence TEXT,
                    status VARCHAR(50) DEFAULT 'saved', -- e.g., 'saved', 'learning', 'mastered'
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    CONSTRAINT unique_user_term_language UNIQUE (user_id, term, language)
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
    try:
        # Create Supabase client
        supabase = create_supabase_client()
        
        # Insert the entry into the journal_entries table
        response = supabase.table(JOURNAL_ENTRIES_TABLE).insert(entry).execute()
        
        # Extract the inserted record
        if response.data and len(response.data) > 0:
            return response.data[0]
        else:
            logger.error(f"No data returned from insert operation: {response}")
            return {"id": "unknown", "created_at": "unknown"}
            
    except Exception as e:
        logger.error(f"Error saving entry to Supabase: {str(e)}")
        raise


def fetch_entries(user_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Return journal entries filtered by user_id, ordered by newest first.
    
    Args:
        user_id: The ID of the user whose entries to fetch (None for all entries)
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

            # Fields that belong inside the ai_feedback object
            ai_feedback_fields = [
                "corrected", "rewrite", "score", "tone", 
                "translation", "explanation", "rubric", 
                "grammar_suggestions", "new_words"
            ]
            
            # Initialize the main entry dictionary and the nested ai_feedback dictionary
            restructured_entry = {}
            ai_feedback_payload = {}

            for key, value in flat_entry_data.items():
                if key in ai_feedback_fields:
                    ai_feedback_payload[key] = value
                else:
                    # Handle original_text to content mapping for JournalEntryBase
                    if key == "original_text":
                        restructured_entry["content"] = value
                    else:
                        restructured_entry[key] = value
            
            # Add the populated ai_feedback object to the main entry
            # Even if ai_feedback_payload is empty, assign it so the field exists.
            restructured_entry["ai_feedback"] = ai_feedback_payload

            # Ensure essential base fields are present if not mapped from original_text
            if "content" not in restructured_entry and "original_text" in flat_entry_data:
                 restructured_entry["content"] = flat_entry_data["original_text"]
            elif "content" not in restructured_entry:
                 restructured_entry["content"] = None # Or some default / error handling

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
        
        # Add user_id to the item_data
        item_data["user_id"] = user_id
        
        # Upsert based on the unique constraint (user_id, term, language)
        # Supabase `upsert` uses the primary key or unique constraints for conflict resolution.
        response = (
            supabase.table(USER_VOCABULARY_TABLE)
            .upsert(item_data, on_conflict="user_id,term,language") 
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
        response = (
            supabase.table(USER_VOCABULARY_TABLE)
            .select("*")
            .eq("user_id", user_id)
            .eq("term", term)
            .eq("language", language)
            .maybe_single() # Returns one row or None, errors if multiple (should not happen with unique constraint)
            .execute()
        )
        return response.data
    except Exception as e:
        logger.error(f"Error fetching vocabulary item {term} for user {user_id} in language {language}: {str(e)}")
        return None

async def fetch_vocabulary_item_by_id_and_user(item_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Dict[str, Any]]:
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
            .select("id, user_id, term, language, part_of_speech, definition, reading, example_sentence, status, created_at, updated_at, entry_id") # Select all relevant fields
            .eq("id", str(item_id)) # Ensure item_id is string for Supabase query if it expects string UUIDs
            .eq("user_id", str(user_id)) # Ensure user_id is string for Supabase query
            .single()
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

async def fetch_word_ai_cache_entry(word_vocabulary_id: uuid.UUID, language: str) -> Optional[Dict[str, Any]]:
    """
    Fetches an AI cache entry from word_ai_cache.

    Args:
        word_vocabulary_id: The UUID of the vocabulary item (foreign key).
        language: The language of the cached entry.

    Returns:
        A dictionary representing the cache entry if found, else None.
    """
    try:
        supabase = create_supabase_client()
        response = (
            supabase.table(WORD_AI_CACHE_TABLE)
            .select("*") # Select all fields needed for EnrichedWordDetailsResponse
            .eq("word_vocabulary_id", str(word_vocabulary_id))
            .eq("language", language)
            .limit(1)
            .execute()
        )
        if response.data:
            entry = response.data[0]
            return entry
        return None
    except Exception as e:
        logger.error(
            f"Error fetching AI cache for vocab_id {word_vocabulary_id}, lang {language}: {e}"
        )
        return None

async def save_word_ai_cache_entry(cache_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Saves an AI cache entry to the word_ai_cache table.
    Expects cache_data to conform to WordAiCacheCreate model dump.

    Args:
        cache_data: A dictionary representing the data to insert.
                    Must include 'word_vocabulary_id' and 'language'.

    Returns:
        The saved cache entry dictionary if successful, else None.
    """
    if not all(k in cache_data for k in ["word_vocabulary_id", "language"]):
        logger.error("Attempted to save cache entry without word_vocabulary_id or language.")
        return None
        
    try:
        supabase = create_supabase_client()
        
        if isinstance(cache_data.get("word_vocabulary_id"), uuid.UUID):
            cache_data["word_vocabulary_id"] = str(cache_data["word_vocabulary_id"])

        response = (
            supabase.table(WORD_AI_CACHE_TABLE)
            .upsert(cache_data, on_conflict="word_vocabulary_id, language") 
            .execute()
        )
        if response.data:
            logger.info(f"Successfully upserted AI cache for vocab_id: {cache_data['word_vocabulary_id']}, lang: {cache_data['language']}")
            return response.data[0]
        else:
            logger.error(f"Failed to save or update AI cache for vocab_id: {cache_data['word_vocabulary_id']}. Response: {response.error}")
            return None
    except Exception as e:
        logger.error(
            f"Error saving AI cache for vocab_id {cache_data.get('word_vocabulary_id')}: {e}"
        )
        return None

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