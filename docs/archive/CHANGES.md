# Changes Summary: Fix Loguru agent_id KeyError
> [!WARNING] **Archived:** This document is retained for historical context and may be outdated. See [Documentation Hub](../README.md) for current guidance.


## Issue
Fixed `KeyError: 'agent_id'` that occurred during agent network startup when running `run_demo.sh`. The error appeared in logging calls from:
- `agents/shared_memory.py` (lines 209, 234)
- `utils/openai_client.py` (lines 236, 413, 429)

## Root Cause
The Loguru logger format string in `demos/runner.py` required `{extra[agent_id]}` but most logging calls didn't provide this field in their `extra` dict.

## Solution
Added a filter function to `demos/runner.py` that automatically provides a default `agent_id` value ("system") for log records that don't have one. The filter also handles two logging patterns:
1. `.bind(agent_id="...")` - agent_id in top-level extra
2. `.info(..., extra={"agent_id": "..."})` - agent_id in nested extra

## Files Changed

### Modified: `demos/runner.py`
**Lines 399-422**: Added `add_default_agent_id()` filter function and applied it to the logger configuration.

**Before:**
```python
# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{extra[agent_id]}</cyan> | <level>{message}</level>",
    level="INFO"
)
```

**After:**
```python
# Configure logging with default agent_id for records that don't have it
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

### Added: `test_loguru_fix.py`
Comprehensive test script that verifies:
- No KeyError occurs for logs without agent_id
- Logs with explicit agent_id show correctly
- Logs using `.bind()` show correctly
- All problematic log locations work without errors

### Added: `LOGURU_FIX.md`
Documentation explaining the issue, root cause, solution, and usage examples.

## Testing
Run the test script to verify the fix:
```bash
python test_loguru_fix.py
```

Expected output:
```
✅ ALL TESTS PASSED
✅ No KeyError: 'agent_id' messages on agent network startup
✅ All agents initialize successfully with clean console output
✅ Loguru format string is properly configured
✅ All logging calls complete successfully
```

## Acceptance Criteria Met
- ✅ No `KeyError: 'agent_id'` messages on agent network startup
- ✅ All agents initialize successfully with clean console output
- ✅ Loguru format string is properly configured
- ✅ All logging calls complete successfully

## Impact
- **Non-breaking**: Existing code continues to work without modification
- **Backward compatible**: Supports both `.bind()` and `.info(..., extra={...})` patterns
- **Default behavior**: Logs without agent_id automatically use "system" as the default
- **Clean output**: No more logging errors during agent initialization

## Example Log Output

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
2025-11-08 07:11:34 | INFO     | coordination | Processing request
```
