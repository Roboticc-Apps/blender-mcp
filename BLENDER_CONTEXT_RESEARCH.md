# Blender MCP Context Broadcasting Research

**Date**: December 9, 2024
**Research Goal**: Determine if Blender MCP can expose current scene state similar to Google Sheets API context or website accessibility tree scanning

---

## Summary

✅ **YES - Blender CAN expose scene state context**
⚠️ **LIMITATION - Current implementation is minimal (only 10 objects, basic info)**
✅ **YES - Real-time event handlers are available in Blender Python API**
❌ **NO - Current MCP implementation doesn't broadcast changes (poll-only)**

---

## Current Blender MCP Capabilities

### Tool: `get_scene_info`

**What it currently returns:**
- Scene name
- Object count
- Materials count
- First 10 objects only with:
  - Object name
  - Object type
  - Object location (x, y, z)

**What it DOESN'T return (but could):**
- ❌ Cameras
- ❌ Lights
- ❌ Modifiers
- ❌ Material properties
- ❌ Selected objects
- ❌ Active object
- ❌ Textures
- ❌ World/environment settings
- ❌ Render settings
- ❌ Constraints
- ❌ Animation data

**Implementation Pattern:**
- Request-response only (no streaming)
- Client must poll `get_scene_info()` to check for changes
- No WebSocket or event broadcasting

---

## Blender Python API - Full Context Available

### `bpy.context` Properties (Available but Underutilized)

```python
import bpy

# Object Selection & Focus
bpy.context.selected_objects    # All selected objects
bpy.context.active_object        # Currently active object
bpy.context.object              # Current object reference

# Scene Information
bpy.context.scene               # Active scene
bpy.context.view_layer          # Current view layer
bpy.context.collection          # Active collection

# Workspace & UI State
bpy.context.area                # Current editor area
bpy.context.region              # Active region
bpy.context.workspace           # Active workspace
bpy.context.mode                # Interaction mode (object/edit/sculpt)
bpy.context.tool                # Active tool

# Animation
bpy.context.scene.frame_current # Current frame
```

### `bpy.data` Access (Complete Scene Data)

```python
import bpy

# All scene elements
bpy.data.objects                # All objects
bpy.data.materials              # All materials
bpy.data.cameras                # All cameras
bpy.data.lights                 # All lights
bpy.data.meshes                 # All mesh data
bpy.data.images                 # All textures/images
bpy.data.worlds                 # World settings
bpy.data.scenes                 # All scenes
bpy.data.collections            # All collections

# Per-object details
obj = bpy.context.active_object
obj.name                        # Object name
obj.type                        # Type (MESH, CAMERA, LIGHT, etc.)
obj.location                    # World location
obj.rotation_euler              # Rotation
obj.scale                       # Scale
obj.modifiers                   # All modifiers
obj.constraints                 # All constraints
obj.material_slots              # Assigned materials
obj.data                        # Object-specific data (mesh, camera, etc.)
```

---

## Real-Time Event Handlers (Available in Blender)

### `bpy.app.handlers` - Event Broadcasting System

Blender has a **complete event system** that can detect changes in real-time:

```python
import bpy

# Scene Change Handlers
bpy.app.handlers.depsgraph_update_post   # Fires after scene graph updates
bpy.app.handlers.depsgraph_update_pre    # Fires before scene graph updates
bpy.app.handlers.frame_change_post       # Animation frame changed
bpy.app.handlers.frame_change_pre        # Before frame change

# File Operation Handlers
bpy.app.handlers.load_post               # File loaded
bpy.app.handlers.save_post               # File saved

# Edit History Handlers
bpy.app.handlers.undo_post               # Undo performed
bpy.app.handlers.redo_post               # Redo performed

# Object/Data Handlers
bpy.app.handlers.object_bake_pre         # Before baking
bpy.app.handlers.object_bake_complete    # After baking
```

### Example: Detecting Mesh Changes

```python
import bpy

def on_depsgraph_update(scene, depsgraph):
    # Check if mesh data changed
    if depsgraph.id_type_updated("MESH"):
        print("Mesh changed!")
        # Could broadcast context here

    # Check if objects changed
    if depsgraph.id_type_updated("OBJECT"):
        print("Object changed!")

# Register handler
bpy.app.handlers.depsgraph_update_post.append(on_depsgraph_update)
```

**Reference**: [Application Handlers Documentation](https://docs.blender.org/api/current/bpy.app.handlers.html)

---

## Comparison to OneController's Other Integrations

### Browser/Websites (Current Implementation)
- **Method**: Accessibility tree scanning
- **Broadcasting**: Real-time via browser events
- **Context sent**: DOM structure, selected elements, page state
- **Display**: AI context container on frontend

### Google Sheets (Current Implementation)
- **Method**: Google Sheets API
- **Broadcasting**: API polling / real-time updates
- **Context sent**: Current spreadsheet data, selected cells, formulas
- **Display**: AI context container on frontend

### Blender MCP (Proposed Enhancement)
- **Method**: Enhanced `get_scene_info` + event handlers
- **Broadcasting**: Could add real-time via `bpy.app.handlers`
- **Context to send**: Full scene state (see below)
- **Display**: AI context container on frontend (same pattern)

---

## Proposed Enhanced Context for Blender

### What We SHOULD Expose (Comprehensive Context)

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
    "selected_objects": ["Cube", "Light", "Camera"],
    "total_selected": 3
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
      "constraints": [],
      "parent": null,
      "children": []
    },
    {
      "name": "Camera",
      "type": "CAMERA",
      "location": [7.36, -6.93, 4.96],
      "rotation": [1.11, 0.0, 0.81],
      "lens": 50.0,
      "sensor_width": 36.0
    },
    {
      "name": "Light",
      "type": "LIGHT",
      "light_type": "POINT",
      "location": [4.08, 1.00, 5.90],
      "energy": 1000.0,
      "color": [1.0, 1.0, 1.0]
    }
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
    "use_nodes": true,
    "background_color": [0.05, 0.05, 0.05]
  },
  "collections": [
    {
      "name": "Collection",
      "object_count": 3,
      "visible": true
    }
  ]
}
```

---

## Implementation Strategies

### Option 1: Polling (Current MCP Pattern)
**How it works:**
- Frontend periodically calls `get_scene_info` tool
- MCP server requests data from Blender addon
- Addon extracts current state via `bpy.context` and `bpy.data`
- Returns JSON to frontend

**Pros:**
- ✅ Simple to implement
- ✅ Works with current MCP architecture
- ✅ No Blender addon changes needed

**Cons:**
- ❌ Network overhead (repeated requests)
- ❌ Delay in detecting changes
- ❌ Wastes resources when nothing changes

### Option 2: Event-Driven Broadcasting (Recommended)
**How it works:**
- Blender addon registers `bpy.app.handlers.depsgraph_update_post`
- On scene change, addon pushes update via MCP server
- MCP server broadcasts to OneController frontend
- Frontend updates AI context container in real-time

**Pros:**
- ✅ Real-time updates (same as browser/Google Sheets)
- ✅ Efficient (only sends when changed)
- ✅ Better UX (instant context refresh)
- ✅ Aligns with existing OneController patterns

**Cons:**
- ⚠️ Requires MCP server websocket/SSE support
- ⚠️ More complex implementation
- ⚠️ Needs Blender addon modification

### Option 3: Hybrid Approach
**How it works:**
- Frontend polls at low frequency (e.g., every 5 seconds)
- Blender addon caches state and detects changes
- Only returns full context if state changed since last poll

**Pros:**
- ✅ Balance of simplicity and efficiency
- ✅ Detects most changes quickly
- ✅ Minimal network overhead

**Cons:**
- ⚠️ Still has polling delay
- ⚠️ Requires change detection logic

---

## Technical Implementation Notes

### Enhancing `get_scene_info` Tool

**Current addon implementation** (addon.py):
```python
def get_scene_info(self):
    scene = bpy.context.scene
    objects_info = []

    # Only first 10 objects - LIMITATION
    for obj in list(scene.objects)[:10]:
        objects_info.append({
            "name": obj.name,
            "type": obj.type,
            "location": [round(x, 2) for x in obj.location]
        })

    return {
        "scene_name": scene.name,
        "objects": objects_info,
        "object_count": len(scene.objects),
        "materials_count": len(bpy.data.materials)
    }
```

**Enhanced implementation** (proposed):
```python
def get_scene_info(self):
    scene = bpy.context.scene

    # Full scene context
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
        "objects": self._get_all_objects(),  # Remove 10-object limit
        "materials": self._get_materials(),
        "world": self._get_world_settings(),
        "collections": self._get_collections()
    }

def _get_all_objects(self):
    """Get comprehensive object data"""
    objects = []
    for obj in bpy.context.scene.objects:
        obj_data = {
            "name": obj.name,
            "type": obj.type,
            "location": list(obj.location),
            "rotation": list(obj.rotation_euler),
            "scale": list(obj.scale),
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
            obj_data["color"] = list(obj.data.color)

        objects.append(obj_data)

    return objects
```

### Adding Event Broadcasting

**Blender addon enhancement**:
```python
import bpy
import json

# Global state tracking
last_scene_state = None

def on_depsgraph_update(scene, depsgraph):
    """Handler fires when scene changes"""
    global last_scene_state

    # Get current state
    current_state = get_scene_info_json()

    # Only broadcast if changed
    if current_state != last_scene_state:
        # Send to MCP server
        broadcast_context_update(current_state)
        last_scene_state = current_state

# Register on addon load
def register():
    bpy.app.handlers.depsgraph_update_post.append(on_depsgraph_update)

def unregister():
    bpy.app.handlers.depsgraph_update_post.remove(on_depsgraph_update)
```

**MCP server enhancement** (server.py):
```python
# Add websocket/SSE endpoint for real-time updates
class ContextBroadcaster:
    def __init__(self):
        self.subscribers = []

    def subscribe(self, client):
        """Frontend subscribes to context updates"""
        self.subscribers.append(client)

    def broadcast(self, context_data):
        """Broadcast to all subscribed clients"""
        for client in self.subscribers:
            client.send({
                "type": "context_update",
                "source": "blender",
                "data": context_data
            })
```

---

## Integration with OneController Frontend

### AI Context Container Pattern

Same pattern as Google Sheets and browser context:

**Frontend component** (ai-context-container.js):
```javascript
class AIContextContainer {
    constructor() {
        this.contexts = {
            browser: null,
            googleSheets: null,
            blender: null  // ← Add Blender
        };
    }

    async updateBlenderContext() {
        // Option 1: Polling
        const result = await window.electronAPI.invoke('mcp-call-tool', {
            server: 'blender-mcp',
            tool: 'get_scene_info',
            parameters: {}
        });

        if (result.success) {
            this.contexts.blender = result.result;
            this.renderContext();
        }
    }

    // Option 2: Event-driven (preferred)
    subscribeToBlenderUpdates() {
        window.electronAPI.on('blender-context-update', (data) => {
            this.contexts.blender = data;
            this.renderContext();
        });
    }

    renderContext() {
        const container = document.getElementById('ai-context');

        // Render Blender context
        if (this.contexts.blender) {
            container.innerHTML += `
                <div class="context-section blender">
                    <h3>🎨 Blender Scene</h3>
                    <div class="context-data">
                        <p><strong>Scene:</strong> ${this.contexts.blender.scene.name}</p>
                        <p><strong>Selected:</strong> ${this.contexts.blender.selection.selected_objects.join(', ')}</p>
                        <p><strong>Objects:</strong> ${this.contexts.blender.objects.length}</p>
                        <p><strong>Mode:</strong> ${this.contexts.blender.scene.mode}</p>
                    </div>
                    <details>
                        <summary>Full Scene Data</summary>
                        <pre>${JSON.stringify(this.contexts.blender, null, 2)}</pre>
                    </details>
                </div>
            `;
        }
    }
}
```

---

## Recommendations

### Immediate Actions (Quick Win)
1. ✅ **Enhance `get_scene_info` to return comprehensive data** (modify addon.py)
   - Remove 10-object limit
   - Add selected objects
   - Add active object
   - Add cameras, lights, materials
   - Add type-specific properties

2. ✅ **Implement polling in frontend** (modify ai-context-container.js)
   - Poll `get_scene_info` every 3-5 seconds when Blender MCP is active
   - Display in AI context container
   - Same UX as Google Sheets context

### Medium-Term (Best UX)
3. ⚠️ **Add event-driven broadcasting**
   - Modify Blender addon to use `bpy.app.handlers`
   - Add websocket/SSE to MCP server
   - Push updates to frontend in real-time
   - Matches browser context pattern

### Long-Term (Advanced Features)
4. 💡 **Context-aware AI commands**
   - AI can see selected objects and suggest operations
   - "Add subdivision to selected mesh" (AI knows Cube is selected)
   - "Change camera angle to face active object"
   - "Apply material to all selected objects"

---

## Answer to Original Question

### **Can Blender MCP expose current state like Google Sheets?**

**YES** - Absolutely! The capabilities are there:

| Feature | Google Sheets | Blender | Status |
|---------|--------------|---------|--------|
| Get current context | ✅ Yes (API) | ✅ Yes (`bpy.context`) | **Available** |
| Comprehensive data | ✅ Yes (cells, formulas) | ✅ Yes (objects, materials, etc.) | **Needs enhancement** |
| Real-time updates | ✅ Yes (API events) | ✅ Yes (`bpy.app.handlers`) | **Not implemented** |
| Frontend display | ✅ Yes (context container) | ⚠️ Could be | **To be built** |
| Broadcasting | ✅ Yes | ❌ No (poll only) | **Could be added** |

### **Current Limitation:**
The existing Blender MCP implementation is **deliberately minimal** (only 10 objects, basic info) - but Blender's Python API exposes **EVERYTHING** we need.

### **Solution:**
Enhance the `get_scene_info` tool to extract comprehensive context from `bpy.context` and `bpy.data`, then either:
- **Quick**: Poll it from frontend (like Google Sheets)
- **Best**: Add `bpy.app.handlers` for real-time broadcasting (like browser events)

---

## References

- [Blender MCP Repository](https://github.com/ahujasid/blender-mcp)
- [Blender MCP Official Site](https://blender-mcp.com/)
- [Blender Python API - Context](https://docs.blender.org/api/current/bpy.context.html)
- [Blender Python API - Handlers](https://docs.blender.org/api/current/bpy.app.handlers.html)
- [MCP Introduction](https://www.digitalocean.com/community/tutorials/model-context-protocol)
- [Depsgraph Documentation](https://docs.blender.org/api/current/bpy.types.Depsgraph.html)

---

## Next Steps

1. **Test current `get_scene_info`** - Call the tool and see what it actually returns
2. **Decide on approach** - Polling vs event-driven
3. **Enhance addon.py** - Add comprehensive context extraction
4. **Update frontend** - Add Blender to AI context container
5. **Test integration** - Verify context updates when scene changes

**Status**: Research complete. Ready for implementation planning.
