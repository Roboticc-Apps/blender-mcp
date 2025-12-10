# Quick Test Guide - Blender Context Broadcasting

## 🚀 Quick Start (5 Minutes)

### Step 1: Start OneController (2 terminals)
```bash
# Terminal 1
cd D:\development\python\one_controller\backend
python main.py

# Terminal 2
cd D:\development\python\one_controller\frontend
npm start
```

### Step 2: Start Blender
1. Open Blender
2. Press `N` → BlenderMCP tab
3. Click "Connect to Claude"

### Step 3: Test
1. **Focus Blender window**
2. **Check logs** for: `🎨 [CONTEXT-MONITOR] Detected Blender`
3. **See AI Context Panel** (bottom-left)
4. **Try voice command**: "What is selected?"

---

## ✅ Success Indicators

### Backend Logs (Should See)
```
[CONTEXT-MONITOR] Context changed to: blender
🎨 [CONTEXT-MONITOR] Detected Blender, fetching scene info...
✅ [CONTEXT-MONITOR] Got scene data from Blender MCP
[CONTEXT-MONITOR] Broadcasted Blender AI context (3 objects, 1 materials, 1 selected)
```

### AI Context Panel (Should Show)
```
🎨 Blender 3D
Scene: Scene
Mode: OBJECT
Selected: Cube
Objects: 3
```

### Voice Commands (Should Work)
- "What is selected?" → "Cube is selected"
- "How many objects?" → "3 objects"
- "List all objects" → "Cube, Camera, Light"

---

## ❌ Troubleshooting

### No Context Panel?
1. Check Blender MCP is running (Settings > MCPs)
2. Restart OneController
3. Check WebSocket connection in browser console

### MCP Call Timeout?
1. In Blender: Edit > Preferences > Add-ons > Enable "Blender MCP"
2. In Blender 3D view: N key > BlenderMCP > "Connect to Claude"
3. Check Blender console (Windows: Window > Toggle System Console)

### Wrong Data?
1. Verify addon.py was updated (check file modified date)
2. Reload Blender addon (disable/enable in preferences)
3. Check if old version is cached

---

## 🧪 Test Scenarios

### Test 1: Object Selection Context
1. In Blender, select Cube
2. Say: "What is selected?"
3. Expected: AI responds "Cube is selected"

### Test 2: Multiple Objects
1. Add more objects (Shift+A)
2. Focus OneController
3. Say: "List all objects in the scene"
4. Expected: AI lists all objects (not just 10!)

### Test 3: Modifier Context
1. Select Cube
2. Add modifier (Modifier Properties > Add Modifier > Subdivision Surface)
3. Say: "What modifiers does the cube have?"
4. Expected: AI responds "Subdivision Surface"

### Test 4: Material Context
1. Create new material (Shading workspace)
2. Say: "What materials are in the scene?"
3. Expected: AI lists all materials

### Test 5: Context-Aware Commands
1. Select Cube
2. Say: "Add subdivision to the selected mesh"
3. Expected: AI generates code and adds modifier to Cube

---

## 📊 Key Metrics

**Context Update Speed**: < 1 second
**Object Limit**: Unlimited (was 10, now ALL)
**Data Points**: 6 categories (scene, selection, objects, materials, world, collections)
**Voice Command Accuracy**: Should improve 50%+ for Blender commands

---

## 🔍 Debug Commands

### Check MCP Status
```javascript
// In OneController frontend console
window.electronAPI.invoke('mcp-list').then(console.log)
```

### Manual MCP Call
```javascript
// In OneController frontend console
window.electronAPI.invoke('mcp-call-tool', {
    server: 'blender-mcp',
    tool: 'get_scene_info',
    parameters: {}
}).then(result => console.log(JSON.stringify(result, null, 2)))
```

### Check WebSocket Messages
```javascript
// In browser console, listen for context updates
// Should see messages with type: 'show_ai_context'
```

---

## 📝 Success Checklist

- [ ] Backend starts without errors
- [ ] Frontend starts without errors
- [ ] Blender addon enabled and connected
- [ ] Focus Blender → See context panel
- [ ] Context shows correct scene name
- [ ] Context shows selected objects
- [ ] Context lists ALL objects (not just 10)
- [ ] Voice command "What is selected?" works
- [ ] Voice command understands object names
- [ ] Context updates when changing selection

---

**Total Test Time**: ~5 minutes
**Files to Monitor**: Backend logs, AI Context Panel, Blender console
