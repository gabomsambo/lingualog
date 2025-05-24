# backend/tests/routers/test_vocabulary_ai.py
import uuid
import pytest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException, status, Request
from httpx import AsyncClient

# Assuming your FastAPI app instance is in backend.server.app
# Adjust the import if your app instance is located elsewhere.
# from backend.server import app # This would be for integration-style tests with TestClient
# For unit testing the router directly, we mock its dependencies.

from app.routers.vocabulary_ai import router as vocabulary_ai_router # Import the router instance
from models import EnrichedWordDetailsResponse, SynonymsAntonyms
from app.models import (
    UserVocabularyItemResponse, # Should this be User model for current_user?
    User, # For get_current_active_user dependency typing
    MoreExamplesRequest, MoreExamplesResponse, # New models for on-demand
    ELI5Request, ELI5Response,
    MiniQuizRequest, MiniQuizResponse, MiniQuizQuestion
)
from app.services.ai_enrichment_service import (
    get_or_create_enriched_details_service,
    generate_more_examples, # New service function for on-demand
    explain_like_i_am_five,
    generate_mini_quiz
)
from app.feedback_engine import FeedbackEngine # For dependency mocking

# Use pytest-asyncio for async tests
pytestmark = pytest.mark.asyncio

# Test data
TEST_ITEM_ID = uuid.uuid4()
TEST_USER_ID_STR = str(uuid.uuid4())
TEST_USER_ID_UUID = uuid.UUID(TEST_USER_ID_STR)
TEST_LANGUAGE = "en"

MOCK_ENRICHED_RESPONSE = EnrichedWordDetailsResponse(
    id=uuid.uuid4(),
    word_vocabulary_id=TEST_ITEM_ID,
    language=TEST_LANGUAGE,
    ai_example_sentences=["Example 1.", "Example 2."],
    synonyms_antonyms=SynonymsAntonyms(synonyms=["similar"], antonyms=["opposite"]),
    related_phrases=["Related phrase 1"],
    cultural_note="A cultural note.",
    emotion_tone="Neutral",
    mnemonic="A mnemonic."
)

# To test the router in isolation, we typically use FastAPI's TestClient
# However, since we are unit testing the router's functions more directly here by calling them,
# we will extensively use patching. For a more integrated test, TestClient with app overrides is better.

@pytest.fixture
def mock_request_valid_user() -> Request:
    mock = AsyncMock(spec=Request)
    mock.headers = {"X-User-ID": TEST_USER_ID_STR}
    return mock

@pytest.fixture
def mock_request_invalid_user_format() -> Request:
    mock = AsyncMock(spec=Request)
    mock.headers = {"X-User-ID": "not-a-uuid"}
    return mock

@pytest.fixture
def mock_request_no_user() -> Request:
    mock = AsyncMock(spec=Request)
    mock.headers = {}
    return mock


async def test_get_enriched_details_success(mock_request_valid_user: Request):
    with patch("app.routers.vocabulary_ai.get_or_create_enriched_details_service", new_callable=AsyncMock) as mock_service:
        mock_service.return_value = MOCK_ENRICHED_RESPONSE
        
        from app.routers.vocabulary_ai import get_enriched_vocabulary_item_details

        # When unit testing the endpoint function, we pass the resolved dependency directly.
        response = await get_enriched_vocabulary_item_details(
            item_id=TEST_ITEM_ID,
            language=TEST_LANGUAGE,
            request=mock_request_valid_user, # request is still needed if the function uses it for other things
            user_id=TEST_USER_ID_UUID  # Pass the resolved UUID directly
        )

        assert response == MOCK_ENRICHED_RESPONSE
        mock_service.assert_called_once_with(
            item_id=TEST_ITEM_ID,
            user_id=TEST_USER_ID_UUID,
            language=TEST_LANGUAGE
        )
        # The direct call to get_user_id_from_request is no longer made from within this test's scope for this specific path,
        # as its resolution is handled by FastAPI's Depends. We test get_user_id_from_request separately.


async def test_get_enriched_details_service_raises_http_404(mock_request_valid_user: Request):
    with patch("app.routers.vocabulary_ai.get_or_create_enriched_details_service", new_callable=AsyncMock) as mock_service:
        mock_service.side_effect = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
        
        from app.routers.vocabulary_ai import get_enriched_vocabulary_item_details

        with pytest.raises(HTTPException) as exc_info:
            await get_enriched_vocabulary_item_details(
                item_id=TEST_ITEM_ID,
                language=TEST_LANGUAGE,
                request=mock_request_valid_user,
                user_id=TEST_USER_ID_UUID # Pass resolved UUID
            )
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


async def test_get_enriched_details_invalid_user_id_format(mock_request_invalid_user_format: Request):
    from app.routers.vocabulary_ai import get_enriched_vocabulary_item_details, get_user_id_from_request
    # Test the get_user_id_from_request dependency directly
    with pytest.raises(HTTPException) as exc_info:
        await get_user_id_from_request(mock_request_invalid_user_format)
    
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc_info.value.detail == "Invalid User ID format. Must be a valid UUID."


async def test_get_enriched_details_no_user_id_header(mock_request_no_user: Request):
    from app.routers.vocabulary_ai import get_user_id_from_request
    with pytest.raises(HTTPException) as exc_info:
        await get_user_id_from_request(mock_request_no_user)
        
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "User ID not provided or authentication failed"

async def test_get_enriched_details_service_raises_generic_exception(mock_request_valid_user: Request):
    with patch("app.routers.vocabulary_ai.get_or_create_enriched_details_service", new_callable=AsyncMock) as mock_service:
        mock_service.side_effect = Exception("Some generic error") # A non-HTTPException

        from app.routers.vocabulary_ai import get_enriched_vocabulary_item_details

        with pytest.raises(HTTPException) as exc_info:
            await get_enriched_vocabulary_item_details(
                item_id=TEST_ITEM_ID,
                language=TEST_LANGUAGE,
                request=mock_request_valid_user,
                user_id=TEST_USER_ID_UUID # Pass resolved UUID
            )
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# Note: For more thorough testing involving the full FastAPI app stack (middleware, dependency injection resolution by FastAPI),
# you would use TestClient:
# from fastapi.testclient import TestClient
# from backend.server import app # Your main app
# client = TestClient(app)
# response = client.get(f"/ai/vocabulary/{TEST_ITEM_ID}/enrich?language={TEST_LANGUAGE}", headers={"X-User-ID": TEST_USER_ID_STR})
# This approach tests integration. The current tests are more unit-focused on the router logic. 

# --- Tests for On-Demand AI Generation Endpoints ---

TEST_ON_DEMAND_WORD = "flabbergasted"
TEST_ON_DEMAND_LANG = "en"

@pytest.fixture
def mock_generate_more_examples_service():
    mock = AsyncMock(return_value=MoreExamplesResponse(new_example_sentences=["Example A", "Example B"]))
    return mock

@pytest.fixture
def mock_explain_like_i_am_five_service():
    mock = AsyncMock(return_value=ELI5Response(explanation="It means very surprised!"))
    return mock

@pytest.fixture
def mock_generate_mini_quiz_service():
    mock = AsyncMock(return_value=MiniQuizResponse(
        quiz_title="Quick Quiz!", 
        questions=[MiniQuizQuestion(question_text="What?", options=["1", "2"], correct_answer_index=0, explanation="Easy one.")]
    ))
    return mock

# --- Test: /on-demand/more-examples --- 

@patch("app.routers.vocabulary_ai.generate_more_examples") # Patch where it's used
async def test_get_more_examples_success(
    mock_generate_examples_svc,
    client: AsyncClient, 
    mock_get_current_active_user: User # Use the existing fixture
):
    mock_generate_examples_svc.return_value = MoreExamplesResponse(new_example_sentences=["New example 1", "New example 2"])
    app.dependency_overrides[get_current_active_user] = lambda: mock_get_current_active_user
    # No need to override get_feedback_engine if we are mocking the service function directly

    payload = MoreExamplesRequest(word=TEST_ON_DEMAND_WORD, language=TEST_ON_DEMAND_LANG).model_dump()
    response = await client.post("/ai/vocabulary/on-demand/more-examples", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["new_example_sentences"] == ["New example 1", "New example 2"]
    mock_generate_examples_svc.assert_called_once()
    # Check arguments passed to the service call if necessary
    call_args = mock_generate_examples_svc.call_args[0] # First positional arg is a tuple
    assert isinstance(call_args[0].request, MoreExamplesRequest)
    assert call_args[0].request.word == TEST_ON_DEMAND_WORD
    del app.dependency_overrides[get_current_active_user]

@patch("app.routers.vocabulary_ai.generate_more_examples")
async def test_get_more_examples_service_http_exception(
    mock_generate_examples_svc,
    client: AsyncClient, 
    mock_get_current_active_user: User
):
    mock_generate_examples_svc.side_effect = HTTPException(status_code=429, detail="Rate limit hit")
    app.dependency_overrides[get_current_active_user] = lambda: mock_get_current_active_user
    
    payload = MoreExamplesRequest(word=TEST_ON_DEMAND_WORD, language=TEST_ON_DEMAND_LANG).model_dump()
    response = await client.post("/ai/vocabulary/on-demand/more-examples", json=payload)
    
    assert response.status_code == 429
    assert response.json()["detail"] == "Rate limit hit"
    del app.dependency_overrides[get_current_active_user]

@patch("app.routers.vocabulary_ai.generate_more_examples")
async def test_get_more_examples_service_generic_exception(
    mock_generate_examples_svc,
    client: AsyncClient, 
    mock_get_current_active_user: User
):
    mock_generate_examples_svc.side_effect = Exception("Unexpected AI error")
    app.dependency_overrides[get_current_active_user] = lambda: mock_get_current_active_user

    payload = MoreExamplesRequest(word=TEST_ON_DEMAND_WORD, language=TEST_ON_DEMAND_LANG).model_dump()
    response = await client.post("/ai/vocabulary/on-demand/more-examples", json=payload)

    assert response.status_code == 500
    assert "Failed to generate more examples: Unexpected AI error" in response.json()["detail"]
    del app.dependency_overrides[get_current_active_user]

# --- Test: /on-demand/eli5 --- 

@patch("app.routers.vocabulary_ai.explain_like_i_am_five")
async def test_get_eli5_success(
    mock_eli5_svc,
    client: AsyncClient, 
    mock_get_current_active_user: User
):
    mock_eli5_svc.return_value = ELI5Response(explanation="Super simple stuff.")
    app.dependency_overrides[get_current_active_user] = lambda: mock_get_current_active_user

    payload = ELI5Request(term=TEST_ON_DEMAND_WORD, language=TEST_ON_DEMAND_LANG).model_dump()
    response = await client.post("/ai/vocabulary/on-demand/eli5", json=payload)

    assert response.status_code == 200
    assert response.json()["explanation"] == "Super simple stuff."
    mock_eli5_svc.assert_called_once()
    del app.dependency_overrides[get_current_active_user]

# --- Test: /on-demand/mini-quiz --- 

@patch("app.routers.vocabulary_ai.generate_mini_quiz")
async def test_get_mini_quiz_success(
    mock_quiz_svc,
    client: AsyncClient, 
    mock_get_current_active_user: User
):
    quiz_response_data = MiniQuizResponse(
        quiz_title="Test Quiz", 
        questions=[MiniQuizQuestion(question_text="Q?", options=["Opt1"], correct_answer_index=0, explanation="Expl.")]
    )
    mock_quiz_svc.return_value = quiz_response_data
    app.dependency_overrides[get_current_active_user] = lambda: mock_get_current_active_user

    payload = MiniQuizRequest(word=TEST_ON_DEMAND_WORD, language=TEST_ON_DEMAND_LANG).model_dump()
    response = await client.post("/ai/vocabulary/on-demand/mini-quiz", json=payload)

    assert response.status_code == 200
    assert response.json() == quiz_response_data.model_dump()
    mock_quiz_svc.assert_called_once()
    del app.dependency_overrides[get_current_active_user]

# Add similar tests for HTTPException and generic Exception for ELI5 and MiniQuiz endpoints.

@patch("app.routers.vocabulary_ai.explain_like_i_am_five")
async def test_get_eli5_service_http_exception(
    mock_eli5_svc,
    client: AsyncClient, 
    mock_get_current_active_user: User
):
    mock_eli5_svc.side_effect = HTTPException(status_code=403, detail="Forbidden action")
    app.dependency_overrides[get_current_active_user] = lambda: mock_get_current_active_user
    payload = ELI5Request(term=TEST_ON_DEMAND_WORD, language=TEST_ON_DEMAND_LANG).model_dump()
    response = await client.post("/ai/vocabulary/on-demand/eli5", json=payload)
    assert response.status_code == 403
    assert response.json()["detail"] == "Forbidden action"
    del app.dependency_overrides[get_current_active_user]

@patch("app.routers.vocabulary_ai.explain_like_i_am_five")
async def test_get_eli5_service_generic_exception(
    mock_eli5_svc,
    client: AsyncClient, 
    mock_get_current_active_user: User
):
    mock_eli5_svc.side_effect = Exception("ELI5 AI craaash")
    app.dependency_overrides[get_current_active_user] = lambda: mock_get_current_active_user
    payload = ELI5Request(term=TEST_ON_DEMAND_WORD, language=TEST_ON_DEMAND_LANG).model_dump()
    response = await client.post("/ai/vocabulary/on-demand/eli5", json=payload)
    assert response.status_code == 500
    assert "Failed to generate ELI5 explanation: ELI5 AI craaash" in response.json()["detail"]
    del app.dependency_overrides[get_current_active_user]

@patch("app.routers.vocabulary_ai.generate_mini_quiz")
async def test_get_mini_quiz_service_http_exception(
    mock_quiz_svc,
    client: AsyncClient, 
    mock_get_current_active_user: User
):
    mock_quiz_svc.side_effect = HTTPException(status_code=503, detail="Service Unavailable")
    app.dependency_overrides[get_current_active_user] = lambda: mock_get_current_active_user
    payload = MiniQuizRequest(word=TEST_ON_DEMAND_WORD, language=TEST_ON_DEMAND_LANG).model_dump()
    response = await client.post("/ai/vocabulary/on-demand/mini-quiz", json=payload)
    assert response.status_code == 503
    assert response.json()["detail"] == "Service Unavailable"
    del app.dependency_overrides[get_current_active_user]

@patch("app.routers.vocabulary_ai.generate_mini_quiz")
async def test_get_mini_quiz_service_generic_exception(
    mock_quiz_svc,
    client: AsyncClient, 
    mock_get_current_active_user: User
):
    mock_quiz_svc.side_effect = Exception("Quiz AI went on break")
    app.dependency_overrides[get_current_active_user] = lambda: mock_get_current_active_user
    payload = MiniQuizRequest(word=TEST_ON_DEMAND_WORD, language=TEST_ON_DEMAND_LANG).model_dump()
    response = await client.post("/ai/vocabulary/on-demand/mini-quiz", json=payload)
    assert response.status_code == 500
    assert "Failed to generate mini-quiz: Quiz AI went on break" in response.json()["detail"]
    del app.dependency_overrides[get_current_active_user] 