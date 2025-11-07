# How to Interact with the Multi-Agent Brain

**Author**: @knowledge-weaver
**Date**: 2025-11-07
**Status**: Final

## 1. Overview

This guide explains the correct method for interacting with the `multi-agent-brain` system. While the OpenAgents Studio UI (available at `http://localhost:8050`) is useful for monitoring the health and activity of the agent network, it is not designed for direct user interaction.

All interactions, such as sending a question or a task to the agents, must be done programmatically by sending HTTP requests to the agent network service. This guide provides a step-by-step walkthrough using the provided `simple_test.py` script as an example.

## 2. The Programmatic Interaction Flow

The `multi-agent-brain` system exposes an API that allows external clients to communicate with the agent network. The primary interaction script, `simple_test.py`, demonstrates the three key steps required for a successful interaction:

1.  **Registration**: Your script or application must first register itself with the network to receive a temporary, unique identity (`agent_id`) and a secret for authentication.
2.  **Send Message**: Once registered, your script can send a message (an "event") to a specific channel within the network.
3.  **Unregistration**: After the interaction is complete, your script should unregister itself to clean up its session.

## 3. Running the Example Script

The `simple_test.py` script is the best way to understand and test the interaction flow.

### Prerequisites

- The `multi-agent-brain` network must be running. You can start it with the command:
  ```bash
  openagents network http --config config.yaml
  ```
- You must have the required Python packages installed:
  ```bash
  pip install -r requirements.txt
  ```

### Step-by-Step Guide

1.  **Open a new terminal** in the root directory of the `multi-agent-brain` project.
2.  **Run the script** using the following command:
    ```bash
    python simple_test.py
    ```
3.  **Observe the output**. The script will print its progress for each of the three steps: registration, sending the message, and unregistration. You will see the payload being sent and the full JSON response from the agent network.

## 4. Understanding the Code in `simple_test.py`

The script is divided into three main parts, corresponding to the interaction flow.

### Part 1: Registration

```python
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
        # ...
```

-   **`AGENT_ID`**: A unique identifier is generated for this script instance.
-   **`requests.post(REGISTER_URL, ...)`**: A `POST` request is sent to the `/api/register` endpoint.
-   **`secret`**: If registration is successful, the network returns a `secret`. This secret must be included in all subsequent requests to authenticate the client.

### Part 2: Sending the Message

```python
# --- 2. Send Message Step ---
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

response = requests.post(
    SEND_EVENT_URL,
    headers={"Content-Type": "application/json"},
    json=event_payload
)
```

-   **`target_channel = "general"`**: The message is sent to the `general` channel. As explained in the technical specification, this is the public entry point for all user interactions.
-   **`event_payload`**: A JSON payload is constructed.
    -   `source_id`: The `AGENT_ID` from the registration step.
    -   `target_agent_id`: The `general` channel.
    -   `payload`: The actual message content is placed inside `payload.text`.
    -   `secret`: The secret received during registration is included for authentication.
-   **`requests.post(SEND_EVENT_URL, ...)`**: The payload is sent as a `POST` request to the `/api/send_event` endpoint.

### Part 3: Unregistration

```python
# --- 3. Unregistration Step (Cleanup) ---
if secret:
    print(f"\n--- 3. Unregistering Agent '{AGENT_ID}' ---")
    try:
        unreg_response = requests.post(UNREGISTER_URL, json={"agent_id": AGENT_ID, "secret": secret})
        # ...
```

-   This final step is crucial for cleanup. It sends a `POST` request to the `/api/unregister` endpoint, including the `AGENT_ID` and the `secret`, to invalidate the session.

## 5. How the System Routes Your Message

Understanding the message flow helps clarify why the script is structured the way it is.

1.  **Entry Point (`general` channel)**: Your message is sent to the `general` channel, which is a public-facing channel handled by the `GeneralAgent`.
2.  **Escalation (`coordination` channel)**: The `GeneralAgent` is configured to immediately escalate all incoming messages to the `coordination` channel.
3.  **Orchestration (`CoordinationAgent`)**: The `CoordinationAgent` receives the message from the `coordination` channel. It analyzes the content of your message (e.g., "What is Milvus?") and intelligently routes it to the most appropriate specialist agent, such as the `PythonExpertAgent` or `MilvusExpertAgent`.
4.  **Response**: The specialist agent processes the request, generates a response, and the final reply is sent back to your script.

This structured, programmatic approach ensures that all interactions are authenticated, correctly routed, and handled by the agent best equipped for the task.