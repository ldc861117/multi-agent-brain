import requests
import json
import uuid

# Define constants for the agent network
BASE_URL = "http://localhost:8700/api"
REGISTER_URL = f"{BASE_URL}/register"
SEND_EVENT_URL = f"{BASE_URL}/send_event"
UNREGISTER_URL = f"{BASE_URL}/unregister"

# --- 1. Registration Step ---
# A unique ID for our script instance to register with the network
AGENT_ID = f"simple-test-script-{uuid.uuid4()}"
secret = None

print(f"--- 1. Registering Agent '{AGENT_ID}' ---")
try:
    reg_response = requests.post(REGISTER_URL, json={"agent_id": AGENT_ID})
    reg_response.raise_for_status()
    reg_data = reg_response.json()
    
    if reg_data.get("success"):
        secret = reg_data.get("secret")
        if secret:
            print(f"✅ Registration successful. Got secret.")
        else:
            raise Exception("Registration successful, but no secret was provided.")
    else:
        raise Exception(f"Registration failed: {reg_data.get('error_message', 'Unknown error')}")

except requests.exceptions.RequestException as e:
    print(f"❌ Error during registration: {e}")
    exit() # Exit if we can't register

# --- 2. Send Message Step ---
print(f"\n--- 2. Sending Message ---")

message_text = "What is Milvus?"
target_channel = "general"

event_payload = {
    "event_id": f"event-{uuid.uuid4()}",
    "event_name": "user.message",
    "source_id": AGENT_ID,
    "target_agent_id": target_channel,
    "payload": {"text": message_text},
    "metadata": {},
    "secret": secret  # Include the secret for authentication
}

print("Payload:")
print(json.dumps(event_payload, indent=2))

try:
    response = requests.post(
        SEND_EVENT_URL,
        headers={"Content-Type": "application/json"},
        json=event_payload
    )
    response.raise_for_status()
    
    print("\n--- Agent Network Response ---")
    print(f"Status Code: {response.status_code}")
    response_json = response.json()
    print("Response JSON:")
    print(json.dumps(response_json, indent=2))

    if response_json.get('data'):
        print("\n--- Agent's Reply ---")
        print(json.dumps(response_json['data'], indent=2))
    else:
        print(f"\nNo direct agent reply in 'data' field. Message: {response_json.get('message')}")

except requests.exceptions.RequestException as e:
    print(f"\n--- Error ---")
    print(f"An error occurred while sending the message: {e}")

finally:
    # --- 3. Unregistration Step (Cleanup) ---
    if secret:
        print(f"\n--- 3. Unregistering Agent '{AGENT_ID}' ---")
        try:
            unreg_response = requests.post(UNREGISTER_URL, json={"agent_id": AGENT_ID, "secret": secret})
            unreg_response.raise_for_status()
            if unreg_response.json().get("success"):
                print("✅ Unregistration successful.")
            else:
                print(f"⚠️ Unregistration failed: {unreg_response.json().get('error_message')}")
        except requests.exceptions.RequestException as e:
            print(f"❌ Error during unregistration: {e}")