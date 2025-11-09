# How to Interact with the Multi-Agent Brain

**Author**: @knowledge-weaver
**Date**: 2025-11-07
**Status**: Final

## 1. Overview

This guide explains the correct method for interacting with the `multi-agent-brain` system. While the OpenAgents Studio UI (available at `http://localhost:8050`) is useful for monitoring the health and activity of the agent network, it is not designed for direct user interaction.

All interactions, such as sending a question or a task to the agents, must be done programmatically by sending HTTP requests to the agent network service. This guide provides a step-by-step walkthrough using the provided `tests/tools/network_smoke.py` script as an example.

## 2. The Programmatic Interaction Flow

The `multi-agent-brain` system exposes an API that allows external clients to communicate with the agent network. The primary interaction script, `network_smoke.py`, demonstrates the three key steps required for a successful interaction:

1.  **Registration**: Your script or application must first register itself with the network to receive a temporary, unique identity (`agent_id`) and a secret for authentication.
2.  **Send Message**: Once registered, your script can send a message (an "event") to a specific channel within the network.
3.  **Unregistration**: After the interaction is complete, your script should unregister itself to clean up its session.

## 3. Running the Example Script

The `tests/tools/network_smoke.py` script is the best way to understand and test the interaction flow.

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
    python -m tests.tools.network_smoke
    ```
3.  **Observe the output**. The script will print its progress for each of the three steps: registration, sending the message, and unregistration. You will see the payload being sent and the full JSON response from the agent network.

## 4. Understanding the Code in `network_smoke.py`

`network_smoke.py` is organised into small helper functions so that importing the
module does not immediately trigger HTTP calls. Each helper mirrors one stage of
the interaction flow.

### Registration (`register_agent`)

```python
secret = register_agent(agent_id, base_url=args.base_url)
```

-   Generates a unique `agent_id` and issues a `POST /register` request.
-   Raises an exception if the network rejects the registration or omits the
    secret.
-   Returns the secret that must accompany all subsequent calls.

### Sending the Message (`send_message`)

```python
payload, response = send_message(
    agent_id,
    secret,
    message_text=args.message,
    target_channel=args.channel,
    base_url=args.base_url,
)
```

-   Builds the JSON payload (`source_id`, `target_agent_id`, `payload.text`,
    `secret`).
-   Posts the payload to `/send_event` and returns both the payload and the JSON
    response for inspection.

### Unregistration (`unregister_agent`)

```python
unregister_agent(agent_id, secret, base_url=args.base_url)
```

-   Sends a final `POST /unregister` request to clean up the temporary agent.
-   Executed inside a `finally` block so cleanup happens even if message sending
    fails.

### Putting everything together (`run_smoke_test`)

```python
result = run_smoke_test(
    message_text=args.message,
    target_channel=args.channel,
    base_url=args.base_url,
)
```

-   Coordinates registration, message sending, and unregistration.
-   Returns a structured `SmokeTestResult` containing the payload, response JSON,
    and any data returned during cleanup.
-   The CLI entry point (`main`) exposes `--channel`, `--base-url`, and
    `--quiet` flags so you can experiment without modifying the code.

## 5. How the System Routes Your Message

Understanding the message flow helps clarify why the script is structured the way it is.

1.  **Entry Point (`general` channel)**: Your message is sent to the `general` channel, which is a public-facing channel handled by the `GeneralAgent`.
2.  **Escalation (`coordination` channel)**: The `GeneralAgent` is configured to immediately escalate all incoming messages to the `coordination` channel.
3.  **Orchestration (`CoordinationAgent`)**: The `CoordinationAgent` receives the message from the `coordination` channel. It analyzes the content of your message (e.g., "What is Milvus?") and intelligently routes it to the most appropriate specialist agent, such as the `PythonExpertAgent` or `MilvusExpertAgent`.
4.  **Response**: The specialist agent processes the request, generates a response, and the final reply is sent back to your script.

This structured, programmatic approach ensures that all interactions are authenticated, correctly routed, and handled by the agent best equipped for the task.