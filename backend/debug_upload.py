import requests

BASE_URL = "http://localhost:8000"

def test_upload():
    # 1. Login
    print("Logging in...")
    response = requests.post(f"{BASE_URL}/auth/token", data={
        "username": "admin@example.com",
        "password": "admin123"
    })
    token = response.json().get("access_token")
    if not token:
        print("Login failed")
        return
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Upload
    print("Uploading file...")
    # Create dummy file
    with open("debug_test.txt", "w") as f:
        f.write("Debug content")
        
    files = {'file': ('debug_test.txt', open('debug_test.txt', 'rb'), 'text/plain')}
    
    # We do NOT set Content-Type header here, requests handles it with boundary
    try:
        response = requests.post(f"{BASE_URL}/ingest/file", headers=headers, files=files)
        if response.status_code != 200:
            try:
                detail = response.json()['detail']
                with open("error_detail.txt", "w") as f:
                    f.write(detail)
                print("Error detail written to error_detail.txt")
            except:
                with open("error_raw.txt", "w") as f:
                    f.write(response.text)
                print("Raw error written to error_raw.txt")
        else:
            print(f"Success: {response.json()}")
            
            # 3. Chat
            print("Testing chat retrieval...")
            chat_response = requests.post(f"{BASE_URL}/chat", headers=headers, json={"question": "What is the content of the debug file?", "thread_id": "test_thread"})
            if chat_response.status_code == 200:
                print(f"Chat Response: {chat_response.json()}")
            else:
                with open("error_detail_chat.txt", "w") as f:
                    f.write(chat_response.text)
                print(f"Chat Failed: See error_detail_chat.txt")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_upload()
