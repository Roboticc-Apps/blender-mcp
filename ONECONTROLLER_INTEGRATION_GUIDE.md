# OneController Integration Guide - Blender Context Broadcasting

**For**: Claude Agent implementing Blender context feature
**Date**: December 9, 2024
**Repository**: D:\development\python\blender-mcp

---

## Mission

Implement real-time Blender scene context broadcasting in OneController, following the same pattern as Google Sheets and browser context integrations.

**Read First**: `BLENDER_CONTEXT_RESEARCH.md` - Contains full technical research on what's possible and recommended approaches.

---

## OneController Project Structure

### Main Repository
```
D:\development\python\one_controller\
├── frontend/                           # Electron frontend (renderer process)
│   ├── main.js                        # Main entry point
│   ├── preload.js                     # IPC bridge
│   ├── mcp-manager.js                 # MCP server management
│   ├── mcp-ipc-handlers.js            # IPC handlers for MCP operations
│   ├── services/
│   │   └── backend-storage-service.js # Supabase edge function calls
│   ├── settings/
│   │   ├── settings.html              # Settings UI
│   │   └── scripts/
│   │       └── mcp-handler.js         # MCP UI logic
│   └── ai-context/                    # ← AI CONTEXT SYSTEM (KEY!)
│       ├── ai-context-container.js    # Context display component
│       └── context-providers/         # Context source implementations
│           ├── browser-context.js     # Browser/website context
│           └── sheets-context.js      # Google Sheets context
│
├── backend/
│   ├── context_extraction.py          # Python context extraction
│   └── voice_processing.py            # Voice command processing
│
└── mcp_builds/                        # Built MCP packages (deployment)
```

### Blender MCP Repository (Your Work Here)
```
D:\development\python\blender-mcp\
├── addon.py                           # Blender addon (runs in Blender)
├── src/
│   └── blender_mcp/
│       └── server.py                  # MCP server (connects to OneController)
├── dist/                              # Built package
└── BLENDER_CONTEXT_RESEARCH.md       # Technical research (READ THIS!)
```

---

## How Context Works in OneController

### Current Implementations (Learn From These)

#### 1. Google Sheets Context

**Flow**:
```
Google Sheets API → backend-storage-service.js → ai-context-container.js → UI Display
```

**Key Files**:
- `frontend/services/backend-storage-service.js` - Fetches sheet data
- `frontend/ai-context/context-providers/sheets-context.js` - Formats context
- `frontend/ai-context/ai-context-container.js` - Displays in UI

**What it sends**:
```javascript
{
  "type": "sheets",
  "spreadsheet_id": "...",
  "active_sheet": "Sheet1",
  "selected_range": "A1:B10",
  "data": [...],
  "formulas": [...]
}
```

#### 2. Browser/Website Context

**Flow**:
```
Browser Accessibility Tree → context_extraction.py → ai-context-container.js → UI Display
```

**Key Files**:
- `backend/context_extraction.py` - Scans accessibility tree
- `frontend/ai-context/context-providers/browser-context.js` - Formats context
- `frontend/ai-context/ai-context-container.js` - Displays in UI

**What it sends**:
```javascript
{
  "type": "browser",
  "url": "https://example.com",
  "title": "Page Title",
  "selected_text": "...",
  "dom_elements": [...],
  "interactive_elements": [...]
}
```

---

## Your Mission: Blender Context

### Goal
Implement the same pattern for Blender MCP:

```
Blender Scene → blender-mcp (enhanced) → OneController Frontend → AI Context Display
```

### What You Need to Build

#### Phase 1: Enhance Blender MCP (blender-mcp repo)

**File**: `D:\development\python\blender-mcp\addon.py`

**Current `get_scene_info()` returns** (LIMITED):
```python
{
    "scene_name": "Scene",
    "object_count": 25,
    "materials_count": 5,
    "objects": [/* Only first 10 */]
}
```

**Enhanced `get_scene_info()` should return** (COMPREHENSIVE):
```python
{
    "scene": {
        "name": "Scene",
        "frame_current": 1,
        "mode": "OBJECT",
        "render_engine": "CYCLES",
        "active_camera": "Camera"
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
            "location": [0, 0, 0],
            "rotation": [0, 0, 0],
            "scale": [1, 1, 1],
            "visible": True,
            "vertex_count": 8,
            "face_count": 6,
            "modifiers": ["Subdivision Surface"],
            "materials": ["Material.001"]
        },
        # ALL objects, not just 10!
    ],
    "materials": [...],
    "cameras": [...],
    "lights": [...]
}
```

**Implementation**:
```python
# In addon.py, replace get_scene_info() method

def get_scene_info(self):
    """Enhanced scene info with comprehensive context"""
    import bpy

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
        "objects": self._get_all_objects(),  # ← Implement this
        "materials": self._get_materials(),  # ← Implement this
        "cameras": self._get_cameras(),      # ← Implement this
        "lights": self._get_lights()         # ← Implement this
    }

def _get_all_objects(self):
    """Get ALL objects with full details (not just 10!)"""
    import bpy

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
            "materials": [slot.material.name for slot in obj.material_slots if slot.material]
        }

        # Add type-specific data
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

# Similar implementations for _get_materials(), _get_cameras(), _get_lights()
```

**See**: `BLENDER_CONTEXT_RESEARCH.md` section "Technical Implementation Notes" for complete code.

---

#### Phase 2: Frontend Integration (one_controller repo)

**File**: Create `D:\development\python\one_controller\frontend\ai-context\context-providers\blender-context.js`

```javascript
/**
 * Blender Context Provider
 * Polls Blender MCP for scene state and formats for AI context display
 */

class BlenderContextProvider {
    constructor() {
        this.currentContext = null;
        this.pollInterval = null;
        this.isActive = false;
    }

    /**
     * Start polling Blender for scene updates
     */
    async start() {
        if (this.isActive) return;

        this.isActive = true;
        console.log('[BlenderContext] Starting context polling...');

        // Poll every 3 seconds
        this.pollInterval = setInterval(() => {
            this.updateContext();
        }, 3000);

        // Get initial context
        await this.updateContext();
    }

    /**
     * Stop polling
     */
    stop() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
        this.isActive = false;
        this.currentContext = null;
        console.log('[BlenderContext] Stopped context polling');
    }

    /**
     * Fetch latest scene info from Blender MCP
     */
    async updateContext() {
        try {
            // Call MCP tool via IPC
            const result = await window.electronAPI.invoke('mcp-call-tool', {
                server: 'blender-mcp',
                tool: 'get_scene_info',
                parameters: {}
            });

            if (result.success) {
                this.currentContext = result.result;

                // Notify AI context container
                window.dispatchEvent(new CustomEvent('context-update', {
                    detail: {
                        source: 'blender',
                        data: this.currentContext
                    }
                }));
            }
        } catch (error) {
            console.error('[BlenderContext] Failed to update:', error);
        }
    }

    /**
     * Get current context
     */
    getContext() {
        return this.currentContext;
    }

    /**
     * Format context for display in AI context container
     */
    formatForDisplay() {
        if (!this.currentContext) return null;

        const ctx = this.currentContext;

        return {
            title: '🎨 Blender Scene',
            summary: [
                `Scene: ${ctx.scene?.name || 'Unknown'}`,
                `Mode: ${ctx.scene?.mode || 'N/A'}`,
                `Selected: ${ctx.selection?.selected_objects?.join(', ') || 'None'}`,
                `Objects: ${ctx.objects?.length || 0}`,
                `Materials: ${ctx.materials?.length || 0}`
            ],
            details: ctx
        };
    }
}

// Export for use in AI context container
window.BlenderContextProvider = BlenderContextProvider;
```

---

**File**: Update `D:\development\python\one_controller\frontend\ai-context\ai-context-container.js`

Add Blender to existing context providers:

```javascript
class AIContextContainer {
    constructor() {
        this.contexts = {
            browser: new BrowserContextProvider(),
            sheets: new SheetsContextProvider(),
            blender: new BlenderContextProvider()  // ← ADD THIS
        };

        this.setupEventListeners();
    }

    setupEventListeners() {
        // Listen for context updates from all providers
        window.addEventListener('context-update', (event) => {
            const { source, data } = event.detail;

            if (source === 'blender') {
                this.renderBlenderContext(data);
            }
        });
    }

    /**
     * Render Blender context in UI
     */
    renderBlenderContext(data) {
        const container = document.getElementById('ai-context-display');
        if (!container) return;

        const blenderSection = `
            <div class="context-section blender-context">
                <div class="context-header">
                    <span class="context-icon">🎨</span>
                    <h3>Blender Scene</h3>
                    <button class="context-collapse" onclick="this.closest('.context-section').classList.toggle('collapsed')">
                        ▼
                    </button>
                </div>
                <div class="context-body">
                    <div class="context-summary">
                        <div class="context-item">
                            <strong>Scene:</strong> ${data.scene?.name || 'N/A'}
                        </div>
                        <div class="context-item">
                            <strong>Mode:</strong> ${data.scene?.mode || 'N/A'}
                        </div>
                        <div class="context-item">
                            <strong>Active Object:</strong> ${data.selection?.active_object || 'None'}
                        </div>
                        <div class="context-item">
                            <strong>Selected:</strong> ${data.selection?.selected_objects?.join(', ') || 'None'}
                        </div>
                        <div class="context-item">
                            <strong>Total Objects:</strong> ${data.objects?.length || 0}
                        </div>
                        <div class="context-item">
                            <strong>Frame:</strong> ${data.scene?.frame_current || 0} / ${data.scene?.frame_end || 250}
                        </div>
                    </div>

                    <details class="context-details">
                        <summary>Full Scene Data</summary>
                        <pre>${JSON.stringify(data, null, 2)}</pre>
                    </details>
                </div>
            </div>
        `;

        // Update or append blender context
        const existingBlender = container.querySelector('.blender-context');
        if (existingBlender) {
            existingBlender.outerHTML = blenderSection;
        } else {
            container.insertAdjacentHTML('beforeend', blenderSection);
        }
    }

    /**
     * Start/stop context providers based on active MCPs
     */
    async updateActiveProviders() {
        // Check if Blender MCP is running
        const mcpStatus = await window.electronAPI.invoke('mcp-get-status', 'blender-mcp');

        if (mcpStatus?.running) {
            this.contexts.blender.start();
        } else {
            this.contexts.blender.stop();
        }
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    window.aiContext = new AIContextContainer();
});
```

---

## Implementation Steps

### Step 1: Enhance Blender MCP

1. **Navigate to blender-mcp repo**:
   ```bash
   cd D:\development\python\blender-mcp
   ```

2. **Edit `addon.py`**:
   - Replace `get_scene_info()` method with enhanced version
   - Add helper methods: `_get_all_objects()`, `_get_materials()`, `_get_cameras()`, `_get_lights()`
   - Remove 10-object limit
   - Add selection context (`bpy.context.selected_objects`, `bpy.context.active_object`)

3. **Test in Blender**:
   - Load addon in Blender
   - Run `get_scene_info()` command
   - Verify comprehensive data is returned

4. **Commit changes**:
   ```bash
   git add addon.py
   git commit -m "Enhance get_scene_info to return comprehensive scene context"
   git push origin main
   ```

---

### Step 2: Add Frontend Integration

1. **Navigate to one_controller repo**:
   ```bash
   cd D:\development\python\one_controller
   ```

2. **Create Blender context provider**:
   - File: `frontend/ai-context/context-providers/blender-context.js`
   - Implement polling mechanism (every 3-5 seconds)
   - Format data for display

3. **Update AI context container**:
   - File: `frontend/ai-context/ai-context-container.js`
   - Add Blender to context providers
   - Implement `renderBlenderContext()` method
   - Add auto-start when Blender MCP is running

4. **Add CSS styling**:
   - File: `frontend/ai-context/ai-context.css` (if exists)
   - Style `.blender-context` section to match existing contexts

5. **Test in OneController**:
   - Start Blender MCP
   - Open Blender with addon running
   - Open OneController
   - Verify context appears in AI Context panel
   - Change scene in Blender → verify context updates

---

### Step 3: Optional - Event-Driven Updates (Advanced)

If polling works well, you can enhance later with real-time events:

**In `addon.py`**:
```python
import bpy

# Global state tracking
last_scene_state = None

def on_depsgraph_update(scene, depsgraph):
    """Handler fires when scene changes"""
    global last_scene_state

    # Only send if mesh or objects changed
    if depsgraph.id_type_updated("MESH") or depsgraph.id_type_updated("OBJECT"):
        current_state = get_scene_info()

        if current_state != last_scene_state:
            # Send via socket to MCP server
            send_context_update(current_state)
            last_scene_state = current_state

# Register handler
bpy.app.handlers.depsgraph_update_post.append(on_depsgraph_update)
```

**See**: `BLENDER_CONTEXT_RESEARCH.md` section "Adding Event Broadcasting" for complete implementation.

---

## Testing Checklist

- [ ] Enhanced `get_scene_info()` returns comprehensive data
- [ ] No 10-object limit
- [ ] Selection context included (selected_objects, active_object)
- [ ] Type-specific data for meshes, cameras, lights
- [ ] Frontend polls Blender MCP every 3-5 seconds
- [ ] Context appears in AI Context panel
- [ ] Context updates when scene changes in Blender
- [ ] Styling matches existing context sections
- [ ] MCP auto-starts context provider when running
- [ ] Context clears when MCP stops

---

## File Locations Summary

### Files You Will Edit (blender-mcp repo):
- ✏️ `D:\development\python\blender-mcp\addon.py` - Enhance `get_scene_info()`

### Files You Will Create (one_controller repo):
- ➕ `D:\development\python\one_controller\frontend\ai-context\context-providers\blender-context.js`

### Files You Will Update (one_controller repo):
- ✏️ `D:\development\python\one_controller\frontend\ai-context\ai-context-container.js` - Add Blender support
- ✏️ `D:\development\python\one_controller\frontend\ai-context\ai-context.css` - Add styling (optional)

---

## References

- **Research Document**: `D:\development\python\blender-mcp\BLENDER_CONTEXT_RESEARCH.md` - Full technical details
- **Blender Python API**: https://docs.blender.org/api/current/
- **MCP SDK**: Check `src/blender_mcp/server.py` for MCP implementation patterns
- **Google Sheets Context**: `frontend/ai-context/context-providers/sheets-context.js` - Example to follow
- **Browser Context**: `frontend/ai-context/context-providers/browser-context.js` - Example to follow

---

## Expected Results

When complete, OneController should display Blender scene context like this:

```
╔═══════════════════════════════════════════════╗
║ 🎨 Blender Scene                          ▼   ║
╠═══════════════════════════════════════════════╣
║ Scene: Scene                                  ║
║ Mode: OBJECT                                  ║
║ Active Object: Cube                           ║
║ Selected: Cube, Light                         ║
║ Total Objects: 12                             ║
║ Frame: 1 / 250                               ║
║                                               ║
║ ▶ Full Scene Data                            ║
║   (expandable JSON)                           ║
╚═══════════════════════════════════════════════╝
```

This context updates every 3-5 seconds as the user works in Blender, providing the AI with current scene state for better voice command context awareness.

---

## Questions?

If you encounter issues:
1. Check `BLENDER_CONTEXT_RESEARCH.md` for technical details
2. Look at existing context providers in `frontend/ai-context/context-providers/`
3. Test Blender addon changes in Blender first before integrating
4. Start with polling - event-driven can come later

**Good luck!** 🚀
