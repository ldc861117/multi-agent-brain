# Loguru agent_id KeyError Fix
> [!WARNING] **Archived:** This document is retained for historical context and may be outdated. See [Documentation Hub](../README.md) for current guidance.


## Issue

When running `run_demo.sh`, the agent network startup was producing repeated Loguru logging errors:

```
KeyError: 'agent_id'
```

These errors occurred in:
- `agents/shared_memory.py` (lines 209, 234)
- `utils/openai_client.py` (lines 236, 413, 429)

The agents initialized successfully despite these errors, indicating this was a non-fatal logging configuration issue.

## Root Cause

The Loguru format string in `demos/runner.py` (line 403) included a `{extra[agent_id]}` placeholder:

```python
format="... | <cyan>{extra[agent_id]}</cyan> | ..."
```

However, most logging calls in the codebase did not include `agent_id` in their `extra` fields:

```python
logger.info(
    "Shared memory initialized",
    extra={
        "milvus_uri": self.milvus_uri,
        "embedding_model": self.embedding_model,
        # No agent_id!
    }
)
```

When Loguru tried to format the log message, it looked for `record['extra']['agent_id']` which didn't exist, causing a `KeyError`.

## Solution

Added a filter function `add_default_agent_id()` to the logger configuration that:

1. **Checks for agent_id in top-level extra** (from `.bind()` usage):
   ```python
   if "agent_id" in record["extra"]:
       return True
   ```

2. **Checks for agent_id in nested extra** (from `.info(..., extra={...})` usage):
   ```python
   if "extra" in record["extra"] and "agent_id" in record["extra"]["extra"]:
       record["extra"]["agent_id"] = record["extra"]["extra"]["agent_id"]
       return True
   ```

3. **Provides a default value** if agent_id is not found:
   ```python
   record["extra"]["agent_id"] = "system"
   return True
   ```

## Implementation

The fix is in `demos/runner.py` lines 399-422:

```python
def add_default_agent_id(record):
    """Add default agent_id to log records that don't have one."""
    # Check if agent_id is in the top-level extra (from .bind())
    if "agent_id" in record["extra"]:
        return True
    
    # Check if agent_id is in nested extra (from .info(..., extra={...}))
    if "extra" in record["extra"] and "agent_id" in record["extra"]["extra"]:
        # Promote it to top-level for the format string
        record["extra"]["agent_id"] = record["extra"]["extra"]["agent_id"]
        return True
    
    # No agent_id found, set default
    record["extra"]["agent_id"] = "system"
    return True

logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{extra[agent_id]}</cyan> | <level>{message}</level>",
    level="INFO",
    filter=add_default_agent_id
)
```

## Testing

Run the test script to verify the fix:

```bash
python test_loguru_fix.py
```

This tests:
- Logs without agent_id (default to "system")
- Logs with explicit agent_id in extra dict
- Logs using `.bind()` for agent context
- All problematic log locations from the issue

## Result

✅ No `KeyError: 'agent_id'` messages on agent network startup  
✅ All agents initialize successfully with clean console output  
✅ Loguru format string is properly configured  
✅ All logging calls complete successfully  

### Before Fix
```
--- Logging error in Loguru Handler #1 ---
KeyError: 'agent_id'
--- End of logging error ---
```

### After Fix
```
2025-11-08 07:11:34 | INFO     | system | Shared memory initialized
2025-11-08 07:11:34 | INFO     | system | Connected to Milvus
2025-11-08 07:11:34 | INFO     | system | OpenAI client wrapper initialized
2025-11-08 07:11:34 | INFO     | coordination | Agent processing request
```

## Future Recommendations

To use agent-specific logging:

```python
# Method 1: Use .bind() to set agent context
logger = logger.bind(agent_id="coordination")
logger.info("Processing message")  # Will show agent_id=coordination

# Method 2: Include agent_id in extra
logger.info("Processing message", extra={"agent_id": "coordination"})

# Method 3: Let it default to "system"
logger.info("Processing message")  # Will show agent_id=system
```
