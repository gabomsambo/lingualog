"""
Test script for the LinguaLog API.
"""
import requests
import json

def test_api():
    """Test the LinguaLog API."""
    url = "http://localhost:8000/log-entry"
    
    # Example journal entry
    payload = {
        "text": "Je suis allé au magasin hier et j'ai acheté du pain.",
        "target_language": "French",
        "user_id": "test-user"
    }
    
    # Make the request
    try:
        response = requests.post(url, json=payload, timeout=60)
        
        # Check the response
        if response.status_code == 200:
            result = response.json()
            print("API test successful!")
            print(json.dumps(result, indent=2))
        else:
            print(f"API request failed with status code: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Error testing API: {e}")

if __name__ == "__main__":
    test_api() 