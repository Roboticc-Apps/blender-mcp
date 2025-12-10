# Blender MCP Context Broadcasting - Complete Implementation Guide

**Date**: December 9, 2024
**Purpose**: Implementation guide for adding Blender scene context broadcasting to OneController
**For**: Voice command implementation via Grok

---

## Executive Summary

This guide provides complete step-by-step instructions to implement **real-time Blender scene context broadcasting** in OneController, following the same pattern as Google Sheets and browser context.

**Goal**: When Blender is the active window, OneController should display the current Blender scene state (objects, selection, cameras, materials, etc.) in the AI Context Panel.

**Result**: Voice commands will have full awareness of the Blender scene, enabling commands like:
- "Add subdivision to the selected mesh" (AI knows Cube is selected)
- "Change camera angle to face the active object"
- "Apply material to all selected objects"

---

## Table of Contents

1. [OneController Architecture](#onecontroller-architecture)
2. [Current Context Implementation Patterns](#current-context-implementation-patterns)
3. [Blender MCP Capabilities](#blender-mcp-capabilities)
4. [Implementation Steps](#implementation-steps)
5. [Code Examples](#code-examples)
6. [Testing Checklist](#testing-checklist)

---

## OneController Architecture

### Project Structure

```
D:\development\python\one_controller\
├── backend/                          # Python backend (FastAPI + WebSocket)
│   ├── main.py                      # Main server entry point
│   ├── context_extraction.py       # Detects active window & app type
│   ├── context_monitor.py          # Monitors window changes & broadcasts context
│   └── context_server.py           # WebSocket server for real-time updates
├── frontend/                        # Electron frontend
│   ├── main.js                     # Electron main process
│   ├── context_app.js              # Frontend WebSocket client
│   ├── ai-context-panel-backend.js # AI Context Panel window manager
│   ├── mcp-manager.js              # MCP process lifecycle
│   └── mcp-ipc-handlers.js         # IPC handlers for calling MCP tools
└── D:\development\python\blender-mcp\  # Blender MCP (standalone repo)
    ├── addon.py                     # Blender addon (runs inside Blender)
    ├── dist/
    │   └── blender-mcp-v1.4.0-win32.zip  # Built package
    └── ONECONTROLLER_INTEGRATION_GUIDE.md
```

### Key Architectural Patterns

#### 1. Context Flow Pattern

```
Active Window Change
    ↓
context_extraction.py detects app type (AppType.BLENDER)
    ↓
context_monitor.py recognizes Blender
    ↓
Calls MCP tool: blender-mcp.get_scene_info
    ↓
Backend broadcasts to frontend via WebSocket
    ↓
Frontend displays in AI Context Panel
```

#### 2. MCP Communication Pattern

**All MCP calls go through IPC (Electron)**:
```javascript
// Backend Python → Frontend WebSocket → Frontend JavaScript → Electron IPC → MCP
const result = await window.electronAPI.invoke('mcp-call-tool', {
    server: 'blender-mcp',
    tool: 'get_scene_info',
    parameters: {}
});
```

**Key files**:
- `frontend/context_app.js` - Handles `mcp_tool_call_request` WebSocket messages
- `frontend/mcp-ipc-handlers.js` - IPC handler for `mcp-call-tool`
- `frontend/mcp-manager.js` - Manages MCP process lifecycle

#### 3. AI Context Panel Pattern

**Window Creation** (`frontend/ai-context-panel-backend.js`):
- Creates transparent, always-on-top BrowserWindow
- Positioned bottom-left (opposite to commands panel)
- Uses IPC to show/hide: `show-ai-context-panel`, `hide-ai-context-panel`

**Context Broadcasting**:
```javascript
// From context_monitor.py via WebSocket
ws.send({
    type: 'show_ai_context',
    app_name: 'Blender 3D',
    total_elements: scene.objects.length,
    context_data: { /* full scene info */ }
});
```

---

## Current Context Implementation Patterns

### Example 1: Google Sheets Context

**File**: `backend/context_monitor.py` (lines 187-200)

```python
elif app_type == 'google_sheets':
    logger.info(f"[CONTEXT-MONITOR] Google Sheets detected, extracting URL...")
    url = window_info.url
    if not url and ui_context_text and 'Browser URL:' in ui_context_text:
        import re
        match = re.search(r'Browser URL:\s*\n\s*(.+)', ui_context_text)
        if match:
            url = match.group(1).strip()

    if url:
        logger.info(f"[CONTEXT-MONITOR] Extracted URL for Google Sheets: {url}")
        await self._handle_google_sheets(url, ui_context_text)
    else:
        logger.warning(f"[CONTEXT-MONITOR] Google Sheets detected but no URL available")
```

**What it does**:
1. Detects Google Sheets is active
2. Extracts spreadsheet URL
3. Calls `_handle_google_sheets()` which:
   - Calls Google Workspace MCP to get spreadsheet data
   - Combines with Windows MCP UI context
   - Broadcasts enriched context to frontend

### Example 2: Browser Context (Windows MCP State-Tool)

**File**: `backend/context_monitor.py` (lines 116-160)

```python
is_browser = app_type in ['chrome', 'edge', 'firefox'] or domain is not None

if is_browser:
    logger.info(f"[CONTEXT-MONITOR] Browser detected ({app_type}), getting UI context...")
    ui_context_text = await self._get_ui_context_direct()

    if ui_context_text:
        parsed_ui_data = self._parse_ui_context(ui_context_text)
        logger.info(f"[CONTEXT-MONITOR] UI context retrieved: {len(ui_context_text)} chars")

# ALWAYS broadcast Windows MCP AI context first
await self._broadcast_ai_context(
    window_info=window_info,
    ui_context_text=ui_context_text,
    parsed_ui_data=parsed_ui_data
)
```

**What it does**:
1. Detects browser is active
2. Calls `_get_ui_context_direct()` to get State-Tool output (accessibility tree)
3. Parses UI data to extract interactive elements
4. Broadcasts to AI Context Panel

### Key Takeaway Pattern

**For Blender, we need to**:
1. Detect when Blender is active (add `AppType.BLENDER` detection)
2. Call Blender MCP's `get_scene_info` tool
3. Parse the scene data
4. Broadcast to AI Context Panel (same as Google Sheets/Browser)

---

## Blender MCP Capabilities

### Current Implementation (Limited)

**Tool**: `get_scene_info`
**Current Response** (from `D:\development\python\blender-mcp\addon.py`):

```json
{
  "scene_name": "Scene",
  "objects": [
    {"name": "Cube", "type": "MESH", "location": [0.0, 0.0, 0.0]},
    {"name": "Light", "type": "LIGHT", "location": [4.08, 1.00, 5.90]},
    {"name": "Camera", "type": "CAMERA", "location": [7.36, -6.93, 4.96]}
    // ... only first 10 objects (LIMITATION)
  ],
  "object_count": 3,
  "materials_count": 1
}
```

**Limitations**:
- ❌ Only first 10 objects
- ❌ No selected objects
- ❌ No active object
- ❌ No cameras, lights details
- ❌ No materials data
- ❌ No modifiers, constraints

### Enhanced Implementation (Needed)

**Same tool, enhanced response**:

```json
{
  "scene": {
    "name": "Scene",
    "frame_current": 1,
    "frame_start": 1,
    "frame_end": 250,
    "render_engine": "CYCLES",
    "active_camera": "Camera",
    "mode": "OBJECT"
  },
  "selection": {
    "active_object": "Cube",
    "selected_objects": ["Cube", "Light"],
    "total_selected": 2
  },
  "objects": [
    {
      "name": "Cube",
      "type": "MESH",
      "location": [0.0, 0.0, 0.0],
      "rotation": [0.0, 0.0, 0.0],
      "scale": [1.0, 1.0, 1.0],
      "visible": true,
      "vertex_count": 8,
      "face_count": 6,
      "modifiers": ["Subdivision Surface"],
      "materials": ["Material.001"],
      "parent": null,
      "children": []
    }
    // ... ALL objects (no limit)
  ],
  "materials": [
    {
      "name": "Material.001",
      "use_nodes": true,
      "base_color": [0.8, 0.8, 0.8, 1.0]
    }
  ],
  "world": {
    "name": "World",
    "background_color": [0.05, 0.05, 0.05]
  }
}
```

### Implementation Required in Blender MCP

**File to modify**: `D:\development\python\blender-mcp\addon.py`

**See**: `BLENDER_CONTEXT_RESEARCH.md` lines 339-398 for complete enhanced code

**Key changes**:
```python
def get_scene_info(self):
    scene = bpy.context.scene

    return {
        "scene": {
            "name": scene.name,
            "frame_current": scene.frame_current,
            "render_engine": scene.render.engine,
            "active_camera": scene.camera.name if scene.camera else None,
            "mode": bpy.context.mode
        },
        "selection": {
            "active_object": bpy.context.active_object.name if bpy.context.active_object else None,
            "selected_objects": [obj.name for obj in bpy.context.selected_objects],
            "total_selected": len(bpy.context.selected_objects)
        },
        "objects": self._get_all_objects(),  # Remove 10-object limit
        "materials": self._get_materials(),
        "world": self._get_world_settings()
    }
```

---

## Implementation Steps

### Step 1: Add Blender App Type Detection

**File**: `backend/context_extraction.py`

**Location**: Line 40 (after `EDGE = "edge"`)

**Add**:
```python
BLENDER = "blender"
```

**Location**: Lines 167-200 (in `_determine_app_type()`)

**Add after line 188**:
```python
# Blender
if "blender.exe" in process_lower:
    return AppType.BLENDER
```

**Test**:
```bash
# Open Blender, check logs for:
[CONTEXT-MONITOR] Context changed to: blender
```

---

### Step 2: Add Blender Context Handling in Context Monitor

**File**: `backend/context_monitor.py`

**Location**: After Google Sheets handler (after line 200)

**Add**:
```python
elif app_type == 'blender':
    logger.info(f"[CONTEXT-MONITOR] Blender detected, fetching scene info...")

    # Fetch Blender scene context from MCP
    await self._handle_blender_scene(ui_context_text)
```

**Location**: Create new method (end of class, around line 400)

**Add**:
```python
async def _handle_blender_scene(self, ui_context_text: Optional[str]):
    """
    Fetch and broadcast Blender scene context

    Args:
        ui_context_text: Windows MCP State-Tool output (optional, for fallback)
    """
    try:
        logger.info(f"[CONTEXT-MONITOR] Fetching Blender scene info from blender-mcp...")

        # Call Blender MCP get_scene_info tool via frontend IPC bridge
        scene_data = await self._call_mcp_tool_via_frontend('blender-mcp', 'get_scene_info', {})

        if not scene_data:
            logger.warning(f"[CONTEXT-MONITOR] No scene data received from blender-mcp")
            return

        logger.info(f"[CONTEXT-MONITOR] Blender scene data retrieved: {len(scene_data.get('objects', []))} objects")

        # Broadcast enriched Blender context to frontend
        await self._broadcast_blender_context(scene_data, ui_context_text)

    except Exception as e:
        logger.error(f"[CONTEXT-MONITOR] Error handling Blender scene: {e}", exc_info=True)

async def _broadcast_blender_context(self, scene_data: dict, ui_context_text: Optional[str]):
    """
    Broadcast Blender scene context to frontend AI Context Panel

    Args:
        scene_data: Blender scene info from get_scene_info tool
        ui_context_text: Optional Windows MCP State-Tool output
    """
    try:
        # Extract key information
        scene_info = scene_data.get('scene', {})
        selection_info = scene_data.get('selection', {})
        objects = scene_data.get('objects', [])
        materials = scene_data.get('materials', [])

        # Build summary for AI
        summary = f"""
Blender Scene: {scene_info.get('name', 'Unknown')}
Mode: {scene_info.get('mode', 'OBJECT')}
Render Engine: {scene_info.get('render_engine', 'Unknown')}
Frame: {scene_info.get('frame_current', 1)}

Selection:
  Active: {selection_info.get('active_object', 'None')}
  Selected: {', '.join(selection_info.get('selected_objects', [])) or 'None'}
  Count: {selection_info.get('total_selected', 0)}

Objects ({len(objects)} total):
{self._format_object_list(objects[:10])}
{f'... and {len(objects) - 10} more' if len(objects) > 10 else ''}

Materials ({len(materials)} total):
{', '.join([m['name'] for m in materials[:5]])}
{f'... and {len(materials) - 5} more' if len(materials) > 5 else ''}
        """.strip()

        # Prepare AI context data
        context_data = {
            'app_name': 'Blender 3D',
            'app_identifier': 'blender',
            'total_elements': len(objects),
            'summary': summary,
            'scene_info': scene_info,
            'selection': selection_info,
            'objects': objects,
            'materials': materials,
            'raw_scene_data': scene_data,
            'ui_context': ui_context_text  # Include Windows MCP context as fallback
        }

        # Broadcast via WebSocket
        if hasattr(self, 'ws_broadcast'):
            await self.ws_broadcast({
                'type': 'show_ai_context',
                'app_name': 'Blender 3D',
                'total_elements': len(objects),
                'context_data': context_data
            })
            logger.info(f"[CONTEXT-MONITOR] Broadcasted Blender context to frontend")

    except Exception as e:
        logger.error(f"[CONTEXT-MONITOR] Error broadcasting Blender context: {e}", exc_info=True)

def _format_object_list(self, objects: list) -> str:
    """Format object list for display"""
    lines = []
    for obj in objects:
        name = obj.get('name', 'Unknown')
        obj_type = obj.get('type', 'UNKNOWN')
        location = obj.get('location', [0, 0, 0])
        lines.append(f"  - {name} ({obj_type}) at [{location[0]:.1f}, {location[1]:.1f}, {location[2]:.1f}]")
    return '\n'.join(lines)
```

**Important**: This code assumes `_call_mcp_tool_via_frontend()` exists. Check if it does in `context_monitor.py`. If not, use the pattern from `_handle_google_sheets()` which calls frontend IPC via WebSocket request.

---

### Step 3: Verify MCP Tool Calling Pattern

**Check**: `backend/context_monitor.py` for method `_call_mcp_tool_via_frontend()`

**If it doesn't exist**, use this pattern (same as Google Sheets):

```python
# Send MCP tool request to frontend via WebSocket
request_id = str(uuid.uuid4())
await self.ws_broadcast({
    'type': 'mcp_tool_call_request',
    'request_id': request_id,
    'server': 'blender-mcp',
    'tool': 'get_scene_info',
    'parameters': {}
})

# Wait for response (implement response handler in WebSocket message handling)
scene_data = await self._wait_for_mcp_response(request_id, timeout=5.0)
```

**Key**: Frontend receives `mcp_tool_call_request`, calls IPC `mcp-call-tool`, sends response back via `mcp_tool_call_response`.

**File**: `frontend/context_app.js` lines 617-671 already handles this pattern.

---

### Step 4: Enhance Blender MCP get_scene_info Tool

**File**: `D:\development\python\blender-mcp\addon.py`

**Location**: Find `get_scene_info()` method (around line 318)

**Replace with** (from `BLENDER_CONTEXT_RESEARCH.md` lines 339-398):

```python
def get_scene_info(self):
    """Get comprehensive Blender scene information"""
    scene = bpy.context.scene

    return {
        "scene": {
            "name": scene.name,
            "frame_current": scene.frame_current,
            "frame_start": scene.frame_start,
            "frame_end": scene.frame_end,
            "render_engine": scene.render.engine,
            "active_camera": scene.camera.name if scene.camera else None,
            "mode": bpy.context.mode
        },
        "selection": {
            "active_object": bpy.context.active_object.name if bpy.context.active_object else None,
            "selected_objects": [obj.name for obj in bpy.context.selected_objects],
            "total_selected": len(bpy.context.selected_objects)
        },
        "objects": self._get_all_objects(),
        "materials": self._get_materials(),
        "world": self._get_world_settings(),
        "collections": self._get_collections()
    }

def _get_all_objects(self):
    """Get comprehensive object data (removes 10-object limit)"""
    objects = []
    for obj in bpy.context.scene.objects:
        obj_data = {
            "name": obj.name,
            "type": obj.type,
            "location": [round(x, 2) for x in obj.location],
            "rotation": [round(x, 2) for x in obj.rotation_euler],
            "scale": [round(x, 2) for x in obj.scale],
            "visible": not obj.hide_get(),
            "modifiers": [mod.name for mod in obj.modifiers],
            "materials": [slot.material.name for slot in obj.material_slots if slot.material],
            "parent": obj.parent.name if obj.parent else None,
            "children": [child.name for child in obj.children]
        }

        # Type-specific data
        if obj.type == 'MESH':
            obj_data["vertex_count"] = len(obj.data.vertices)
            obj_data["face_count"] = len(obj.data.polygons)
        elif obj.type == 'CAMERA':
            obj_data["lens"] = obj.data.lens
            obj_data["sensor_width"] = obj.data.sensor_width
        elif obj.type == 'LIGHT':
            obj_data["light_type"] = obj.data.type
            obj_data["energy"] = obj.data.energy
            obj_data["color"] = [round(x, 2) for x in obj.data.color]

        objects.append(obj_data)

    return objects

def _get_materials(self):
    """Get all materials in scene"""
    materials = []
    for mat in bpy.data.materials:
        materials.append({
            "name": mat.name,
            "use_nodes": mat.use_nodes,
            "base_color": [round(x, 2) for x in mat.diffuse_color] if mat.diffuse_color else None
        })
    return materials

def _get_world_settings(self):
    """Get world/environment settings"""
    world = bpy.context.scene.world
    if not world:
        return None

    return {
        "name": world.name,
        "use_nodes": world.use_nodes
    }

def _get_collections(self):
    """Get all collections in scene"""
    collections = []
    for col in bpy.data.collections:
        collections.append({
            "name": col.name,
            "object_count": len(col.objects),
            "visible": not col.hide_viewport
        })
    return collections
```

**After modifying**, rebuild blender-mcp:
```bash
cd D:\development\python\blender-mcp
pyinstaller blender-mcp.spec
```

**Then** re-package and upload following `D:\development\python\one_controller\MCP_BUILD_AND_UPLOAD_GUIDE.md`

---

### Step 5: Test Blender Context Extraction

**Test Plan**:

1. **Start OneController**:
```bash
# Terminal 1: Backend
cd D:\development\python\one_controller\backend
python main.py

# Terminal 2: Frontend
cd D:\development\python\one_controller\frontend
npm start
```

2. **Open Blender**:
   - Create a simple scene (Cube, Light, Camera)
   - Select the Cube
   - Add a modifier (e.g., Subdivision Surface)

3. **Check Logs**:
```
[CONTEXT-MONITOR] Context changed to: blender
[CONTEXT-MONITOR] Blender detected, fetching scene info...
[CONTEXT-MONITOR] Fetching Blender scene info from blender-mcp...
[CONTEXT-MONITOR] Blender scene data retrieved: 3 objects
[CONTEXT-MONITOR] Broadcasted Blender context to frontend
```

4. **Verify AI Context Panel**:
   - Should appear bottom-left
   - Should show:
     ```
     Blender 3D
     Mode: OBJECT
     Selected: Cube
     Objects: 3 total
     ```

5. **Test Voice Commands**:
   - Say: "What is selected?"
     - Expected: AI responds "Cube is selected"
   - Say: "Add subdivision to the selected mesh"
     - Expected: AI knows Cube is selected, adds modifier

---

### Step 6: Add Polling for Real-Time Updates (Optional)

**Current**: Context only updates when window focus changes
**Enhancement**: Poll Blender every 3-5 seconds for scene changes

**File**: `backend/context_monitor.py`

**Location**: In `_monitor_loop()` method

**Add**:
```python
async def _monitor_loop(self):
    """Main monitoring loop"""
    last_blender_poll = 0
    blender_poll_interval = 3.0  # Poll Blender every 3 seconds

    try:
        while self._running:
            await self._check_context_change()

            # If Blender is active, poll for scene changes
            if self._last_context and self._last_context.app_type == 'blender':
                current_time = asyncio.get_event_loop().time()
                if current_time - last_blender_poll >= blender_poll_interval:
                    await self._handle_blender_scene(None)
                    last_blender_poll = current_time

            await asyncio.sleep(self._check_interval)
    except asyncio.CancelledError:
        logger.info("[CONTEXT-MONITOR] Monitor loop cancelled")
    except Exception as e:
        logger.error(f"[CONTEXT-MONITOR] Error in monitor loop: {e}", exc_info=True)
```

**Why**: This ensures that if you modify the scene in Blender (select different object, add modifier, etc.), the AI Context Panel updates automatically without switching windows.

---

## Code Examples

### Example: Full Context Monitor Integration

**File**: `backend/context_monitor.py`

```python
async def _check_context_change(self):
    """Check if active window context has changed"""
    try:
        from context_extraction import get_context_extractor

        context_extractor = get_context_extractor()
        window_info = context_extractor.get_active_window_info()

        if not window_info:
            return

        app_type = window_info.app_type.value

        # ... existing Google Sheets/Browser handling ...

        # Add Blender handling
        elif app_type == 'blender':
            logger.info(f"[CONTEXT-MONITOR] Blender detected, fetching scene...")

            # Get Windows MCP UI context (optional - shows Blender window state)
            ui_context_text = await self._get_ui_context_direct()

            # Broadcast Windows MCP context first (shows Blender is active)
            await self._broadcast_ai_context(
                window_info=window_info,
                ui_context_text=ui_context_text,
                parsed_ui_data={'interactive_elements': []}
            )

            # Then fetch and broadcast Blender scene context
            await self._handle_blender_scene(ui_context_text)

        # ... rest of method ...
```

---

## Testing Checklist

### Unit Tests

- [ ] `AppType.BLENDER` detection works for `blender.exe`
- [ ] `get_scene_info` returns enhanced data (not just 10 objects)
- [ ] Context monitor detects Blender as active app
- [ ] MCP tool call succeeds (returns scene data)
- [ ] AI Context Panel receives broadcast

### Integration Tests

- [ ] Open Blender → AI Context Panel shows scene
- [ ] Select object in Blender → Panel updates to show selection
- [ ] Add modifier in Blender → Panel reflects change (if polling enabled)
- [ ] Switch to Chrome → Panel switches to browser context
- [ ] Switch back to Blender → Panel returns to Blender context

### Voice Command Tests

- [ ] "What is selected?" → AI responds with selected object name
- [ ] "Add subdivision to selected mesh" → AI knows which object
- [ ] "List all objects" → AI lists all scene objects
- [ ] "What materials are in the scene?" → AI lists materials

---

## Troubleshooting

### Issue: Blender not detected

**Check**:
1. `blender.exe` in process name
2. `context_extraction.py` has `AppType.BLENDER`
3. `_determine_app_type()` checks for `blender.exe`

**Logs**:
```
[CONTEXT-MONITOR] Context changed to: blender
```

### Issue: MCP tool call fails

**Check**:
1. Blender MCP is installed and active
2. Blender is running (MCP connects to Blender)
3. `mcp-call-tool` IPC returns success

**Logs**:
```
[MCP] Calling tool: blender-mcp.get_scene_info
[MCP] Tool result: { success: true, result: {...} }
```

### Issue: AI Context Panel doesn't update

**Check**:
1. WebSocket connection is active
2. `show_ai_context` message is sent
3. Frontend receives message

**Logs**:
```
[AI-CONTEXT] Show AI context panel request: { app: 'Blender 3D', elements: 3 }
```

---

## Next Steps

1. **Implement Steps 1-4** (basic Blender context)
2. **Test with simple scene** (3 objects)
3. **Enhance blender-mcp addon** (Step 4)
4. **Add polling** (Step 6) for real-time updates
5. **Test voice commands** with Blender context

---

## Reference Files

- `D:\development\python\one_controller\BLENDER_CONTEXT_RESEARCH.md` - Blender capabilities research
- `D:\development\python\blender-mcp\ONECONTROLLER_INTEGRATION_GUIDE.md` - Blender MCP enhancement guide
- `D:\development\python\one_controller\backend\context_monitor.py` - Context monitoring implementation
- `D:\development\python\one_controller\backend\context_extraction.py` - App type detection
- `D:\development\python\one_controller\frontend\context_app.js` - WebSocket client & MCP bridge
- `D:\development\python\one_controller\MCP_BUILD_AND_UPLOAD_GUIDE.md` - MCP build process

---

**Status**: Ready for implementation
**Estimated Complexity**: Medium (follows existing patterns)
**Estimated Time**: 2-3 hours (includes testing)
