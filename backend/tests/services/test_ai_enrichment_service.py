# backend/tests/services/test_ai_enrichment_service.py
import uuid
import pytest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException, status

from app.services.ai_enrichment_service import (
    get_or_create_enriched_details_service,
    call_ai_for_word_enrichment, # We might mock this directly or its underlying call
    generate_more_examples,    # New service function
    explain_like_i_am_five,    # New service function
    generate_mini_quiz         # New service function
)
from models import (
    EnrichedWordDetailsResponse, 
    WordAiCacheCreate,
    SynonymsAntonyms,
    WordAiCacheDB,
    MoreExamplesRequest, MoreExamplesResponse, # New models
    ELI5Request, ELI5Response,                # New models
    MiniQuizRequest, MiniQuizResponse, MiniQuizQuestion # New models
)
from app.feedback_engine import FeedbackEngine # For mocking

pytestmark = pytest.mark.asyncio

# Test data
TEST_ITEM_ID = uuid.uuid4()
TEST_USER_ID = uuid.uuid4()
TEST_LANGUAGE = "en"
TEST_TERM = "test_word"
TEST_WORD = "testword"

MOCK_VOCAB_ITEM_DB = {
    "id": TEST_ITEM_ID,
    "user_id": TEST_USER_ID,
    "term": TEST_TERM,
    "language": TEST_LANGUAGE,
    "part_of_speech": "noun",
    "definition": "A test word.",
    # ... other fields from UserVocabularyItemResponse if needed for the object hydration
}

MOCK_AI_GENERATED_DATA = {
    "ai_example_sentences": ["AI Sentence 1."],
    "synonyms_antonyms": {"synonyms": ["ai_syn"], "antonyms": ["ai_ant"]},
    "related_phrases": ["ai phrase"],
    "cultural_note": "AI cultural note.",
    "emotion_tone": "AI Tone",
    "mnemonic": "AI Mnemonic."
}

MOCK_CACHE_CREATE_MODEL = WordAiCacheCreate(
    word_vocabulary_id=TEST_ITEM_ID,
    language=TEST_LANGUAGE,
    **MOCK_AI_GENERATED_DATA
)

MOCK_SAVED_CACHE_DB_DICT = WordAiCacheDB(
    id=uuid.uuid4(), 
    created_at="2023-01-01T12:00:00Z", # Isoformat string for datetime
    updated_at="2023-01-01T12:00:00Z",
    **MOCK_CACHE_CREATE_MODEL.model_dump()
).model_dump()

MOCK_ENRICHED_RESPONSE_FROM_CACHE = EnrichedWordDetailsResponse(**MOCK_SAVED_CACHE_DB_DICT)
MOCK_ENRICHED_RESPONSE_FROM_AI = EnrichedWordDetailsResponse(
    id=MOCK_SAVED_CACHE_DB_DICT["id"], # Simulating it gets an id after saving
    **MOCK_CACHE_CREATE_MODEL.model_dump()
)

@pytest.fixture
def mock_db_fetch_vocab_item(monkeypatch):
    mock = AsyncMock(return_value=MOCK_VOCAB_ITEM_DB)
    monkeypatch.setattr("app.services.ai_enrichment_service.fetch_vocabulary_item_by_id_and_user", mock)
    return mock

@pytest.fixture
def mock_db_fetch_vocab_item_none(monkeypatch):
    mock = AsyncMock(return_value=None)
    monkeypatch.setattr("app.services.ai_enrichment_service.fetch_vocabulary_item_by_id_and_user", mock)
    return mock

@pytest.fixture
def mock_db_fetch_cache_entry(monkeypatch):
    mock = AsyncMock(return_value=MOCK_SAVED_CACHE_DB_DICT)
    monkeypatch.setattr("app.services.ai_enrichment_service.fetch_word_ai_cache_entry", mock)
    return mock

@pytest.fixture
def mock_db_fetch_cache_entry_none(monkeypatch):
    mock = AsyncMock(return_value=None)
    monkeypatch.setattr("app.services.ai_enrichment_service.fetch_word_ai_cache_entry", mock)
    return mock

@pytest.fixture
def mock_db_save_cache_entry(monkeypatch):
    # This mock should return a dict that matches WordAiCacheDB after saving
    mock = AsyncMock(return_value=MOCK_SAVED_CACHE_DB_DICT) 
    monkeypatch.setattr("app.services.ai_enrichment_service.save_word_ai_cache_entry", mock)
    return mock

@pytest.fixture
def mock_call_ai_enrichment(monkeypatch):
    mock = AsyncMock(return_value=MOCK_AI_GENERATED_DATA)
    # We are mocking the call_ai_for_word_enrichment function in the same service module
    monkeypatch.setattr("app.services.ai_enrichment_service.call_ai_for_word_enrichment", mock)
    return mock

@pytest.fixture
def mock_feedback_engine():
    engine = AsyncMock(spec=FeedbackEngine)
    engine.generate_additional_examples = AsyncMock(return_value=["Example 1", "Example 2"])
    engine.generate_eli5_explanation = AsyncMock(return_value="This is a simple explanation.")
    engine.generate_quiz = AsyncMock(return_value=MiniQuizResponse(
        quiz_title=f"Quiz for {TEST_WORD}",
        questions=[
            MiniQuizQuestion(question_text="Q1?", options=["A", "B"], correct_answer_index=0, explanation="Because A.")
        ]
    ))
    return engine

# --- Test Cases --- 

async def test_get_or_create_enriched_details_vocab_item_not_found(mock_db_fetch_vocab_item_none):
    with pytest.raises(HTTPException) as exc_info:
        await get_or_create_enriched_details_service(TEST_ITEM_ID, TEST_USER_ID, TEST_LANGUAGE)
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "Vocabulary item not found" in exc_info.value.detail
    mock_db_fetch_vocab_item_none.assert_called_once_with(item_id=TEST_ITEM_ID, user_id=TEST_USER_ID)

async def test_get_or_create_enriched_details_language_mismatch(mock_db_fetch_vocab_item):
    # Modify the mock to return a different language
    mock_db_fetch_vocab_item.return_value = {**MOCK_VOCAB_ITEM_DB, "language": "es"}
    with pytest.raises(HTTPException) as exc_info:
        await get_or_create_enriched_details_service(TEST_ITEM_ID, TEST_USER_ID, TEST_LANGUAGE) # Requesting 'en'
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "does not match the language of the stored vocabulary item" in exc_info.value.detail

async def test_get_or_create_enriched_details_cache_hit(
    mock_db_fetch_vocab_item,
    mock_db_fetch_cache_entry,
    # We don't need mock_call_ai_enrichment or mock_db_save_cache_entry if cache hits
):
    response = await get_or_create_enriched_details_service(TEST_ITEM_ID, TEST_USER_ID, TEST_LANGUAGE)
    assert response == MOCK_ENRICHED_RESPONSE_FROM_CACHE
    mock_db_fetch_vocab_item.assert_called_once_with(item_id=TEST_ITEM_ID, user_id=TEST_USER_ID)
    mock_db_fetch_cache_entry.assert_called_once_with(word_vocabulary_id=TEST_ITEM_ID, language=TEST_LANGUAGE)


async def test_get_or_create_enriched_details_cache_miss_ai_success(
    mock_db_fetch_vocab_item,
    mock_db_fetch_cache_entry_none, # Cache miss
    mock_call_ai_enrichment,      # AI call will be made
    mock_db_save_cache_entry      # Save to cache will be attempted
):
    response = await get_or_create_enriched_details_service(TEST_ITEM_ID, TEST_USER_ID, TEST_LANGUAGE)
    
    # The response should be constructed from the saved cache data, which includes an id and timestamps
    assert response.word_vocabulary_id == TEST_ITEM_ID
    assert response.language == TEST_LANGUAGE
    assert response.ai_example_sentences == MOCK_AI_GENERATED_DATA["ai_example_sentences"]
    assert response.synonyms_antonyms.model_dump() == MOCK_AI_GENERATED_DATA["synonyms_antonyms"]
    # Add more assertions for other fields as needed

    mock_db_fetch_vocab_item.assert_called_once_with(item_id=TEST_ITEM_ID, user_id=TEST_USER_ID)
    mock_db_fetch_cache_entry_none.assert_called_once_with(word_vocabulary_id=TEST_ITEM_ID, language=TEST_LANGUAGE)
    mock_call_ai_enrichment.assert_called_once_with(term=TEST_TERM, language=TEST_LANGUAGE)
    
    # Check what was passed to save_word_ai_cache_entry
    # The argument to save_word_ai_cache_entry is cache_data.model_dump()
    expected_save_arg = MOCK_CACHE_CREATE_MODEL.model_dump()
    mock_db_save_cache_entry.assert_called_once_with(cache_data=expected_save_arg)


async def test_get_or_create_enriched_details_ai_call_fails(
    mock_db_fetch_vocab_item,
    mock_db_fetch_cache_entry_none,
    mock_call_ai_enrichment # This will be modified to raise an error
):
    mock_call_ai_enrichment.side_effect = Exception("AI Provider Down")

    with pytest.raises(HTTPException) as exc_info:
        await get_or_create_enriched_details_service(TEST_ITEM_ID, TEST_USER_ID, TEST_LANGUAGE)
    
    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Failed to generate or cache AI enrichment" in exc_info.value.detail
    assert "AI Provider Down" in exc_info.value.detail # Check if original error is propagated in detail
    mock_call_ai_enrichment.assert_called_once_with(term=TEST_TERM, language=TEST_LANGUAGE)


async def test_get_or_create_enriched_details_db_save_fails(
    mock_db_fetch_vocab_item,
    mock_db_fetch_cache_entry_none, 
    mock_call_ai_enrichment,
    mock_db_save_cache_entry # This will be modified to return None (simulating save failure)
):
    mock_db_save_cache_entry.return_value = None # Simulate save failure

    response = await get_or_create_enriched_details_service(TEST_ITEM_ID, TEST_USER_ID, TEST_LANGUAGE)

    assert response.word_vocabulary_id == TEST_ITEM_ID
    assert response.ai_example_sentences == MOCK_AI_GENERATED_DATA["ai_example_sentences"]
    assert isinstance(response.id, uuid.UUID) # ID should be a UUID, even if transient
    assert response.id is not None # Ensure an ID was actually generated
    
    mock_db_save_cache_entry.assert_called_once()


async def test_get_or_create_enriched_details_term_missing_in_vocab_item(
    mock_db_fetch_vocab_item
):
    # Modify the mock to return a vocab item without a 'term'
    vocab_item_no_term = MOCK_VOCAB_ITEM_DB.copy()
    del vocab_item_no_term['term']
    mock_db_fetch_vocab_item.return_value = vocab_item_no_term

    with pytest.raises(HTTPException) as exc_info:
        await get_or_create_enriched_details_service(TEST_ITEM_ID, TEST_USER_ID, TEST_LANGUAGE)
    
    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Vocabulary item data is incomplete" in exc_info.value.detail


# Test for the call_ai_for_word_enrichment helper itself (optional, as it's simple)
async def test_call_ai_for_word_enrichment_success():
    with patch("app.services.ai_enrichment_service.generate_word_enrichment_details", new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = MOCK_AI_GENERATED_DATA
        result = await call_ai_for_word_enrichment(TEST_TERM, TEST_LANGUAGE)
        assert result == MOCK_AI_GENERATED_DATA
        mock_generate.assert_called_once_with(term=TEST_TERM, language=TEST_LANGUAGE)

async def test_call_ai_for_word_enrichment_failure():
    with patch("app.services.ai_enrichment_service.generate_word_enrichment_details", new_callable=AsyncMock) as mock_generate:
        mock_generate.side_effect = Exception("AI Engine Error")
        result = await call_ai_for_word_enrichment(TEST_TERM, TEST_LANGUAGE)
        # Check for fallback structure
        assert result["cultural_note"] == "AI enrichment failed."
        assert not result["ai_example_sentences"] # Should be empty list
        assert result["synonyms_antonyms"] == {"synonyms": [], "antonyms": []} 

# --- Tests for On-Demand AI Generation --- 

TEST_WORD = "testword"
TEST_LANG = "en"

async def test_generate_more_examples_success(mock_feedback_engine):
    request = MoreExamplesRequest(word=TEST_WORD, language=TEST_LANG)
    response = await generate_more_examples(db=AsyncMock(), request=request, feedback_engine=mock_feedback_engine)
    assert isinstance(response, MoreExamplesResponse)
    assert response.new_example_sentences == ["Example 1", "Example 2"]
    mock_feedback_engine.generate_additional_examples.assert_called_once_with(
        word=TEST_WORD, 
        language=TEST_LANG, 
        existing_examples=None,
        target_audience_level="intermediate" # Default from model
    )

async def test_generate_more_examples_ai_returns_empty(mock_feedback_engine):
    mock_feedback_engine.generate_additional_examples.return_value = []
    request = MoreExamplesRequest(word=TEST_WORD, language=TEST_LANG)
    with pytest.raises(HTTPException) as exc_info:
        await generate_more_examples(db=AsyncMock(), request=request, feedback_engine=mock_feedback_engine)
    assert exc_info.value.status_code == 500
    assert "AI engine failed to generate more examples" in exc_info.value.detail

async def test_generate_more_examples_ai_raises_exception(mock_feedback_engine):
    mock_feedback_engine.generate_additional_examples.side_effect = Exception("AI Down")
    request = MoreExamplesRequest(word=TEST_WORD, language=TEST_LANG)
    with pytest.raises(HTTPException) as exc_info:
        await generate_more_examples(db=AsyncMock(), request=request, feedback_engine=mock_feedback_engine)
    assert exc_info.value.status_code == 500
    assert "Failed to generate more examples: AI Down" in exc_info.value.detail

async def test_explain_like_i_am_five_success(mock_feedback_engine):
    request = ELI5Request(term=TEST_WORD, language=TEST_LANG)
    response = await explain_like_i_am_five(db=AsyncMock(), request=request, feedback_engine=mock_feedback_engine)
    assert isinstance(response, ELI5Response)
    assert response.explanation == "This is a simple explanation."
    mock_feedback_engine.generate_eli5_explanation.assert_called_once_with(term=TEST_WORD, language=TEST_LANG)

async def test_explain_like_i_am_five_ai_returns_empty(mock_feedback_engine):
    mock_feedback_engine.generate_eli5_explanation.return_value = "" # Empty string
    request = ELI5Request(term=TEST_WORD, language=TEST_LANG)
    with pytest.raises(HTTPException) as exc_info:
        await explain_like_i_am_five(db=AsyncMock(), request=request, feedback_engine=mock_feedback_engine)
    assert exc_info.value.status_code == 500
    assert "AI engine failed to generate ELI5 explanation" in exc_info.value.detail

async def test_explain_like_i_am_five_ai_raises_exception(mock_feedback_engine):
    mock_feedback_engine.generate_eli5_explanation.side_effect = Exception("AI Broken")
    request = ELI5Request(term=TEST_WORD, language=TEST_LANG)
    with pytest.raises(HTTPException) as exc_info:
        await explain_like_i_am_five(db=AsyncMock(), request=request, feedback_engine=mock_feedback_engine)
    assert exc_info.value.status_code == 500