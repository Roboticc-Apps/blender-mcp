# Blender Voice Control System - Complete Documentation

## System Overview

The Blender voice control system uses a single powerful tool (`execute_blender_code`) combined with comprehensive AI knowledge to provide full control over Blender via voice commands.

**Architecture:**
```
Voice → OneController → Edge Function (AI) → execute_blender_code → Blender
```

**Core Principle**: Instead of 48+ primitive tools, we use:
1. **One execution tool**: `execute_blender_code` - runs any Python in Blender
2. **Context tools**: `get_scene_info`, `get_full_context`, `get_node_tree`
3. **AI knowledge**: Comprehensive Blender Python API knowledge in app_prompt

## Key Files

| File | Purpose |
|------|---------|
| `addon.py` | Blender addon - socket server on port 9876, executes Python in Blender |
| `src/blender_mcp/server.py` | MCP server - exposes tools via JSON-RPC |
| `BLENDER_AI_CONTROL_SYSTEM.md` | Comprehensive API knowledge (verified from source) |
| `BLENDER_APP_PROMPT.md` | Database-ready prompt for `app_prompts` table |

## MCP Tools Available

### Context Tools
- `get_scene_info` - Scene overview, objects, materials
- `get_full_context` - Editor state, selection, mode, viewport
- `get_node_tree` - Material nodes and connections
- `get_modifier_stack` - Object modifiers
- `get_viewport_state` - Viewport settings
- `get_viewport_screenshot` - Visual capture

### Execution Tool
- `execute_blender_code` - **THE CORE TOOL** - executes any Python code in Blender

### Asset Tools
- PolyHaven integration (HDRIs, textures, models)
- Sketchfab integration
- Hyper3D/Rodin integration
- Hunyuan3D integration

## How It Works

1. **User speaks**: "Make this object metallic"
2. **OneController transcribes** and sends to Edge Function
3. **Edge Function (AI)** receives:
   - Voice transcription
   - Scene context (from `get_scene_info` or `get_full_context`)
   - App prompt (comprehensive Blender knowledge)
4. **AI generates Python code**:
   ```python
   from bpy_extras.node_shader_utils import PrincipledBSDFWrapper
   import bpy

   obj = bpy.context.active_object
   if not obj:
       raise ValueError("No object selected")

   mat = obj.active_material or bpy.data.materials.new(name="Metal")
   mat.use_nodes = True
   wrapper = PrincipledBSDFWrapper(mat, is_readonly=False)
   wrapper.metallic = 1.0
   wrapper.roughness = 0.2

   if not obj.data.materials:
       obj.data.materials.append(mat)
   ```
5. **`execute_blender_code`** sends code to addon
6. **Addon executes** in Blender's main thread
7. **Result returned** to user

## Self-Healing

If code fails:
1. Error message returned to AI
2. AI analyzes error and generates fixed code
3. Retry (max 2 attempts)

## Voice Command Examples

| Say This | AI Generates |
|----------|--------------|
| "Make it red" | `wrapper.base_color = (0.8, 0.1, 0.1)` |
| "Make it shiny" | `wrapper.metallic = 1.0; wrapper.roughness = 0.2` |
| "Add subdivision" | `obj.modifiers.new(name="Subdivision", type='SUBSURF')` |
| "Delete it" | `bpy.ops.object.delete()` |
| "Move it up" | `obj.location.z += 1` |
| "Make it glass" | `wrapper.transmission = 1.0; wrapper.ior = 1.45` |
| "Add a sphere" | `bpy.ops.mesh.primitive_uv_sphere_add()` |
| "Render" | `bpy.ops.render.render(write_still=True)` |

## Database Setup

Insert into `app_prompts` table:
```sql
INSERT INTO app_prompts (app_identifier, system_prompt, is_enabled, priority)
VALUES ('blender', '[content from BLENDER_APP_PROMPT.md]', true, 100)
ON CONFLICT (app_identifier) DO UPDATE SET
    system_prompt = EXCLUDED.system_prompt,
    updated_at = NOW();
```

## Testing

1. Start Blender with addon enabled
2. Ensure socket server running on port 9876
3. Start MCP server: `python -m blender_mcp`
4. Test with voice commands or direct MCP calls

## Key Technical Details

### PrincipledBSDFWrapper (VERIFIED)
- `base_color` - RGB tuple (NOT RGBA!)
- `metallic` - float 0-1
- `roughness` - float 0-1
- `specular` - float 0-1 (maps to "Specular IOR Level")
- `transmission` - float 0-1 (maps to "Transmission Weight")
- `emission_color` - RGB
- `emission_strength` - float 0-1000000
- `ior` - float 0-1000
- `alpha` - float 0-1

### Critical Rules
1. Always `mat.use_nodes = True` before accessing node_tree
2. Always return to object mode after edit mode
3. Use exact names from context for objects/materials/nodes
4. Handle None checks for objects/materials
5. Wrap code in try-except for error handling

---

*System verified against Blender source code for accuracy.*
