# Self-Healing Retry Implementation - Complete

## Overview

Implemented a fully automated self-healing retry mechanism for OneController's Blender MCP integration. When Blender code execution fails, the system automatically:
1. Detects the error
2. Notifies the user ("Command failed. Adjusting...")
3. Sends error context to AI
4. AI analyzes the error and generates fixed code
5. Executes the fixed code automatically
6. Maximum 2 retry attempts

## Implementation Summary

### 1. MCP Server Error Handling (blender-mcp)

**File**: `D:\development\python\blender-mcp\src\blender_mcp\server.py`

**Changes**:
- **Lines 141-146**: Fixed `send_command` to return full response instead of raising exceptions
- **Lines 252-271**: Fixed `get_scene_info` to return error strings instead of raising
- **Lines 329-354**: Fixed `execute_blender_code` to return error strings instead of raising

**Result**: Errors now flow cleanly from Blender → MCP → Frontend → Backend without socket disconnection

### 2. Edge Function Types (Supabase)

**File**: `D:\development\supabase\one-controller-supabase\supabase\functions\detect-voice-command\types.ts`

**Changes**:
- **Lines 14-22**: Added `retry_context` parameter to `RequestBody` interface
- **Lines 17-22**: Added `RetryContext` interface with fields:
  - `previous_code`: The Python code that failed
  - `error_message`: Error from Blender
  - `attempt_number`: Retry attempt number (1, 2, 3...)
  - `original_command`: Original voice command

### 3. Edge Function Command Detection (Supabase)

**File**: `D:\development\supabase\one-controller-supabase\supabase\functions\detect-voice-command\command-detector.ts`

**Changes**:
- **Line 5**: Added `RetryContext` import
- **Lines 59-69**: Added `retryContext` parameter to `detectCommandWithAI` function
- **Lines 327-344**: Added retry context prompt injection that:
  - Shows previous failed code
  - Shows error message
  - Provides Blender-specific error hints:
    - "enum 'EDIT' not found" → Can't switch to EDIT mode on lights/cameras
    - "mesh.to_sphere()" → Requires EDIT mode AND mesh object
    - Context errors → Some operations need specific selection or mode
  - Instructs AI to generate FIXED code

### 4. Edge Function Main Handler (Supabase)

**File**: `D:\development\supabase\one-controller-supabase\supabase\functions\detect-voice-command\index.ts`

**Changes**:
- **Line 59**: Added `retry_context` to request body destructuring
- **Line 121**: Passed `retry_context` to `detectCommandWithAI`

**Deployment**: ✅ Successfully deployed to Supabase (project: icajylcaekqydjsbyssp)

### 5. Backend Command Detection Service

**File**: `D:\development\python\one_controller\backend\command_detection_service.py`

**Changes**:
- **Line 103**: Added `retry_context` parameter to `detect_command` method
- **Lines 199-203**: Added retry context to Edge Function payload:
  ```python
  if retry_context:
      payload["retry_context"] = retry_context
      logger.info(f"🔄 Retry attempt #{retry_context['attempt_number']}")
  ```

### 6. Backend Action Router

**File**: `D:\development\python\one_controller\backend\action_router.py`

**Changes**:
- **Line 12**: Added import: `from command_detection_service import get_command_detection_service`
- **Line 36**: Added `retry_attempt` parameter to `route_actions` method
- **Lines 86-126**: Added error detection and retry trigger logic:
  - Detects Blender code execution errors
  - Broadcasts "Adjusting..." notification to user
  - Calls `_retry_with_ai_fix` method
  - Maximum 2 retries
- **Lines 254-351**: Added `_retry_with_ai_fix` method that:
  - Extracts previous code from action parameters
  - Builds retry_context dict
  - Calls Edge Function with error context
  - Recursively calls `route_actions` with fixed code
  - Returns result

## How It Works - End-to-End Flow

### Normal Flow (Success)
```
User: "transform cube to sphere"
  ↓
AI generates code → Blender executes → Success ✅
```

### Self-Healing Flow (Error → Retry → Success)
```
User: "transform cube to sphere"
  ↓
AI generates code: bpy.ops.mesh.to_sphere()
  ↓
Blender executes → ERROR: "enum 'EDIT' not found in ('OBJECT')"
  ↓
Backend detects error (action_router.py:86-126)
  ↓
User sees: "Command failed. Adjusting... (attempt 1/2)"
  ↓
Backend calls _retry_with_ai_fix (action_router.py:254-351)
  ↓
Builds retry_context:
{
  "previous_code": "bpy.ops.mesh.to_sphere()",
  "error_message": "enum 'EDIT' not found in ('OBJECT')",
  "attempt_number": 1,
  "original_command": "transform cube to sphere"
}
  ↓
Calls Edge Function with retry_context
  ↓
AI sees error context (command-detector.ts:327-344)
AI analyzes: "Ah, need to switch to EDIT mode first!"
AI generates FIXED code:
```python
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.to_sphere()
bpy.ops.object.mode_set(mode='OBJECT')
```
  ↓
Backend executes fixed code → Success ✅
  ↓
User sees: Success notification
```

## Testing Instructions

### Test Case 1: Simple Error (Edit Mode)
**Command**: "transform cube to sphere"

**Expected Behavior**:
1. First attempt fails with "enum 'EDIT' not found"
2. User sees "Command failed. Adjusting..."
3. AI fixes code by adding mode_set
4. Second attempt succeeds
5. Cube transforms to sphere

### Test Case 2: Complex Error (Multiple Issues)
**Command**: "make the light a sphere"

**Expected Behavior**:
1. First attempt fails (can't convert light to mesh)
2. User sees "Command failed. Adjusting..."
3. AI realizes lights can't become spheres
4. AI generates code to create new sphere instead
5. Second attempt succeeds

### Test Case 3: Unfixable Error (Max Retries)
**Command**: "do something impossible"

**Expected Behavior**:
1. First attempt fails
2. User sees "Command failed. Adjusting... (attempt 1/2)"
3. Second attempt fails
4. User sees error message
5. No third attempt (max 2 retries)

## Backend Logs to Monitor

When testing, watch for these log messages:

```python
# Error detection
🔧 Blender code execution failed. Attempting self-healing retry 1/2...

# Retry attempt
🔄 Attempting self-healing retry #1/2
Previous code: ...
Error message: ...

# AI call
🤖 Calling AI to analyze error and generate fixed code...
✅ AI generated fixed code for retry attempt #1

# Execution
🔄 Executing fixed code (retry #1/2)...
```

## Edge Function Logs to Monitor

In Supabase Dashboard → Functions → detect-voice-command → Logs:

```typescript
🔄 RETRY ATTEMPT 1: Previous code failed
⚠️ Your previous code for "transform cube to sphere" failed with this error:
Error Message: enum 'EDIT' not found in ('OBJECT')
IMPORTANT INSTRUCTIONS:
1. Analyze the error message carefully
2. Fix the code to avoid this specific error
...
```

## Files Modified

### blender-mcp Repository
1. `src/blender_mcp/server.py` - Fixed error handling

### one-controller-supabase Repository
2. `supabase/functions/detect-voice-command/types.ts` - Added RetryContext types
3. `supabase/functions/detect-voice-command/command-detector.ts` - Added retry logic
4. `supabase/functions/detect-voice-command/index.ts` - Added retry_context parameter

### one_controller Repository
5. `backend/command_detection_service.py` - Added retry_context parameter
6. `backend/action_router.py` - Added self-healing retry mechanism

## Configuration

No configuration changes required. The self-healing retry mechanism is automatically enabled for all Blender MCP commands.

**Max Retries**: 2 (configurable in action_router.py line 88)

## Known Limitations

1. **Only works for Blender MCP**: Currently only triggers for `blender-mcp` + `execute_blender_code` errors
2. **Max 2 retries**: After 2 failed attempts, gives up (prevents infinite loops)
3. **No persistent learning**: Each retry is independent, doesn't learn from past errors across sessions
4. **Code-only fixes**: Can only fix Python code errors, not Blender scene state issues

## Future Enhancements

1. **Extend to other MCP servers**: Apply same pattern to other error-prone MCP tools
2. **Increase max retries**: Make configurable per user/command type
3. **Error pattern database**: Build knowledge base of common errors and fixes
4. **Multi-step fixes**: Allow AI to request scene info before generating fix
5. **User feedback loop**: Let users approve/reject AI fixes before execution

## Success Metrics

The implementation is successful if:
- ✅ MCP errors no longer cause socket timeouts
- ✅ Users see clear error notifications
- ✅ Simple errors (like mode switching) are automatically fixed
- ✅ Backend logs show retry attempts with fixed code
- ✅ Overall Blender command success rate increases by >30%

## Deployment Status

- ✅ MCP server changes: Committed (needs rebuild/reinstall)
- ✅ Edge Function: Deployed to Supabase production
- ✅ Backend changes: Implemented (needs restart)

## Next Steps

1. **Restart OneController backend** to load new action_router.py
2. **Test with known failing commands** (e.g., "transform cube to sphere")
3. **Monitor logs** for retry attempts and success rates
4. **Iterate on AI prompt** if common errors not fixed correctly
5. **Extend to other MCP servers** if pattern proves successful
