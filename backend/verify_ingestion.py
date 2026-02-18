import requests
import sys

BASE_URL = "http://localhost:8000"

def verify():
    # 1. Login
    print("Logging in...")
    response = requests.post(f"{BASE_URL}/auth/token", data={
        "username": "admin@example.com",
        "password": "admin123"
    })
    
    if response.status_code != 200:
        print(f"Login failed: {response.text}")
        sys.exit(1)
        
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Login successful.")
    
    # 2. Upload File
    print("Uploading file...")
    files = {'file': ('test_doc.txt', open('../test_doc.txt', 'rb'), 'text/plain')}
    response = requests.post(f"{BASE_URL}/ingest/file", headers=headers, files=files)
    
    if response.status_code != 200:
        print(f"Upload failed: {response.text}")
        sys.exit(1)
        
    print(f"Upload successful: {response.json()}")
    
    # 3. Chat
    print("Testing chat...")
    chat_payload = {
        "question": "Who is the lead engineer of Project Falcon?",
        "thread_id": "test_verification"
    }
    response = requests.post(f"{BASE_URL}/chat", headers=headers, json=chat_payload)
    
    if response.status_code != 200:
        print(f"Chat failed: {response.text}")
        sys.exit(1)
        
    answer = response.json().get("answer", "")
    print(f"Chat Answer: {answer}")
    
    if "Sarah Connor" in answer:
        print("VERIFICATION PASSED!")
    else:
        print("VERIFICATION FAILED: Answer did not contain expected content.")

if __name__ == "__main__":
    verify()
