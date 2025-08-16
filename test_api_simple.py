"""Simple API test to debug the issue."""
import requests
import json

# Test Grok API
def test_grok_api():
    print("Testing Grok API...")
    
    # You'll need to replace this with your actual API key
    api_key = "your_grok_key_here"  # Replace with actual key
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "grok-2-1212",
        "messages": [
            {"role": "user", "content": "Say hello in one word."}
        ],
        "max_tokens": 10
    }
    
    try:
        response = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data}")
        else:
            print(f"Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"Exception: {e}")

# Test Claude API  
def test_claude_api():
    print("\nTesting Claude API...")
    
    # You'll need to replace this with your actual API key
    api_key = "your_claude_key_here"  # Replace with actual key
    
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }
    
    payload = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 10,
        "messages": [
            {"role": "user", "content": "Say hello in one word."}
        ]
    }
    
    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data}")
        else:
            print(f"Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    print("API Test Script")
    print("Replace the API keys in this script with your actual keys to test")
    # Uncomment these lines after adding your API keys:
    # test_grok_api()
    # test_claude_api()
