# Quick Test Guide - Self-Healing Retry

## Prerequisites

1. ✅ Edge Function deployed (already done)
2. ⚠️ **Restart OneController backend** to load new code:
   ```
   Stop the backend process
   Restart it
   ```

## Test 1: Basic Self-Healing (Should Auto-Fix)

### Command
Say: **"transform cube to sphere"**

### Expected Sequence

1. **Initial Attempt** (fails):
   - Blender console shows: `Error in handler: Code execution error: enum 'EDIT' not found in ('OBJECT')`
   - OneController shows: "Command failed. Adjusting... (attempt 1/2)"

2. **AI Retry** (auto-fixes):
   - Backend log shows: `🔄 Attempting self-healing retry #1/2`
   - Backend log shows: `🤖 Calling AI to analyze error and generate fixed code...`
   - Backend log shows: `✅ AI generated fixed code for retry attempt #1`

3. **Fixed Execution** (succeeds):
   - Blender console shows: `Executing handler for execute_code` (second time)
   - Cube transforms to sphere ✅
   - OneController shows success

### What to Watch

**OneController Backend Logs**:
```
🔧 Blender code execution failed. Attempting self-healing retry 1/2...
🔄 Attempting self-healing retry #1/2
Previous code:
bpy.ops.mesh.to_sphere()

Error message: enum 'EDIT' not found in ('OBJECT')
🤖 Calling AI to analyze error and generate fixed code...
✅ AI generated fixed code for retry attempt #1
🔄 Executing fixed code (retry #1/2)...
```

**Blender Console**:
```
Executing handler for execute_code
Error in handler: Code execution error: enum 'EDIT' not found in ('OBJECT')
Client disconnected  # First attempt fails

Executing handler for execute_code  # Retry with fixed code
Handler completed successfully  # Second attempt succeeds ✅
```

## Test 2: Verify Max Retries (Should Give Up After 2)

### Setup
Create an impossible command that can't be fixed.

### Command
Say: **"convert the default cube into a living cat"**

### Expected Sequence
1. First attempt fails
2. Shows "Adjusting... (attempt 1/2)"
3. Second attempt fails
4. Shows "Adjusting... (attempt 2/2)"
5. Final error message
6. **No third attempt**

## Test 3: Verify Normal Commands Still Work

### Command
Say: **"add a three point lighting setup"**

### Expected
- Should work on first attempt (no error, no retry)
- Logs should NOT show retry attempts
- Three lights added to scene ✅

## Common Issues & Solutions

### Issue: "Command failed" but no retry
**Cause**: Backend not restarted with new code
**Solution**: Stop and restart OneController backend

### Issue: Retry happens but same error
**Cause**: AI not understanding error context
**Solution**: Check Edge Function logs in Supabase dashboard to see AI's reasoning

### Issue: Socket timeout (30 seconds)
**Cause**: MCP server still raising exceptions (old code)
**Solution**: Rebuild and reinstall blender-mcp addon

### Issue: No error detection
**Cause**: Error message format changed
**Solution**: Check action_router.py line 98-100 for error extraction logic

## Viewing Logs

### OneController Backend
Watch the terminal where backend is running for:
- `🔧 Blender code execution failed`
- `🔄 Attempting self-healing retry`
- `🤖 Calling AI to analyze error`
- `✅ AI generated fixed code`

### Blender Console
Window → Toggle System Console (Windows)
Watch for:
- `Error in handler: Code execution error:`
- `Client disconnected` (indicates error)
- Second `Executing handler for execute_code` (indicates retry)

### Edge Function (Supabase)
https://supabase.com/dashboard/project/icajylcaekqydjsbyssp/functions
Click "detect-voice-command" → Logs tab
Watch for:
- `🔄 RETRY ATTEMPT 1: Previous code failed`
- `⚠️ Your previous code for "..." failed with this error:`
- `IMPORTANT INSTRUCTIONS: 1. Analyze the error message carefully`

## Success Criteria

✅ Self-healing is working if:
1. "transform cube to sphere" fails first, then succeeds automatically
2. User sees "Adjusting..." notification between attempts
3. Blender console shows two executions (first fails, second succeeds)
4. Backend logs show retry attempt with fixed code
5. No more 30-second socket timeouts

## Quick Debug Commands

```bash
# Check if backend has new code
grep "_retry_with_ai_fix" "D:\development\python\one_controller\backend\action_router.py"

# Check Edge Function deployment
cd "D:\development\supabase\one-controller-supabase"
supabase functions list

# Check if retry_context in Edge Function types
grep "retry_context" "D:\development\supabase\one-controller-supabase\supabase\functions\detect-voice-command\types.ts"
```

## Report Results

After testing, note:
1. Which commands auto-fixed successfully? ✅
2. Which commands failed even after retry? ❌
3. Any unexpected behavior? 🤔
4. Backend log snippets showing retry flow
5. Blender console showing before/after
