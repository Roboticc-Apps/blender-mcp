# Blender MCP v2 - Complete Architecture & Design

## System Architecture

```
                    ┌─────────────────────────────────────────────────────────────┐
                    │                      USER VOICE                              │
                    └─────────────────────────────────────────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              ONECONTROLLER FRONTEND                                      │
│  - Transcription (Deepgram/etc)                                                         │
│  - WebSocket to backend                                                                 │
│  - MCP Tool execution                                                                   │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                              │
                    ┌─────────────────────────┴────────────────────────┐
                    │                                                  │
                    ▼                                                  ▼
┌──────────────────────────────────┐        ┌──────────────────────────────────────────────┐
│      CONTEXT MONITOR             │        │         EDGE FUNCTION                        │
│  (context_monitor.py)            │        │    (detect-voice-command)                    │
│                                  │        │                                              │
│  - Detects Blender is active     │        │  - AI DECIDES (no string matching!)         │
│  - Calls get_scene_info          │        │  - Analyzes voice + context                  │
│  - Broadcasts context to UI      │        │  - Selects MCP tool + parameters            │
│  - Auto-polls on focus change    │        │  - execution_mode: single_shot | agent      │
└──────────────────────────────────┘        │  - retry_context for self-healing            │
                    │                        └──────────────────────────────────────────────┘
                    │                                                  │
                    └──────────────────────┬───────────────────────────┘
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              ACTION ROUTER (action_router.py)                           │
│                                                                                         │
│  - Receives AI decision                                                                 │
│  - Executes MCP tool call                                                              │
│  - SELF-HEALING: If execute_blender_code fails, retries with error context             │
│  - Max 2 retries with AI-generated fix                                                 │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           │ JSON-RPC (stdio)
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              BLENDER MCP SERVER (server.py)                             │
│                                                                                         │
│  - FastMCP JSON-RPC server                                                             │
│  - Receives tool calls from OneController                                              │
│  - Forwards to Blender addon via TCP socket (localhost:9876)                           │
│  - Returns results                                                                      │
│                                                                                         │
│  @mcp.tool() decorators expose:                                                        │
│  - Context tools (get_scene_info, get_full_context, etc.)                             │
│  - Command tools (execute_blender_code, add_primitive, etc.)                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           │ TCP Socket (localhost:9876)
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              BLENDER ADDON (addon.py)                                   │
│                              Runs INSIDE Blender                                        │
│                                                                                         │
│  BlenderMCPServer class:                                                               │
│  - Socket server on localhost:9876                                                     │
│  - Receives JSON commands                                                              │
│  - Executes in Blender main thread via bpy.app.timers                                 │
│  - Returns results via socket                                                          │
│                                                                                         │
│  handlers dict:                                                                        │
│  - Context: get_full_context, get_scene_info, get_node_tree, etc.                     │
│  - Actions: execute_code, add_node, add_modifier, etc.                                │
│  - Polyhaven/Sketchfab/Hyper3D integration                                            │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           │ bpy.app.timers (main thread)
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              BLENDER API (bpy)                                          │
│                                                                                         │
│  - bpy.data (meshes, materials, objects, images, etc.)                                │
│  - bpy.ops (operators)                                                                 │
│  - bpy.context (active object, mode, scene)                                           │
│  - bpy_extras.node_shader_utils (PrincipledBSDFWrapper)                               │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## The AI-Driven Approach (NO String Matching!)

### How Commands Work Today:

1. **User speaks**: "Make this object shiny metal"
2. **OneController transcribes**: Text sent to Edge Function
3. **AI analyzes** (NOT string matching!):
   - Current context: Blender scene, selected object, materials
   - User intent: Apply metallic material
   - Available MCP tools from `unified_commands` table
4. **AI selects tool**: `execute_blender_code` with generated Python code
5. **Code executed in Blender**: Via addon socket server
6. **Self-healing if fails**: AI analyzes error, generates fixed code

### Why This Matters for v2:

The AI decides what code to generate. We don't need to create 100 primitive tools - we need to:
1. **Provide rich context** so AI understands the scene
2. **Create workflow tool descriptions** that guide AI thinking
3. **Let AI generate the code** using `execute_blender_code`

---

## The Problem with v1 Primitives

v1 exposes 48 low-level tools like:
- `add_node(type, material)`
- `connect_nodes(from, to)`
- `set_node_value(node, input, value)`

But the AI just uses `execute_blender_code` anyway! It generates Python code that does the whole workflow in one shot.

**The primitives are redundant** - they're just pre-written code snippets that the AI could generate.

---

## v2 Strategy: Smart Workflows via execute_blender_code

Instead of creating more primitive tools, v2 should:

### 1. Enhance Context Tools (for AI awareness)

```python
@mcp.tool()
async def get_full_context() -> dict:
    """
    Get comprehensive Blender state for AI decision-making.

    Returns:
        - editor: Current editor type, mode, active tool
        - viewport: Shading, camera, overlays
        - selection: Selected objects with full details
        - scene: Frame range, render settings
        - materials: All materials with node summaries
        - modifiers: Active object's modifier stack
    """
```

### 2. Create Workflow Guide Tools (for AI guidance)

These aren't "execute this code" tools - they're **documentation tools** that help the AI understand workflows:

```python
@mcp.tool()
async def get_workflow_guide(workflow_type: str) -> str:
    """
    Get code patterns and best practices for common Blender workflows.

    workflow_type options:
    - "pbr_material": PBR material setup using PrincipledBSDFWrapper
    - "mesh_cleanup": Removing doubles, fixing normals, etc.
    - "three_point_lighting": Standard 3-point lighting setup
    - "character_rig": Basic character rigging workflow
    - "cloth_sim": Cloth simulation setup

    Returns Python code examples and best practices that AI can adapt.
    """

    workflows = {
        "pbr_material": '''
# PBR Material Setup using Blender's built-in wrapper
from bpy_extras.node_shader_utils import PrincipledBSDFWrapper

# Create material
mat = bpy.data.materials.new(name="PBR_Material")
mat.use_nodes = True

# Use wrapper for easy setup
wrapper = PrincipledBSDFWrapper(mat, is_readonly=False)

# Set values
wrapper.base_color = (0.8, 0.2, 0.2)  # RGB
wrapper.metallic = 1.0
wrapper.roughness = 0.2

# Set textures (optional)
# wrapper.base_color_texture.image = bpy.data.images.load("/path/to/texture.png")
# wrapper.roughness_texture.image = bpy.data.images.load("/path/to/roughness.png")

# Apply to object
obj = bpy.context.active_object
if obj.data.materials:
    obj.data.materials[0] = mat
else:
    obj.data.materials.append(mat)
''',
        "mesh_cleanup": '''
# Mesh Cleanup Workflow
import bpy
import bmesh

obj = bpy.context.active_object
if obj.type != 'MESH':
    raise ValueError("Select a mesh object")

# Enter edit mode
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')

# Remove doubles (merge by distance)
bpy.ops.mesh.remove_doubles(threshold=0.0001)

# Recalculate normals
bpy.ops.mesh.normals_make_consistent(inside=False)

# Remove loose vertices/edges/faces
bpy.ops.mesh.delete_loose(use_verts=True, use_edges=True, use_faces=True)

# Return to object mode
bpy.ops.object.mode_set(mode='OBJECT')
''',
        # ... more workflows
    }
    return workflows.get(workflow_type, "Unknown workflow type")
```

### 3. Improve App Prompt (in app_prompts table)

```
You are controlling Blender via MCP. When the user asks to do something in Blender:

1. ANALYZE the context from get_full_context or get_scene_info
2. UNDERSTAND what the user wants (material, modeling, animation, etc.)
3. GENERATE Python code that accomplishes the task
4. USE execute_blender_code to run the code

For complex workflows, you can call get_workflow_guide first to get code patterns.

IMPORTANT:
- Always use bpy.context.active_object when user refers to "this" or "selected"
- Use PrincipledBSDFWrapper from bpy_extras.node_shader_utils for materials
- Set material.use_nodes = True before accessing node_tree
- Use bpy.ops.object.mode_set(mode='EDIT') before mesh operations
- Always return to object mode after edit mode operations

Common workflows:
- PBR Material: Use PrincipledBSDFWrapper for easy Principled BSDF setup
- Mesh cleanup: remove_doubles → normals_make_consistent → delete_loose
- Lighting: Create lights with bpy.ops.object.light_add()
```

---

## Database Updates for v2

### unified_commands Table

Instead of mapping to primitive tools, map to workflow descriptions:

```sql
-- Example: Material workflow command
INSERT INTO unified_commands (
    app_identifier,
    mcp_server_id,
    mcp_tool_name,
    command_triggers,
    description,
    command_type,
    is_enabled
) VALUES (
    'blender',
    'uuid-of-blender-mcp',
    'execute_blender_code',
    ARRAY['apply material', 'create material', 'make shiny', 'add texture'],
    'Create or modify materials on selected object. AI generates Python code using PrincipledBSDFWrapper for PBR materials.',
    'voice_command',
    true
);
```

### app_prompts Table

Update Blender app prompt with workflow guidance (see section 3 above).

---

## Context Polling Flow

When user focuses on Blender:

1. **context_extraction.py**: Detects `blender.exe` or `.blend` in window title
2. **context_monitor.py**: Calls `_handle_blender_scene()`
3. **MCP call**: `get_scene_info` via socket to addon
4. **Broadcast**: Scene data sent to frontend AI Context Panel
5. **Edge Function**: Receives context with voice command for AI decision

This happens automatically - context is always fresh when user speaks.

---

## Self-Healing Loop

```python
# In action_router.py
if server == 'blender-mcp' and tool_name == 'execute_blender_code' and error_msg:
    # Build retry context
    retry_context = {
        "previous_code": previous_code,
        "error_message": error_msg,
        "attempt_number": retry_attempt + 1,
        "original_command": command_text
    }

    # Call Edge Function again with retry_context
    # AI sees the error and generates fixed code
    # Execute again (max 2 retries)
```

This means AI can learn from errors and self-correct. The workflow tools don't need perfect code - AI will fix issues.

---

## v2 Tool List (Simplified)

### Context Tools (Keep from v1)
- `get_full_context` - Complete Blender state
- `get_scene_info` - Scene overview
- `get_object_info` - Selected object details
- `get_viewport_state` - Viewport settings
- `get_node_tree` - Material nodes
- `get_modifier_stack` - Modifiers

### Core Execution (Keep from v1)
- `execute_blender_code` - Run arbitrary Python code (AI uses this!)

### NEW: Workflow Guides (v2)
- `get_workflow_guide` - Code patterns for common tasks
- `get_available_workflows` - List all workflow types

### Asset Integration (Keep from v1)
- Polyhaven tools
- Sketchfab tools
- Hyper3D/Rodin tools
- Hunyuan3D tools

### DEPRECATE: Primitive Tools
These can remain for backwards compatibility but should not be promoted:
- `add_node`, `remove_node`, `connect_nodes`, `set_node_value`
- `add_modifier`, `remove_modifier`, `apply_modifier`
- `add_primitive`, `transform_object`, `delete_object`
- etc.

The AI will use `execute_blender_code` with self-generated Python instead.

---

## Implementation Priority

### Phase 1: Enhance Context
1. Improve `get_full_context` with more structured data
2. Add `get_workflow_guide` tool
3. Update app_prompts with workflow guidance

### Phase 2: Database
1. Update unified_commands with workflow-oriented descriptions
2. Update app_prompts table

### Phase 3: Testing
1. Test voice commands generate proper workflow code
2. Test self-healing on common errors
3. Test context polling speed

### Phase 4: Documentation
1. Document workflow patterns for users
2. Create voice command examples

---

## Summary

**v1 Mistake**: Creating 48 primitive tools that mirror Blender's API
**v2 Insight**: AI generates code anyway - give it better context and guidance

The power is in:
1. **Rich context** so AI understands the scene
2. **Workflow guides** so AI knows best practices
3. **Self-healing** so errors get fixed automatically
4. **One core tool** (`execute_blender_code`) that does everything

The AI is the intelligence - we just need to feed it the right information.
