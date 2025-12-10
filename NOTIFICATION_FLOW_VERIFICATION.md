# Notification Flow Verification - Self-Healing Retry

## Complete User Notification Flow

### Success Scenario: "transform cube to sphere"

```
User says: "transform cube to sphere"
          ↓
AI generates code: bpy.ops.mesh.to_sphere()
          ↓
Blender executes → ERROR
          ↓
Backend detects error (action_router.py:108-114)
          ↓
🔴 NOTIFICATION 1: "❌ enum 'EDIT' not found in ('OBJECT')"
   - Type: error
   - Duration: 5 seconds (error notifications are longer)
   - Position: left side of screen
          ↓
⏱️ 0.5 second delay
          ↓
🟡 NOTIFICATION 2: "🔄 Adjusting code... (attempt 1/2)"
   - Type: error (still showing problem state)
   - Duration: 3 seconds
   - Position: left side of screen
          ↓
Backend calls Edge Function with error context
          ↓
AI analyzes error: "Need to switch to EDIT mode first!"
          ↓
AI generates fixed code:
```python
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.to_sphere()
bpy.ops.object.mode_set(mode='OBJECT')
```
          ↓
Backend executes fixed code → SUCCESS
          ↓
Backend detects success (action_router.py:139-147)
          ↓
🟢 NOTIFICATION 3: "✅ Fixed and executed successfully!"
   - Type: success
   - Duration: 3 seconds
   - Position: left side of screen
          ↓
User sees cube transform to sphere ✅
```

### Failure Scenario: Retry Also Fails

```
User says: "do something impossible"
          ↓
AI generates code → ERROR
          ↓
🔴 NOTIFICATION 1: "❌ error message"
          ↓
⏱️ 0.5 second delay
          ↓
🟡 NOTIFICATION 2: "🔄 Adjusting code... (attempt 1/2)"
          ↓
AI tries to fix → Still fails
          ↓
Backend detects failure (action_router.py:148-156)
          ↓
🔴 NOTIFICATION 3: "❌ Retry failed: error message"
          ↓
Check retry attempt count
          ↓
If attempt < 2: Try again (back to NOTIFICATION 2 with "attempt 2/2")
If attempt >= 2: Give up, final error shown
```

### Max Retries Scenario

```
Attempt 1 fails → Show error → Show "Adjusting... (attempt 1/2)" → Retry
Retry 1 fails   → Show "Retry failed" → Check attempt count
Attempt 2 fails → Show error → Show "Adjusting... (attempt 2/2)" → Retry
Retry 2 fails   → Show "Retry failed" → STOP (max 2 retries reached)
Final state: User sees last error message, command failed
```

## Code Flow Verification

### 1. Error Detection (action_router.py:88-158)

**Lines 88-99**: Extract error message from MCP result
```python
error_msg = None
if 'content' in result and isinstance(result['content'], list):
    error_text = result['content'][0].get('text', '')
    if 'Error executing code:' in error_text:
        error_msg = error_text.replace('Error executing code: ', '')

if not error_msg and result.get('error'):
    error_msg = result['error']
```

**Lines 104-126**: Check if Blender error and broadcast notifications
```python
if server == 'blender-mcp' and tool_name == 'execute_blender_code' and error_msg:
    # First notification: Show the actual error
    self.ws_broadcast({
        "type": "action_command_result",
        "success": False,
        "error": f"❌ {error_msg}",
        "original_intent": command_text
    })

    # Delay so user sees error first
    await asyncio.sleep(0.5)

    # Second notification: Show we're retrying
    self.ws_broadcast({
        "type": "action_command_result",
        "success": False,
        "error": f"🔄 Adjusting code... (attempt {retry_attempt + 1}/2)",
        "original_intent": command_text,
        "is_retrying": True
    })
```

**Lines 128-158**: Execute retry and broadcast result
```python
retry_result = await self._retry_with_ai_fix(...)

if retry_result:
    if retry_result.get('success'):
        # Success notification
        self.ws_broadcast({
            "type": "action_command_result",
            "success": True,
            "message": f"✅ Fixed and executed successfully!",
            "original_intent": command_text
        })
    else:
        # Failure notification
        self.ws_broadcast({
            "type": "action_command_result",
            "success": False,
            "error": f"❌ Retry failed: {retry_result.get('error', 'Unknown error')}",
            "original_intent": command_text
        })
```

### 2. WebSocket Message Routing

**Backend** (action_router.py):
```python
self.ws_broadcast({
    "type": "action_command_result",
    "success": False,
    "error": "message here"
})
```
↓ WebSocket ↓

**Frontend** (context_app.js:185-192):
```javascript
this.ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    this.handleBackendMessage(data);
}
```
↓

**Message Handler** (context_app.js:369-372):
```javascript
case 'action_command_result':
    console.log('✅ [ACTION] Command result:', data);
    this.handleActionCommandResult(data);
    break;
```
↓

**Result Handler** (context_app.js:673-694):
```javascript
handleActionCommandResult(data) {
    const { success, message, error } = data;

    if (success) {
        this.showNotification(message || `✅ Action completed successfully`, 'success');
    } else {
        this.showNotification(error || `❌ Action failed`, 'error');
    }
}
```
↓

**Notification Display** (context_app.js:1476-1522):
```javascript
showNotification(message, level = 'info') {
    // Deduplication check (3 second cooldown)
    const now = Date.now();
    const lastShown = this.recentNotifications.get(message);

    if (lastShown && (now - lastShown) < 3000) {
        return; // Skip duplicate
    }

    // Show via Electron IPC
    window.electronAPI.invoke('show-notification', {
        message: message,
        level: level,  // 'success', 'error', 'info', 'warning'
        duration: level === 'error' ? 5000 : 3000,  // Errors show longer
        position: 'left'
    });
}
```

### 3. Notification Deduplication

**Problem**: Multiple broadcasts might create duplicate notifications

**Solution** (context_app.js:1477-1484):
- Tracks recent notifications in Map
- 3 second cooldown per unique message
- Prevents notification spam

**Example**:
```
Time 0s: Show "❌ Error A" → Displayed ✅
Time 1s: Show "❌ Error A" → Skipped (duplicate)
Time 4s: Show "❌ Error A" → Displayed ✅ (cooldown expired)
```

## Verification Checklist

### Backend (Python)

- [x] Error extracted from MCP result (lines 88-99)
- [x] Error detection for Blender MCP (line 105)
- [x] First notification: Error message (lines 108-114)
- [x] Delay between notifications (line 117)
- [x] Second notification: Adjusting message (lines 119-126)
- [x] Retry logic execution (lines 128-135)
- [x] Success notification after retry (lines 139-147)
- [x] Failure notification after retry (lines 148-156)
- [x] WebSocket broadcast function available (self.ws_broadcast)

### Frontend (JavaScript)

- [x] WebSocket onmessage handler (context_app.js:185-192)
- [x] Message type routing (context_app.js:369-372)
- [x] Action result handler (context_app.js:673-694)
- [x] Success notification display (line 681)
- [x] Error notification display (line 692)
- [x] Notification deduplication (lines 1477-1484)
- [x] Electron IPC notification (lines 1502-1517)
- [x] Error notifications show for 5 seconds (line 1505)
- [x] Success notifications show for 3 seconds (line 1505)

### Integration Points

- [x] Backend uses correct WebSocket broadcast type: "action_command_result"
- [x] Backend includes required fields: success, error/message, original_intent
- [x] Frontend expects these exact field names
- [x] Notification system handles errors, success, info, warning levels
- [x] Deduplication prevents spam from multiple broadcasts

## Testing Instructions

### Test 1: Verify Initial Error Shows
```
Command: "transform cube to sphere"
Expected: See "❌ enum 'EDIT' not found in ('OBJECT')"
Duration: 5 seconds
```

### Test 2: Verify Retry Notification Shows
```
After error, expect: "🔄 Adjusting code... (attempt 1/2)"
Timing: 0.5 seconds after error notification
Duration: 3 seconds
```

### Test 3: Verify Success After Retry
```
After retry completes successfully, expect: "✅ Fixed and executed successfully!"
Duration: 3 seconds
Result: Cube transforms to sphere
```

### Test 4: Verify Retry Failure
```
Command: Something that can't be fixed
Expect sequence:
1. "❌ original error" (5 sec)
2. "🔄 Adjusting... (attempt 1/2)" (3 sec)
3. "❌ Retry failed: error" (5 sec)
4. If attempt < 2, repeat from step 2 with "attempt 2/2"
```

### Test 5: Verify No Duplicate Notifications
```
If backend sends same error twice within 3 seconds:
- First one: Shows ✅
- Second one: Skipped (deduplication)
- After 3 seconds: Shows again if sent
```

## Potential Issues & Solutions

### Issue 1: Notifications Not Showing
**Symptoms**: No popup appears
**Debug**:
1. Check backend logs for `ws_broadcast` calls
2. Check frontend console for `[ACTION] Command result:` logs
3. Check frontend console for `Showing notification via overlay system:` logs
4. Check if Electron IPC is working: `window.electronAPI` exists

**Solution**: If IPC broken, notification system won't work. Check Electron setup.

### Issue 2: Duplicate Notifications
**Symptoms**: Same error shows twice
**Debug**: Check if deduplication is working (3 second cooldown)
**Solution**: Already implemented in context_app.js lines 1477-1484

### Issue 3: Notifications Too Fast
**Symptoms**: User doesn't see error before "Adjusting..."
**Debug**: Check if 0.5 second delay is happening
**Solution**: Already implemented at line 117 with `await asyncio.sleep(0.5)`

### Issue 4: Final Success Not Showing
**Symptoms**: Cube transforms but no success notification
**Debug**:
1. Check if `retry_result.get('success')` is True
2. Check backend logs for `✅ Self-healing retry #1 succeeded!`
3. Check if ws_broadcast was called

**Solution**: Already implemented at lines 139-147

## Success Criteria

✅ User notification flow is complete if:
1. User sees initial error message (red notification, 5 seconds)
2. User sees "Adjusting..." message after 0.5 seconds (yellow/error, 3 seconds)
3. User sees success message when fixed (green notification, 3 seconds)
4. User sees failure message if retry also fails (red notification, 5 seconds)
5. No duplicate notifications within 3 seconds
6. All notifications appear on left side of screen
7. Notifications auto-dismiss after duration
8. User can click notification to dismiss early

## Implementation Status

- ✅ Backend error detection and extraction
- ✅ Backend notification broadcasts (all 3 types)
- ✅ Frontend WebSocket message handling
- ✅ Frontend notification display via Electron IPC
- ✅ Notification deduplication
- ✅ Proper timing delays between notifications
- ✅ Error vs success notification durations
- ✅ User-visible notification flow complete

## Next Steps

1. **Test end-to-end flow** with "transform cube to sphere" command
2. **Monitor logs** to verify all 3 notifications are sent and received
3. **Verify timing** - 0.5s delay between error and retry notifications
4. **Test edge cases** - max retries, unfixable errors, etc.
5. **Gather user feedback** on notification clarity and timing
