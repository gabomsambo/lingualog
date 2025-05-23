"""
Supabase integration for LinguaLog.

This module handles all interactions with Supabase for database operations
and user authentication.
"""
import logging
from typing import Dict, List, Any, Optional, Union

# Import Supabase client
from supabase import create_client, Client

# Import environment variables
from config import SUPABASE_URL, SUPABASE_SERVICE_KEY

# Configure logger
logger = logging.getLogger(__name__)

# Table name constant
JOURNAL_ENTRIES_TABLE = "journal_entries"


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
        # Since we can't easily create tables with the Supabase Python client,
        # we'll check if the table exists by querying it and catching the error
        try:
            client.table(JOURNAL_ENTRIES_TABLE).select("*").limit(1).execute()
            logger.info(f"Table {JOURNAL_ENTRIES_TABLE} already exists")
            return  # Table exists, nothing to do
        except Exception as e:
            if "relation" in str(e) and "does not exist" in str(e):
                logger.info(f"Table {JOURNAL_ENTRIES_TABLE} does not exist")
                logger.warning("Unable to create table automatically. Please create the table manually in the Supabase dashboard.")
                logger.info(f"""
                CREATE TABLE IF NOT EXISTS public.{JOURNAL_ENTRIES_TABLE} (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID,
                    title VARCHAR(255),
                    language VARCHAR(50),
                    original_text TEXT NOT NULL,
                    corrected TEXT,
                    rewrite TEXT,
                    score INTEGER,
                    tone VARCHAR(50),
                    translation TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
                """)
            else:
                # Different error, re-raise
                raise e
            
    except Exception as e:
        logger.error(f"Error checking database schema: {str(e)}")
        raise


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

    Args:
        entry_id: The ID of the entry to fetch.
        user_id: The ID of the user who owns the entry.

    Returns:
        The entry record if found and matches user_id, else None.

    Raises:
        Exception: If the database operation fails.
    """
    try:
        supabase = create_supabase_client()
        response = (
            supabase.table(JOURNAL_ENTRIES_TABLE)
            .select("*")
            .eq("id", entry_id)
            .eq("user_id", user_id) # Ensure it belongs to the user
            .single()  # Expects a single row or raises an error if more/less (unless PostgREST error)
            .execute()
        )

        # response.data will be None if no row found, or the dict if found.
        # If .single() encounters 0 rows, it should result in an error handled by PostgREST
        # which the Supabase client might convert. If it returns None in data, that's our non-found case.
        if response.data:
            return response.data
        else:
            # This case might also be hit if PostgREST returns 0 rows and .single() doesn't error out as expected
            # or if there was an issue that didn't throw an exception but returned no data.
            logger.info(f"No entry found with id {entry_id} for user_id {user_id}")
            return None

    except Exception as e:
        # Check if it's a PostgREST error for 0 rows when .single() was used
        # Supabase client might wrap this, e.g. in a PostgrestAPIError
        # A common error message for .single() and 0 rows is "JSON object requested, multiple (or no) rows returned"
        if "PGRST116" in str(e) or "multiple (or no) rows returned" in str(e):
            logger.info(f"No entry found with id {entry_id} for user_id {user_id} (PostgREST .single() error indicative of 0 rows).")
            return None
        logger.error(f"Error fetching single entry from Supabase (id: {entry_id}, user: {user_id}): {str(e)}")
        raise # Re-raise other errors


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