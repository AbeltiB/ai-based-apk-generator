import requests
import json

def test_service():
    """Simple test to verify service is running."""
    url = "http://localhost:8000"
    
    print("Testing AI Service...")
    
    # Test health endpoint
    try:
        response = requests.get(f"{url}/health", timeout=5)
        print(f"✅ Health check: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Status: {data.get('status')}")
            print(f"   Version: {data.get('version')}")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to service. Is it running?")
        print("\nStart the service with:")
        print("   poetry run uvicorn app.main:app --reload")
        return False
    
    # Test generation endpoint
    try:
        test_data = {
            "prompt": "Create a simple counter app",
            "user_id": "test_user",
            "session_id": "test_session_1",
            "priority": 1
        }
        response = requests.post(f"{url}/api/v1/generate", json=test_data, timeout=30)
        print(f"✅ Generation test: {response.status_code}")
        if response.status_code == 202:
            data = response.json()
            print(f"   Task ID: {data.get('task_id')}")
            print(f"   Message: {data.get('message')}")
            return True
        else:
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Generation test failed: {e}")
        return False

if __name__ == "__main__":
    test_service()