import logging
import uuid
from fastapi import HTTPException, status
from typing import Optional, Dict, Any

from app.models import EnrichedWordDetailsResponse
from app.feedback_engine import FeedbackEngine
from database import fetch_user_vocabulary_item_by_id

logger = logging.getLogger(__name__)

# Comprehensive bidirectional language mapping for 24+ languages
LANGUAGE_MAPPINGS = {
    # Spanish
    'es': 'Spanish', 'spanish': 'Spanish', 'spa': 'Spanish', 'español': 'Spanish',
    'Spanish': 'es', 'ESP': 'es', 'castilian': 'Spanish', 'castellano': 'Spanish',
    
    # English  
    'en': 'English', 'english': 'English', 'eng': 'English',
    'English': 'en', 'ENG': 'en',
    
    # French
    'fr': 'French', 'french': 'French', 'fra': 'French', 'français': 'French',
    'French': 'fr', 'FRA': 'fr', 'francais': 'French',
    
    # German
    'de': 'German', 'german': 'German', 'deu': 'German', 'deutsch': 'German',
    'German': 'de', 'DEU': 'de', 'ger': 'German',
    
    # Italian
    'it': 'Italian', 'italian': 'Italian', 'ita': 'Italian', 'italiano': 'Italian',
    'Italian': 'it', 'ITA': 'it',
    
    # Portuguese
    'pt': 'Portuguese', 'portuguese': 'Portuguese', 'por': 'Portuguese', 'português': 'Portuguese',
    'Portuguese': 'pt', 'POR': 'pt', 'portugues': 'Portuguese',
    
    # Japanese
    'ja': 'Japanese', 'japanese': 'Japanese', 'jpn': 'Japanese', '日本語': 'Japanese',
    'Japanese': 'ja', 'JPN': 'ja', 'nihongo': 'Japanese',
    
    # Chinese
    'zh': 'Chinese', 'chinese': 'Chinese', 'cmn': 'Chinese', '中文': 'Chinese',
    'Chinese': 'zh', 'CHN': 'zh', 'mandarin': 'Chinese',
    
    # Korean
    'ko': 'Korean', 'korean': 'Korean', 'kor': 'Korean', '한국어': 'Korean',
    'Korean': 'ko', 'KOR': 'ko', 'hangul': 'Korean',
    
    # Russian
    'ru': 'Russian', 'russian': 'Russian', 'rus': 'Russian', 'русский': 'Russian',
    'Russian': 'ru', 'RUS': 'ru',
    
    # Arabic
    'ar': 'Arabic', 'arabic': 'Arabic', 'ara': 'Arabic', 'العربية': 'Arabic',
    'Arabic': 'ar', 'ARA': 'ar',
    
    # Dutch
    'nl': 'Dutch', 'dutch': 'Dutch', 'nld': 'Dutch', 'nederlands': 'Dutch',
    'Dutch': 'nl', 'NLD': 'nl',
    
    # Swedish
    'sv': 'Swedish', 'swedish': 'Swedish', 'swe': 'Swedish', 'svenska': 'Swedish',
    'Swedish': 'sv', 'SWE': 'sv',
    
    # Norwegian
    'no': 'Norwegian', 'norwegian': 'Norwegian', 'nor': 'Norwegian', 'norsk': 'Norwegian',
    'Norwegian': 'no', 'NOR': 'no',
    
    # Danish
    'da': 'Danish', 'danish': 'Danish', 'dan': 'Danish', 'dansk': 'Danish',
    'Danish': 'da', 'DAN': 'da',
    
    # Polish
    'pl': 'Polish', 'polish': 'Polish', 'pol': 'Polish', 'polski': 'Polish',
    'Polish': 'pl', 'POL': 'pl',
    
    # Czech
    'cs': 'Czech', 'czech': 'Czech', 'ces': 'Czech', 'čeština': 'Czech',
    'Czech': 'cs', 'CES': 'cs', 'cestina': 'Czech',
    
    # Hungarian
    'hu': 'Hungarian', 'hungarian': 'Hungarian', 'hun': 'Hungarian', 'magyar': 'Hungarian',
    'Hungarian': 'hu', 'HUN': 'hu',
    
    # Finnish
    'fi': 'Finnish', 'finnish': 'Finnish', 'fin': 'Finnish', 'suomi': 'Finnish',
    'Finnish': 'fi', 'FIN': 'fi',
    
    # Turkish
    'tr': 'Turkish', 'turkish': 'Turkish', 'tur': 'Turkish', 'türkçe': 'Turkish',
    'Turkish': 'tr', 'TUR': 'tr', 'turkce': 'Turkish',
    
    # Greek
    'el': 'Greek', 'greek': 'Greek', 'ell': 'Greek', 'ελληνικά': 'Greek',
    'Greek': 'el', 'ELL': 'el', 'ellinika': 'Greek',
    
    # Hebrew
    'he': 'Hebrew', 'hebrew': 'Hebrew', 'heb': 'Hebrew', 'עברית': 'Hebrew',
    'Hebrew': 'he', 'HEB': 'he',
    
    # Hindi
    'hi': 'Hindi', 'hindi': 'Hindi', 'hin': 'Hindi', 'हिन्दी': 'Hindi',
    'Hindi': 'hi', 'HIN': 'hi',
    
    # Thai
    'th': 'Thai', 'thai': 'Thai', 'tha': 'Thai', 'ไทย': 'Thai',
    'Thai': 'th', 'THA': 'th',
    
    # Vietnamese
    'vi': 'Vietnamese', 'vietnamese': 'Vietnamese', 'vie': 'Vietnamese', 'tiếng việt': 'Vietnamese',
    'Vietnamese': 'vi', 'VIE': 'vi', 'tieng viet': 'Vietnamese',
}

def normalize_language(language_input: str, to_code: bool = True) -> str:
    """
    Normalize language input to either language code (e.g., 'es') or full name (e.g., 'Spanish').
    
    Args:
        language_input: The input language string (e.g., 'Spanish', 'es', 'español')
        to_code: If True, return language code. If False, return full language name.
    
    Returns:
        Normalized language string
    """
    if not language_input:
        return language_input
    
    # Clean and normalize input
    cleaned_input = language_input.strip().lower()
    
    # Look up in mappings
    mapped_value = LANGUAGE_MAPPINGS.get(cleaned_input)
    if mapped_value:
        if to_code:
            # If mapped_value is a full name, find its code
            if len(mapped_value) > 3:  # It's a full name like 'Spanish'
                code = LANGUAGE_MAPPINGS.get(mapped_value)
                return code if code else language_input
            else:  # It's already a code like 'es'
                return mapped_value
        else:
            # Return full name
            if len(mapped_value) > 3:  # It's already a full name
                return mapped_value
            else:  # It's a code, find the full name
                for key, value in LANGUAGE_MAPPINGS.items():
                    if value == mapped_value and len(key) > 3:
                        return key
                return language_input
    
    # If no mapping found, return original
    return language_input

async def update_user_vocabulary_with_enrichment(
    user_id: uuid.UUID,
    item_id: uuid.UUID,
    enrichment_data: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Update user_vocabulary table with AI enrichment data.
    
    Args:
        user_id: User UUID
        item_id: Vocabulary item UUID
        enrichment_data: Dictionary containing enrichment fields
    
    Returns:
        Updated vocabulary item or None if failed
    """
    try:
        from supabase import create_client
        import os
        
        # Create Supabase client
        supabase = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        )
        
        # Update the vocabulary item with enrichment data
        result = supabase.table("user_vocabulary").update(enrichment_data).eq("id", str(item_id)).eq("user_id", str(user_id)).execute()
        
        if result.data:
            logger.info(f"Successfully updated user_vocabulary item {item_id} with enrichment data")
            return result.data[0]
        else:
            logger.error(f"Failed to update user_vocabulary item {item_id}")
            return None
            
    except Exception as e:
        logger.error(f"Error updating user_vocabulary with enrichment: {e}")
        return None

async def get_or_create_enriched_details_service(
    item_id: uuid.UUID, 
    user_id: uuid.UUID, 
    language: str,
    db, # Mock database session (not used with Supabase functions) 
    feedback_engine: FeedbackEngine
) -> EnrichedWordDetailsResponse:
    """
    Retrieve AI-enriched details for a vocabulary item directly from user_vocabulary table.
    If enrichment doesn't exist, generate it and save directly to user_vocabulary.
    
    Args:
        item_id: The unique identifier of the vocabulary item in the user's list.
        user_id: The UUID of the authenticated user.
        language: The language of the vocabulary item (e.g., "Spanish", "es", "Japanese", "ja").
        db: Database session (not used with Supabase, but kept for interface compatibility).
        feedback_engine: The AI feedback engine to generate enrichments.
    
    Returns:
        EnrichedWordDetailsResponse: Contains comprehensive AI-generated information about the vocabulary word.
        
    Raises:
        HTTPException: If the vocabulary item is not found, permission denied, or generation fails.
    """
    logger.info(f"Starting enrichment service for item_id: {item_id}, user_id: {user_id}, language: {language}")
    
    # 1. Validate that the vocabulary item exists and belongs to the user
    vocab_item = await fetch_user_vocabulary_item_by_id(user_id=user_id, item_id=item_id)
    if not vocab_item:
        logger.warning(f"Vocabulary item {item_id} not found for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vocabulary item not found or you do not have permission to access it."
        )
    
    logger.info(f"Vocabulary item found: {vocab_item['term']} ({vocab_item['language']})")
    
    # 2. Check if enrichment data already exists in user_vocabulary
    if vocab_item.get('ai_synonyms') or vocab_item.get('emoji') or vocab_item.get('emotion_tone'):
        logger.info(f"Enrichment data already exists for item_id: {item_id}")
        # Return existing enrichment data
        enrichment_data = {
            "id": item_id,
            "ai_example_sentences": vocab_item.get('ai_example_sentences', []),
            "ai_definitions": vocab_item.get('ai_definitions', []),
            "ai_synonyms": vocab_item.get('ai_synonyms', []),
            "ai_antonyms": vocab_item.get('ai_antonyms', []),
            "ai_related_phrases": vocab_item.get('ai_related_phrases', []),
            "ai_conjugation_info": vocab_item.get('ai_conjugation_info', {}),
            "ai_cultural_note": vocab_item.get('ai_cultural_note', ""),
            "ai_pronunciation_guide": vocab_item.get('ai_pronunciation_guide', ""),
            "ai_alternative_forms": vocab_item.get('ai_alternative_forms', []),
            "ai_common_mistakes": vocab_item.get('ai_common_mistakes', []),
            "emotion_tone": vocab_item.get('emotion_tone', ""),
            "mnemonic": vocab_item.get('mnemonic', ""),
            "emoji": vocab_item.get('emoji', ""),
            "source_model": vocab_item.get('source_model', ""),
            "word_vocabulary_id": item_id,
            "language": vocab_item['language'],
            "created_at": vocab_item.get('created_at', ''),
            "updated_at": vocab_item.get('updated_at', ''),
            "last_accessed_at": None
        }
        return EnrichedWordDetailsResponse(**enrichment_data)

    # 3. Generate new enrichment if it doesn't exist
    logger.info(f"No enrichment data found for item_id: {item_id}. Generating new enrichment.")
    
    # Normalize language for AI generation
    vocab_lang_code = normalize_language(vocab_item['language'])
    
    try:
        ai_generated_data_dict = await feedback_engine.generate_word_enrichment_details(
            term=vocab_item['term'], 
            language=vocab_lang_code  # Use normalized language code for AI generation
        )
        
        # Update user_vocabulary directly with enrichment data
        enrichment_update = {
            "ai_example_sentences": ai_generated_data_dict.get('ai_example_sentences', []),
            "ai_definitions": ai_generated_data_dict.get('ai_definitions', []),
            "ai_synonyms": ai_generated_data_dict.get('ai_synonyms', []),
            "ai_antonyms": ai_generated_data_dict.get('ai_antonyms', []),
            "ai_related_phrases": ai_generated_data_dict.get('ai_related_phrases', []),
            "ai_conjugation_info": ai_generated_data_dict.get('ai_conjugation_info', {}),
            "ai_cultural_note": ai_generated_data_dict.get('ai_cultural_note', ""),
            "ai_pronunciation_guide": ai_generated_data_dict.get('ai_pronunciation_guide', ""),
            "ai_alternative_forms": ai_generated_data_dict.get('ai_alternative_forms', []),
            "ai_common_mistakes": ai_generated_data_dict.get('ai_common_mistakes', []),
            "emotion_tone": ai_generated_data_dict.get('emotion_tone', ""),
            "mnemonic": ai_generated_data_dict.get('mnemonic', ""),
            "emoji": ai_generated_data_dict.get('emoji', ""),
            "source_model": ai_generated_data_dict.get('source_model', "atomic_agents")
        }
        
        # Save enrichment data directly to user_vocabulary
        updated_vocab_item = await update_user_vocabulary_with_enrichment(
            user_id=user_id,
            item_id=item_id,
            enrichment_data=enrichment_update
        )
        
        if not updated_vocab_item:
            logger.error(f"Failed to save AI enrichment to user_vocabulary for item_id: {item_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save AI enrichment data"
            )

        logger.info(f"Successfully generated and saved AI enrichment for item_id: {item_id}, language: {language}")
        
        # Return the enriched data
        enrichment_data = {
            "id": item_id,
            **enrichment_update,
            "word_vocabulary_id": item_id,
            "language": vocab_item['language'],
            "created_at": vocab_item.get('created_at', ''),
            "updated_at": vocab_item.get('updated_at', ''),
            "last_accessed_at": None
        }
        return EnrichedWordDetailsResponse(**enrichment_data)

    except Exception as e:
        logger.error(f"Error during AI enrichment for item_id {item_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate AI enrichment: {str(e)}"
        )
