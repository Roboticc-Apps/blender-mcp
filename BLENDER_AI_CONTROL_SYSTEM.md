# Blender AI Control System - Complete Implementation Plan

## Document Purpose

This document is the **complete specification** for building a production-ready, professional-quality AI control system for Blender. It is designed to be self-contained - if context is compacted, this document alone should provide all information needed to implement the system.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture](#2-architecture)
3. [Component Specifications](#3-component-specifications)
4. [API Reference](#4-api-reference)
5. [Implementation Phases](#5-implementation-phases)
6. [File Structure](#6-file-structure)
7. [Detailed Implementation Guide](#7-detailed-implementation-guide)
8. [Testing Strategy](#8-testing-strategy)
9. [Integration with OneController](#9-integration-with-onecontroller)

---

## 1. System Overview

### 1.1 Vision

Transform Blender from a complex manual tool into a **voice-controllable creative environment** where:
- Users speak natural commands ("add a glass material with blue tint")
- AI understands context (current editor, selection, mode)
- System executes multi-step operations automatically
- Errors self-heal with AI-powered corrections

### 1.2 Current State (What Exists)

**Blender MCP Addon** (`addon.py`):
- Socket server on port 9876
- Basic handlers: `get_scene_info`, `get_object_info`, `execute_code`
- Asset integrations: PolyHaven, Sketchfab, Hyper3D
- Self-healing error handling (returns errors, doesn't raise exceptions)

**OneController Backend** (`action_router.py`):
- Routes voice commands to MCP tools
- Self-healing retry with AI fix (sends error context back to AI)
- WebSocket notifications to frontend

### 1.3 Target State (What We're Building)

| Capability | Current | Target |
|------------|---------|--------|
| Context Awareness | Scene info only | Full UI state, nodes, modifiers, viewport |
| Command Types | Raw Python execution | High-level semantic actions |
| Error Handling | Basic retry | Intelligent self-healing with context |
| Multi-Step | Single operations | Sequenced workflows |
| Node Control | Via code only | Direct node inspection/manipulation |
| UI Control | None | Editor switching, viewport modes |

---

## 2. Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           VOICE INPUT                                    │
│                    (Whisper/Speech Recognition)                          │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      ONECONTROLLER BACKEND                               │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ Command Detection Service (detect-voice-command Edge Function)  │    │
│  │ • Understands natural language                                   │    │
│  │ • Has access to Blender context (sent with each request)        │    │
│  │ • Generates structured actions (not just raw code)              │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ Action Router                                                    │    │
│  │ • Routes actions to Blender MCP                                 │    │
│  │ • Handles self-healing retry                                    │    │
│  │ • Manages multi-step sequences                                  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │ MCP Protocol (JSON over TCP)
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       BLENDER MCP ADDON                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────────────┐  │
│  │ Context Layer    │  │ Action Layer     │  │ Execution Layer       │  │
│  │ • get_context()  │  │ • switch_editor  │  │ • execute_code        │  │
│  │ • get_nodes()    │  │ • add_node       │  │ • execute_sequence    │  │
│  │ • get_viewport() │  │ • set_material   │  │ • validate_context    │  │
│  │ • get_modifiers()│  │ • add_modifier   │  │ • handle_error        │  │
│  └──────────────────┘  └──────────────────┘  └───────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         BLENDER APPLICATION                              │
│                    (bpy API - Full Python Access)                        │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow

```
1. User: "Add a glass shader with IOR 1.5"
                    │
2. OneController:   │ Transcription
                    ▼
3. Backend calls:   get_blender_context() → Returns current UI state
                    │
4. Edge Function:   Receives text + context
                    │ AI understands: Node editor active, material selected
                    ▼
5. AI generates:    {
                      "command": "BLENDER_ACTION",
                      "execution_mode": "single_shot",
                      "actions": [
                        {"action": "add_node", "type": "ShaderNodeBsdfGlass"},
                        {"action": "set_node_value", "node": "Glass BSDF", "input": "IOR", "value": 1.5},
                        {"action": "connect_nodes", "from": "Glass BSDF:BSDF", "to": "Material Output:Surface"}
                      ]
                    }
                    │
6. Action Router:   Sends to Blender MCP via blender-mcp server
                    │
7. Blender MCP:     Executes each action, returns success/error
                    │
8. If error:        Self-healing retry with error context → AI fixes
                    │
9. Notification:    "Glass shader created with IOR 1.5"
```

---

## 3. Component Specifications

### 3.1 Context Layer (New Handlers)

These handlers gather rich context from Blender to send to AI.

#### 3.1.1 `get_full_context`

Returns complete UI and scene state for AI decision-making.

```python
def get_full_context(self):
    """
    Returns comprehensive Blender context for AI.
    This is called BEFORE each voice command to give AI full awareness.
    """
    return {
        # Current editor state
        "editor": {
            "type": self._get_active_editor_type(),      # 'VIEW_3D', 'NODE_EDITOR', etc.
            "mode": bpy.context.mode,                     # 'OBJECT', 'EDIT_MESH', 'SCULPT'
            "active_tool": self._get_active_tool(),       # Current tool name
        },

        # 3D Viewport state (if in 3D view)
        "viewport": {
            "shading_type": None,      # 'WIREFRAME', 'SOLID', 'MATERIAL', 'RENDERED'
            "shading_light": None,     # 'STUDIO', 'MATCAP', 'FLAT'
            "show_overlays": None,     # Boolean
            "is_camera_view": None,    # Boolean
            "view_perspective": None,  # 'PERSP', 'ORTHO', 'CAMERA'
        },

        # Node editor state (if in node editor)
        "node_editor": {
            "tree_type": None,         # 'ShaderNodeTree', 'GeometryNodeTree', 'CompositorNodeTree'
            "active_material": None,   # Material name if shader nodes
            "active_node": None,       # Currently selected node name
            "node_count": None,        # Total nodes in tree
        },

        # Selection state
        "selection": {
            "active_object": None,     # Name of active object
            "active_object_type": None,# 'MESH', 'CAMERA', 'LIGHT', etc.
            "selected_objects": [],    # List of selected object names
            "selected_count": 0,
            # Edit mode specifics
            "selected_vertices": 0,
            "selected_edges": 0,
            "selected_faces": 0,
        },

        # Scene state
        "scene": {
            "name": None,
            "frame_current": 0,
            "frame_start": 0,
            "frame_end": 250,
            "render_engine": None,     # 'CYCLES', 'BLENDER_EEVEE', etc.
            "active_camera": None,
        },

        # Available objects (for reference)
        "objects": {
            "count": 0,
            "meshes": [],              # List of mesh object names
            "cameras": [],
            "lights": [],
            "empties": [],
            "armatures": [],
        },

        # Available materials
        "materials": [],               # List of material names

        # Modifiers on active object
        "modifiers": [],               # [{name, type}, ...]
    }
```

#### 3.1.2 `get_node_tree`

Returns detailed node tree structure for the AI to understand and manipulate.

```python
def get_node_tree(self, material_name=None, tree_type="shader"):
    """
    Get complete node tree structure.

    Args:
        material_name: Material name for shader nodes (None = active material)
        tree_type: 'shader', 'geometry', 'compositor', 'world'

    Returns:
        {
            "tree_type": "ShaderNodeTree",
            "material": "Material.001",
            "nodes": [
                {
                    "name": "Principled BSDF",
                    "type": "ShaderNodeBsdfPrincipled",
                    "location": [0, 0],
                    "inputs": [
                        {"name": "Base Color", "type": "RGBA", "value": [0.8, 0.8, 0.8, 1.0], "is_linked": false},
                        {"name": "Metallic", "type": "VALUE", "value": 0.0, "is_linked": false},
                        ...
                    ],
                    "outputs": [
                        {"name": "BSDF", "type": "SHADER", "is_linked": true}
                    ]
                },
                ...
            ],
            "links": [
                {"from_node": "Principled BSDF", "from_socket": "BSDF", "to_node": "Material Output", "to_socket": "Surface"},
                ...
            ]
        }
    """
```

#### 3.1.3 `get_modifier_stack`

Returns all modifiers on an object with their settings.

```python
def get_modifier_stack(self, object_name=None):
    """
    Get modifier stack for an object.

    Args:
        object_name: Object name (None = active object)

    Returns:
        {
            "object": "Cube",
            "modifiers": [
                {
                    "name": "Subdivision",
                    "type": "SUBSURF",
                    "show_viewport": true,
                    "show_render": true,
                    "settings": {
                        "levels": 2,
                        "render_levels": 3,
                        "subdivision_type": "CATMULL_CLARK"
                    }
                },
                {
                    "name": "Bevel",
                    "type": "BEVEL",
                    "settings": {
                        "width": 0.02,
                        "segments": 3,
                        "limit_method": "ANGLE"
                    }
                }
            ]
        }
    """
```

#### 3.1.4 `get_viewport_state`

Returns current 3D viewport configuration.

```python
def get_viewport_state(self):
    """
    Get current 3D viewport state.

    Returns:
        {
            "shading": {
                "type": "SOLID",           # WIREFRAME, SOLID, MATERIAL, RENDERED
                "light": "STUDIO",         # STUDIO, MATCAP, FLAT
                "color_type": "MATERIAL",  # MATERIAL, SINGLE, OBJECT, RANDOM, VERTEX, TEXTURE
                "show_xray": false,
                "show_shadows": true,
                "show_cavity": false
            },
            "overlay": {
                "show_overlays": true,
                "show_floor": true,
                "show_axis_x": true,
                "show_axis_y": true,
                "show_wireframes": false,
                "show_face_orientation": false
            },
            "view": {
                "perspective": "PERSP",    # PERSP, ORTHO, CAMERA
                "camera_name": null,       # If in camera view
                "lens": 50,
                "clip_start": 0.1,
                "clip_end": 1000
            }
        }
    """
```

### 3.2 Action Layer (High-Level Commands)

These handlers execute semantic actions without needing raw Python code.

#### 3.2.1 UI Control Actions

```python
# Handler: switch_editor
def switch_editor(self, editor_type, tree_type=None):
    """
    Switch the current editor type.

    Args:
        editor_type: 'VIEW_3D', 'NODE_EDITOR', 'PROPERTIES', 'OUTLINER',
                     'UV', 'IMAGE_EDITOR', 'SEQUENCE_EDITOR', 'GRAPH_EDITOR',
                     'DOPESHEET', 'NLA_EDITOR', 'TEXT_EDITOR', 'CONSOLE'
        tree_type: For NODE_EDITOR: 'ShaderNodeTree', 'GeometryNodeTree',
                   'CompositorNodeTree', 'TextureNodeTree'

    Returns:
        {"success": true} or {"error": "message"}
    """

# Handler: set_viewport_shading
def set_viewport_shading(self, shading_type, light=None, color_type=None):
    """
    Set 3D viewport shading mode.

    Args:
        shading_type: 'WIREFRAME', 'SOLID', 'MATERIAL', 'RENDERED'
        light: 'STUDIO', 'MATCAP', 'FLAT' (for SOLID mode)
        color_type: 'MATERIAL', 'SINGLE', 'OBJECT', 'RANDOM', 'VERTEX', 'TEXTURE'
    """

# Handler: set_viewport_overlay
def set_viewport_overlay(self, show_overlays=None, show_wireframes=None,
                          show_floor=None, show_axis_x=None, show_axis_y=None):
    """Toggle viewport overlays."""

# Handler: set_view_angle
def set_view_angle(self, view):
    """
    Set 3D viewport view angle.

    Args:
        view: 'FRONT', 'BACK', 'LEFT', 'RIGHT', 'TOP', 'BOTTOM', 'CAMERA', 'PERSP', 'ORTHO'
    """
```

#### 3.2.2 Node Actions

```python
# Handler: add_node
def add_node(self, node_type, location=None, material=None):
    """
    Add a node to the current node tree.

    Args:
        node_type: Blender node type (e.g., 'ShaderNodeBsdfPrincipled', 'ShaderNodeTexImage')
        location: [x, y] coordinates (optional, auto-positioned if None)
        material: Material name (optional, uses active if None)

    Returns:
        {"success": true, "node_name": "Principled BSDF"} or {"error": "message"}
    """

# Handler: remove_node
def remove_node(self, node_name, material=None):
    """Remove a node by name."""

# Handler: set_node_value
def set_node_value(self, node_name, input_name, value, material=None):
    """
    Set a node input value.

    Args:
        node_name: Name of the node
        input_name: Name of the input socket (e.g., 'Base Color', 'Metallic')
        value: Value to set (number, [r,g,b,a], etc.)
        material: Material name (optional)

    Examples:
        set_node_value("Principled BSDF", "Metallic", 1.0)
        set_node_value("Principled BSDF", "Base Color", [1.0, 0.0, 0.0, 1.0])
    """

# Handler: connect_nodes
def connect_nodes(self, from_node, from_socket, to_node, to_socket, material=None):
    """
    Connect two nodes.

    Args:
        from_node: Source node name
        from_socket: Source output socket name
        to_node: Destination node name
        to_socket: Destination input socket name

    Example:
        connect_nodes("Glass BSDF", "BSDF", "Material Output", "Surface")
    """

# Handler: disconnect_node
def disconnect_node(self, node_name, socket_name, socket_type="input", material=None):
    """Disconnect a node socket."""

# Handler: create_material
def create_material(self, name, assign_to_active=True):
    """
    Create a new material.

    Args:
        name: Material name
        assign_to_active: Assign to active object

    Returns:
        {"success": true, "material_name": "Glass"}
    """
```

#### 3.2.3 Modifier Actions

```python
# Handler: add_modifier
def add_modifier(self, modifier_type, name=None, object_name=None, settings=None):
    """
    Add a modifier to an object.

    Args:
        modifier_type: 'SUBSURF', 'BEVEL', 'BOOLEAN', 'MIRROR', 'ARRAY',
                       'SOLIDIFY', 'DECIMATE', 'REMESH', 'SMOOTH', etc.
        name: Custom modifier name (optional)
        object_name: Target object (optional, uses active if None)
        settings: Dict of modifier settings (optional)

    Example:
        add_modifier("SUBSURF", settings={"levels": 2, "render_levels": 3})
        add_modifier("BEVEL", settings={"width": 0.02, "segments": 3})
    """

# Handler: remove_modifier
def remove_modifier(self, modifier_name, object_name=None):
    """Remove a modifier by name."""

# Handler: apply_modifier
def apply_modifier(self, modifier_name, object_name=None):
    """Apply a modifier (make it permanent)."""

# Handler: set_modifier_settings
def set_modifier_settings(self, modifier_name, settings, object_name=None):
    """
    Update modifier settings.

    Args:
        modifier_name: Name of the modifier
        settings: Dict of settings to update
        object_name: Target object (optional)

    Example:
        set_modifier_settings("Subdivision", {"levels": 3})
    """

# Handler: reorder_modifier
def reorder_modifier(self, modifier_name, direction, object_name=None):
    """
    Move modifier up or down in stack.

    Args:
        modifier_name: Name of modifier
        direction: 'UP' or 'DOWN'
    """
```

#### 3.2.4 Object Actions

```python
# Handler: select_object
def select_object(self, object_name, extend=False, active=True):
    """
    Select an object.

    Args:
        object_name: Name of object to select
        extend: Add to selection (don't deselect others)
        active: Make this the active object
    """

# Handler: select_all
def select_all(self, action="SELECT"):
    """
    Select or deselect all objects.

    Args:
        action: 'SELECT', 'DESELECT', 'INVERT', 'TOGGLE'
    """

# Handler: set_mode
def set_mode(self, mode, object_name=None):
    """
    Set object mode.

    Args:
        mode: 'OBJECT', 'EDIT', 'SCULPT', 'VERTEX_PAINT', 'WEIGHT_PAINT', 'TEXTURE_PAINT'
        object_name: Target object (optional)
    """

# Handler: add_primitive
def add_primitive(self, primitive_type, location=None, size=None, name=None):
    """
    Add a primitive mesh object.

    Args:
        primitive_type: 'CUBE', 'SPHERE', 'CYLINDER', 'CONE', 'TORUS', 'PLANE',
                        'CIRCLE', 'GRID', 'MONKEY', 'EMPTY', 'CAMERA', 'LIGHT'
        location: [x, y, z] (optional)
        size: Size or radius (optional)
        name: Custom name (optional)
    """

# Handler: transform_object
def transform_object(self, object_name=None, location=None, rotation=None, scale=None):
    """
    Transform an object.

    Args:
        object_name: Target object (optional, uses active if None)
        location: [x, y, z] absolute position
        rotation: [x, y, z] rotation in degrees
        scale: [x, y, z] or single value for uniform scale
    """

# Handler: duplicate_object
def duplicate_object(self, object_name=None, linked=False):
    """Duplicate an object."""

# Handler: delete_object
def delete_object(self, object_name=None):
    """Delete an object."""
```

#### 3.2.5 Animation Actions

```python
# Handler: set_frame
def set_frame(self, frame):
    """Set current frame."""

# Handler: set_frame_range
def set_frame_range(self, start, end):
    """Set animation frame range."""

# Handler: insert_keyframe
def insert_keyframe(self, data_path, frame=None, object_name=None):
    """
    Insert a keyframe.

    Args:
        data_path: 'location', 'rotation_euler', 'scale', or specific path
        frame: Frame number (optional, uses current frame if None)
        object_name: Target object (optional)
    """

# Handler: delete_keyframe
def delete_keyframe(self, data_path, frame=None, object_name=None):
    """Delete a keyframe."""

# Handler: play_animation
def play_animation(self):
    """Start animation playback."""

# Handler: stop_animation
def stop_animation(self):
    """Stop animation playback."""
```

#### 3.2.6 Camera Actions

```python
# Handler: set_active_camera
def set_active_camera(self, camera_name):
    """Set scene active camera."""

# Handler: frame_selected
def frame_selected(self):
    """Frame selected objects in viewport."""

# Handler: camera_to_view
def camera_to_view(self):
    """Move camera to current view."""

# Handler: set_camera_settings
def set_camera_settings(self, lens=None, sensor_width=None, clip_start=None, clip_end=None, camera_name=None):
    """Update camera settings."""
```

#### 3.2.7 Render Actions

```python
# Handler: set_render_engine
def set_render_engine(self, engine):
    """
    Set render engine.

    Args:
        engine: 'CYCLES', 'BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT', 'BLENDER_WORKBENCH'
    """

# Handler: set_render_settings
def set_render_settings(self, resolution_x=None, resolution_y=None,
                         resolution_percentage=None, samples=None):
    """Update render settings."""

# Handler: render_image
def render_image(self, filepath=None, open_after=False):
    """Render current frame to image."""
```

### 3.3 Execution Layer

#### 3.3.1 `execute_code` (Existing, Enhanced)

```python
def execute_code(self, code):
    """
    Execute arbitrary Blender Python code.
    Used as fallback when no high-level action exists.

    Args:
        code: Python code string

    Returns:
        {"executed": true, "result": "stdout output"} or
        {"executed": false, "error": "error message"}

    Note: Errors are returned, not raised. This enables self-healing retry.
    """
```

#### 3.3.2 `execute_action_sequence` (New)

```python
def execute_action_sequence(self, actions):
    """
    Execute a sequence of high-level actions atomically.

    Args:
        actions: List of action dicts
        [
            {"action": "add_node", "node_type": "ShaderNodeBsdfGlass"},
            {"action": "set_node_value", "node_name": "Glass BSDF", "input_name": "IOR", "value": 1.5},
            {"action": "connect_nodes", "from_node": "Glass BSDF", ...}
        ]

    Returns:
        {
            "success": true,
            "completed_actions": 3,
            "results": [
                {"action": "add_node", "success": true, "node_name": "Glass BSDF"},
                {"action": "set_node_value", "success": true},
                {"action": "connect_nodes", "success": true}
            ]
        }
        or
        {
            "success": false,
            "completed_actions": 1,
            "failed_at": 2,
            "error": "Node 'Glass BSDF' not found",
            "results": [...]
        }
    """
```

#### 3.3.3 `validate_context` (New)

```python
def validate_context(self, required_context):
    """
    Validate that current Blender state matches requirements.
    Used before executing actions that need specific context.

    Args:
        required_context: Dict of requirements
        {
            "editor": "NODE_EDITOR",           # Required editor type
            "mode": "OBJECT",                  # Required mode
            "has_active_object": true,         # Must have active object
            "active_object_type": "MESH",      # Active object must be mesh
            "has_material": true,              # Active object must have material
        }

    Returns:
        {"valid": true} or
        {"valid": false, "missing": ["has_material"], "message": "Active object has no material"}
    """
```

---

## 4. API Reference

### 4.1 MCP Tool Manifest (Updated)

The Blender MCP exposes these tools to OneController:

```json
{
  "name": "blender-mcp",
  "version": "2.0.0",
  "tools": [
    {
      "name": "get_full_context",
      "description": "Get comprehensive Blender UI and scene state for AI context awareness"
    },
    {
      "name": "get_node_tree",
      "description": "Get complete node tree structure with all nodes, connections, and values",
      "parameters": {
        "material_name": "optional string - material name (uses active if omitted)",
        "tree_type": "optional string - 'shader', 'geometry', 'compositor', 'world'"
      }
    },
    {
      "name": "get_modifier_stack",
      "description": "Get all modifiers on an object with their settings",
      "parameters": {
        "object_name": "optional string - object name (uses active if omitted)"
      }
    },
    {
      "name": "switch_editor",
      "description": "Switch the current editor type",
      "parameters": {
        "editor_type": "required string - VIEW_3D, NODE_EDITOR, etc.",
        "tree_type": "optional string - for NODE_EDITOR: ShaderNodeTree, etc."
      }
    },
    {
      "name": "set_viewport_shading",
      "description": "Set 3D viewport shading mode",
      "parameters": {
        "shading_type": "required string - WIREFRAME, SOLID, MATERIAL, RENDERED"
      }
    },
    {
      "name": "add_node",
      "description": "Add a node to the current node tree",
      "parameters": {
        "node_type": "required string - e.g., ShaderNodeBsdfPrincipled",
        "location": "optional [x, y] - node position"
      }
    },
    {
      "name": "set_node_value",
      "description": "Set a node input value",
      "parameters": {
        "node_name": "required string - node name",
        "input_name": "required string - input socket name",
        "value": "required - value to set"
      }
    },
    {
      "name": "connect_nodes",
      "description": "Connect two nodes",
      "parameters": {
        "from_node": "required string",
        "from_socket": "required string",
        "to_node": "required string",
        "to_socket": "required string"
      }
    },
    {
      "name": "add_modifier",
      "description": "Add a modifier to an object",
      "parameters": {
        "modifier_type": "required string - SUBSURF, BEVEL, etc.",
        "settings": "optional object - modifier settings"
      }
    },
    {
      "name": "execute_action_sequence",
      "description": "Execute a sequence of actions atomically",
      "parameters": {
        "actions": "required array - list of action objects"
      }
    },
    {
      "name": "execute_blender_code",
      "description": "Execute arbitrary Python code in Blender (fallback)",
      "parameters": {
        "code": "required string - Python code"
      }
    }
  ]
}
```

### 4.2 Command Format from AI

The Edge Function (detect-voice-command) should return structured commands:

```json
{
  "command": "BLENDER_ACTION",
  "execution_mode": "single_shot",
  "tool_type": "mcp",
  "server": "blender-mcp",

  // Option A: Single high-level action
  "tool_name": "add_modifier",
  "tool_parameters": {
    "modifier_type": "SUBSURF",
    "settings": {"levels": 2}
  },

  // Option B: Multi-step sequence
  "tool_name": "execute_action_sequence",
  "tool_parameters": {
    "actions": [
      {"action": "create_material", "name": "Glass"},
      {"action": "add_node", "node_type": "ShaderNodeBsdfGlass"},
      {"action": "connect_nodes", "from_node": "Glass BSDF", "from_socket": "BSDF", "to_node": "Material Output", "to_socket": "Surface"},
      {"action": "set_node_value", "node_name": "Glass BSDF", "input_name": "IOR", "value": 1.5}
    ]
  },

  // Option C: Raw code (fallback)
  "tool_name": "execute_blender_code",
  "tool_parameters": {
    "code": "import bpy\nbpy.ops.mesh.primitive_cube_add()"
  }
}
```

---

## 5. Implementation Phases

### Phase 1: Context Layer (Foundation)
**Goal**: Give AI full awareness of Blender state
**Files**: `addon.py`
**Time**: 2-3 hours

1. Implement `get_full_context()` handler
2. Implement `get_node_tree()` handler
3. Implement `get_modifier_stack()` handler
4. Implement `get_viewport_state()` handler
5. Update handler registry
6. Test context gathering

### Phase 2: UI Control Actions
**Goal**: Control editor layout and viewport
**Files**: `addon.py`
**Time**: 1-2 hours

1. Implement `switch_editor()` handler
2. Implement `set_viewport_shading()` handler
3. Implement `set_viewport_overlay()` handler
4. Implement `set_view_angle()` handler
5. Test UI control

### Phase 3: Node Actions
**Goal**: Full node tree manipulation
**Files**: `addon.py`
**Time**: 2-3 hours

1. Implement `add_node()` handler
2. Implement `remove_node()` handler
3. Implement `set_node_value()` handler
4. Implement `connect_nodes()` handler
5. Implement `disconnect_node()` handler
6. Implement `create_material()` handler
7. Test node operations

### Phase 4: Modifier Actions
**Goal**: Full modifier stack control
**Files**: `addon.py`
**Time**: 1-2 hours

1. Implement `add_modifier()` handler
2. Implement `remove_modifier()` handler
3. Implement `apply_modifier()` handler
4. Implement `set_modifier_settings()` handler
5. Test modifier operations

### Phase 5: Object & Animation Actions
**Goal**: Object manipulation and animation
**Files**: `addon.py`
**Time**: 2 hours

1. Implement object actions (select, transform, delete, duplicate)
2. Implement animation actions (keyframe, playback)
3. Implement camera actions
4. Test object and animation operations

### Phase 6: Action Sequencing
**Goal**: Multi-step atomic operations
**Files**: `addon.py`
**Time**: 1-2 hours

1. Implement `execute_action_sequence()` handler
2. Implement `validate_context()` helper
3. Add rollback support for failed sequences
4. Test multi-step operations

### Phase 7: Edge Function Update
**Goal**: AI understands new capabilities
**Files**: `detect-voice-command` Edge Function
**Time**: 2-3 hours

1. Update system prompt with new Blender actions
2. Add context injection (send `get_full_context()` with each request)
3. Update output format for action sequences
4. Add node type reference for AI
5. Test AI command generation

### Phase 8: Integration & Testing
**Goal**: End-to-end voice control
**Files**: `action_router.py`, `addon.py`
**Time**: 2-3 hours

1. Update action router for new handlers
2. Add context fetching before command detection
3. Test self-healing with new actions
4. End-to-end voice testing
5. Performance optimization

---

## 6. File Structure

```
blender-mcp/
├── addon.py                      # Main addon (all handlers here)
├── dist/
│   ├── blender_mcp_addon.py     # Built addon for distribution
│   └── manifest.json             # MCP manifest
├── src/
│   └── blender_mcp/
│       └── server.py             # MCP server (Python side)
├── BLENDER_AI_CONTROL_SYSTEM.md  # This document
├── build_simple.ps1              # Build script
└── pyproject.toml                # Package config

one_controller/backend/
├── action_router.py              # Routes actions (update for Blender context)
├── command_detection_service.py  # Calls Edge Function (update for context injection)
└── mcp_manager.py                # Manages MCP connections

supabase/functions/
└── detect-voice-command/
    ├── index.ts                  # Main handler (update for Blender context)
    ├── command-detector.ts       # AI command detection (update prompts)
    ├── types.ts                  # TypeScript types (add Blender types)
    └── blender-actions.ts        # NEW: Blender action reference for AI
```

---

## 7. Detailed Implementation Guide

### 7.1 Phase 1: Context Layer

Add these methods to `BlenderMCPServer` class in `addon.py`:

```python
# === CONTEXT LAYER ===

def get_full_context(self):
    """Get comprehensive Blender context for AI."""
    try:
        context = {
            "editor": self._get_editor_context(),
            "viewport": self._get_viewport_context(),
            "node_editor": self._get_node_editor_context(),
            "selection": self._get_selection_context(),
            "scene": self._get_scene_context(),
            "objects": self._get_objects_summary(),
            "materials": [m.name for m in bpy.data.materials],
            "modifiers": self._get_active_modifiers(),
        }
        return context
    except Exception as e:
        return {"error": str(e)}

def _get_editor_context(self):
    """Get current editor state."""
    area = bpy.context.area
    return {
        "type": area.type if area else None,
        "mode": bpy.context.mode,
        "active_tool": self._get_active_tool_name(),
    }

def _get_active_tool_name(self):
    """Get name of active tool."""
    try:
        workspace = bpy.context.workspace
        tool = workspace.tools.from_space_view3d_mode(bpy.context.mode, create=False)
        return tool.idname if tool else None
    except:
        return None

def _get_viewport_context(self):
    """Get 3D viewport state."""
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    return {
                        "shading_type": space.shading.type,
                        "shading_light": space.shading.light,
                        "show_overlays": space.overlay.show_overlays,
                        "is_camera_view": space.region_3d.view_perspective == 'CAMERA' if space.region_3d else False,
                        "view_perspective": space.region_3d.view_perspective if space.region_3d else None,
                    }
    return None

def _get_node_editor_context(self):
    """Get node editor state."""
    for area in bpy.context.screen.areas:
        if area.type == 'NODE_EDITOR':
            for space in area.spaces:
                if space.type == 'NODE_EDITOR':
                    tree = space.node_tree
                    return {
                        "tree_type": space.tree_type,
                        "active_material": bpy.context.active_object.active_material.name if bpy.context.active_object and bpy.context.active_object.active_material else None,
                        "active_node": tree.nodes.active.name if tree and tree.nodes.active else None,
                        "node_count": len(tree.nodes) if tree else 0,
                    }
    return None

def _get_selection_context(self):
    """Get selection state."""
    obj = bpy.context.active_object
    result = {
        "active_object": obj.name if obj else None,
        "active_object_type": obj.type if obj else None,
        "selected_objects": [o.name for o in bpy.context.selected_objects],
        "selected_count": len(bpy.context.selected_objects),
        "selected_vertices": 0,
        "selected_edges": 0,
        "selected_faces": 0,
    }

    # Get edit mode selection counts
    if obj and obj.type == 'MESH' and bpy.context.mode == 'EDIT_MESH':
        bm = bmesh.from_edit_mesh(obj.data)
        result["selected_vertices"] = len([v for v in bm.verts if v.select])
        result["selected_edges"] = len([e for e in bm.edges if e.select])
        result["selected_faces"] = len([f for f in bm.faces if f.select])

    return result

def _get_scene_context(self):
    """Get scene state."""
    scene = bpy.context.scene
    return {
        "name": scene.name,
        "frame_current": scene.frame_current,
        "frame_start": scene.frame_start,
        "frame_end": scene.frame_end,
        "render_engine": scene.render.engine,
        "active_camera": scene.camera.name if scene.camera else None,
    }

def _get_objects_summary(self):
    """Get summary of scene objects."""
    objects = bpy.context.scene.objects
    return {
        "count": len(objects),
        "meshes": [o.name for o in objects if o.type == 'MESH'],
        "cameras": [o.name for o in objects if o.type == 'CAMERA'],
        "lights": [o.name for o in objects if o.type == 'LIGHT'],
        "empties": [o.name for o in objects if o.type == 'EMPTY'],
        "armatures": [o.name for o in objects if o.type == 'ARMATURE'],
    }

def _get_active_modifiers(self):
    """Get modifiers on active object."""
    obj = bpy.context.active_object
    if not obj:
        return []
    return [{"name": m.name, "type": m.type} for m in obj.modifiers]


def get_node_tree(self, material_name=None, tree_type="shader"):
    """Get complete node tree structure."""
    try:
        # Determine which node tree to get
        if tree_type == "shader":
            if material_name:
                mat = bpy.data.materials.get(material_name)
            else:
                obj = bpy.context.active_object
                mat = obj.active_material if obj else None

            if not mat or not mat.use_nodes:
                return {"error": "No material with nodes found"}

            tree = mat.node_tree
            material = mat.name
        elif tree_type == "geometry":
            # Get from active modifier
            obj = bpy.context.active_object
            for mod in obj.modifiers:
                if mod.type == 'NODES' and mod.node_group:
                    tree = mod.node_group
                    material = None
                    break
            else:
                return {"error": "No geometry nodes modifier found"}
        elif tree_type == "compositor":
            tree = bpy.context.scene.node_tree
            material = None
        else:
            return {"error": f"Unknown tree_type: {tree_type}"}

        # Build node data
        nodes = []
        for node in tree.nodes:
            node_data = {
                "name": node.name,
                "type": node.bl_idname,
                "label": node.label,
                "location": [node.location.x, node.location.y],
                "inputs": [],
                "outputs": [],
            }

            # Get inputs
            for inp in node.inputs:
                inp_data = {
                    "name": inp.name,
                    "type": inp.type,
                    "is_linked": inp.is_linked,
                }
                # Get default value if not linked
                if not inp.is_linked and hasattr(inp, 'default_value'):
                    val = inp.default_value
                    if hasattr(val, '__iter__') and not isinstance(val, str):
                        inp_data["value"] = list(val)
                    else:
                        inp_data["value"] = val
                node_data["inputs"].append(inp_data)

            # Get outputs
            for out in node.outputs:
                node_data["outputs"].append({
                    "name": out.name,
                    "type": out.type,
                    "is_linked": out.is_linked,
                })

            nodes.append(node_data)

        # Build link data
        links = []
        for link in tree.links:
            links.append({
                "from_node": link.from_node.name,
                "from_socket": link.from_socket.name,
                "to_node": link.to_node.name,
                "to_socket": link.to_socket.name,
            })

        return {
            "tree_type": tree_type,
            "material": material,
            "nodes": nodes,
            "links": links,
        }
    except Exception as e:
        return {"error": str(e)}


def get_modifier_stack(self, object_name=None):
    """Get modifier stack for an object."""
    try:
        if object_name:
            obj = bpy.data.objects.get(object_name)
        else:
            obj = bpy.context.active_object

        if not obj:
            return {"error": "No object found"}

        modifiers = []
        for mod in obj.modifiers:
            mod_data = {
                "name": mod.name,
                "type": mod.type,
                "show_viewport": mod.show_viewport,
                "show_render": mod.show_render,
                "settings": {},
            }

            # Get common settings based on modifier type
            if mod.type == 'SUBSURF':
                mod_data["settings"] = {
                    "levels": mod.levels,
                    "render_levels": mod.render_levels,
                    "subdivision_type": mod.subdivision_type,
                }
            elif mod.type == 'BEVEL':
                mod_data["settings"] = {
                    "width": mod.width,
                    "segments": mod.segments,
                    "limit_method": mod.limit_method,
                }
            elif mod.type == 'BOOLEAN':
                mod_data["settings"] = {
                    "operation": mod.operation,
                    "object": mod.object.name if mod.object else None,
                }
            elif mod.type == 'MIRROR':
                mod_data["settings"] = {
                    "use_axis": [mod.use_axis[0], mod.use_axis[1], mod.use_axis[2]],
                    "use_clip": mod.use_clip,
                }
            elif mod.type == 'ARRAY':
                mod_data["settings"] = {
                    "count": mod.count,
                    "use_relative_offset": mod.use_relative_offset,
                    "relative_offset_displace": list(mod.relative_offset_displace),
                }
            elif mod.type == 'SOLIDIFY':
                mod_data["settings"] = {
                    "thickness": mod.thickness,
                    "offset": mod.offset,
                }
            # Add more modifier types as needed

            modifiers.append(mod_data)

        return {
            "object": obj.name,
            "modifiers": modifiers,
        }
    except Exception as e:
        return {"error": str(e)}
```

### 7.2 Update Handler Registry

In the `_execute_command_internal` method, update the handlers dict:

```python
handlers = {
    # Existing handlers
    "get_scene_info": self.get_scene_info,
    "get_object_info": self.get_object_info,
    "get_viewport_screenshot": self.get_viewport_screenshot,
    "execute_code": self.execute_code,

    # NEW: Context handlers
    "get_full_context": self.get_full_context,
    "get_node_tree": self.get_node_tree,
    "get_modifier_stack": self.get_modifier_stack,
    "get_viewport_state": self.get_viewport_state,

    # NEW: UI control handlers
    "switch_editor": self.switch_editor,
    "set_viewport_shading": self.set_viewport_shading,
    "set_view_angle": self.set_view_angle,

    # NEW: Node handlers
    "add_node": self.add_node,
    "remove_node": self.remove_node,
    "set_node_value": self.set_node_value,
    "connect_nodes": self.connect_nodes,
    "create_material": self.create_material,

    # NEW: Modifier handlers
    "add_modifier": self.add_modifier,
    "remove_modifier": self.remove_modifier,
    "apply_modifier": self.apply_modifier,
    "set_modifier_settings": self.set_modifier_settings,

    # NEW: Object handlers
    "select_object": self.select_object,
    "set_mode": self.set_mode,
    "add_primitive": self.add_primitive,
    "transform_object": self.transform_object,

    # NEW: Animation handlers
    "set_frame": self.set_frame,
    "insert_keyframe": self.insert_keyframe,

    # NEW: Sequence execution
    "execute_action_sequence": self.execute_action_sequence,
}
```

---

## 8. Testing Strategy

### 8.1 Unit Tests (Context Layer)

```python
# Test get_full_context returns expected structure
def test_get_full_context():
    result = server.get_full_context()
    assert "editor" in result
    assert "viewport" in result
    assert "selection" in result
    assert "scene" in result

# Test get_node_tree with material
def test_get_node_tree():
    # Create test material with nodes
    mat = bpy.data.materials.new("TestMat")
    mat.use_nodes = True

    result = server.get_node_tree(material_name="TestMat")
    assert "nodes" in result
    assert "links" in result
    assert len(result["nodes"]) > 0  # Should have at least Principled BSDF and Output
```

### 8.2 Integration Tests (Actions)

```python
# Test node creation
def test_add_node():
    result = server.add_node(node_type="ShaderNodeBsdfGlass")
    assert result.get("success") == True
    assert "node_name" in result

# Test modifier addition
def test_add_modifier():
    result = server.add_modifier(modifier_type="SUBSURF", settings={"levels": 2})
    assert result.get("success") == True

# Test action sequence
def test_execute_action_sequence():
    actions = [
        {"action": "create_material", "name": "TestGlass"},
        {"action": "add_node", "node_type": "ShaderNodeBsdfGlass"},
    ]
    result = server.execute_action_sequence(actions)
    assert result.get("success") == True
    assert result.get("completed_actions") == 2
```

### 8.3 Voice Command Tests

| Voice Command | Expected Action | Verification |
|---------------|-----------------|--------------|
| "Show me the shader editor" | `switch_editor("NODE_EDITOR", "ShaderNodeTree")` | Area type is NODE_EDITOR |
| "Add a subdivision modifier with 3 levels" | `add_modifier("SUBSURF", {"levels": 3})` | Modifier exists with levels=3 |
| "Make this object metallic" | `set_node_value("Principled BSDF", "Metallic", 1.0)` | Metallic value is 1.0 |
| "Connect the color to the base color" | `connect_nodes(...)` | Link exists |
| "Switch to rendered view" | `set_viewport_shading("RENDERED")` | Shading is RENDERED |

---

## 9. Integration with OneController

### 9.1 Context Injection Flow

Before calling the Edge Function for command detection:

```python
# In command_detection_service.py or action_router.py

async def detect_command_with_context(self, text: str, ...):
    # First, get Blender context
    blender_context = await self.get_blender_context()

    # Include context in Edge Function call
    payload = {
        "text": text,
        "blender_context": blender_context,  # NEW
        "mcp_tools": mcp_tools,
        "system_info": system_info,
    }

    # Call Edge Function
    response = await client.post(url, json=payload, headers=headers)

async def get_blender_context(self):
    """Fetch current Blender context via MCP."""
    try:
        result = await self.mcp_manager.call_tool(
            server="blender-mcp",
            tool="get_full_context",
            parameters={}
        )
        return result.get("result", {})
    except:
        return {}
```

### 9.2 Edge Function Prompt Update

Add to the system prompt in `command-detector.ts`:

```typescript
const BLENDER_CONTEXT_PROMPT = `
## Blender Context Awareness

When the user is working in Blender, you have access to rich context about their current state.
Use this context to make intelligent decisions:

### Available Blender Context Fields:
- editor.type: Current editor ('VIEW_3D', 'NODE_EDITOR', 'PROPERTIES', etc.)
- editor.mode: Current mode ('OBJECT', 'EDIT_MESH', 'SCULPT', etc.)
- viewport.shading_type: Viewport shading ('WIREFRAME', 'SOLID', 'MATERIAL', 'RENDERED')
- node_editor.tree_type: Node tree type ('ShaderNodeTree', 'GeometryNodeTree', etc.)
- node_editor.active_node: Currently selected node name
- selection.active_object: Active object name
- selection.selected_objects: List of selected object names
- modifiers: List of modifiers on active object

### Available Blender Actions:

**UI Control:**
- switch_editor(editor_type, tree_type?) - Switch to different editor
- set_viewport_shading(shading_type) - Change viewport shading
- set_view_angle(view) - Set view angle (FRONT, TOP, CAMERA, etc.)

**Node Operations:**
- add_node(node_type, location?) - Add node to current tree
- remove_node(node_name) - Remove a node
- set_node_value(node_name, input_name, value) - Set node input value
- connect_nodes(from_node, from_socket, to_node, to_socket) - Connect nodes
- create_material(name) - Create new material

**Modifier Operations:**
- add_modifier(modifier_type, settings?) - Add modifier
- remove_modifier(modifier_name) - Remove modifier
- apply_modifier(modifier_name) - Apply modifier
- set_modifier_settings(modifier_name, settings) - Update modifier

**Object Operations:**
- select_object(object_name, extend?) - Select object
- set_mode(mode) - Set object mode
- add_primitive(primitive_type, location?, size?) - Add primitive mesh
- transform_object(location?, rotation?, scale?) - Transform object

**Animation:**
- set_frame(frame) - Set current frame
- insert_keyframe(data_path, frame?) - Insert keyframe

**Sequences:**
- execute_action_sequence(actions[]) - Execute multiple actions atomically

### Example Command Generation:

User says: "Make this glass with IOR 1.5"
Context shows: editor.type = 'NODE_EDITOR', node_editor.tree_type = 'ShaderNodeTree'

Response:
{
  "command": "BLENDER_ACTION",
  "tool_name": "execute_action_sequence",
  "tool_parameters": {
    "actions": [
      {"action": "add_node", "node_type": "ShaderNodeBsdfGlass"},
      {"action": "set_node_value", "node_name": "Glass BSDF", "input_name": "IOR", "value": 1.5},
      {"action": "connect_nodes", "from_node": "Glass BSDF", "from_socket": "BSDF", "to_node": "Material Output", "to_socket": "Surface"}
    ]
  }
}
`;
```

### 9.3 Action Router Updates

In `action_router.py`, add handling for action sequences:

```python
async def route_blender_action(self, command_result: Dict) -> Dict:
    """Route Blender action to MCP."""
    tool_name = command_result.get("tool_name")
    tool_parameters = command_result.get("tool_parameters", {})

    # Execute via MCP
    result = await self.mcp_manager.call_tool(
        server="blender-mcp",
        tool=tool_name,
        parameters=tool_parameters
    )

    # Check for errors and potentially self-heal
    if not result.get("success") and result.get("error"):
        # Self-healing retry
        return await self._retry_with_ai_fix(...)

    return result
```

---

## Summary

This document provides a complete specification for building a production-ready Blender AI control system. Key components:

1. **Context Layer** - Rich state awareness (editor, nodes, modifiers, viewport)
2. **Action Layer** - High-level semantic commands (not just raw Python)
3. **Execution Layer** - Atomic sequences with error handling
4. **Integration** - Context injection into AI, structured output format

**Total Implementation Estimate**: 15-20 hours across 8 phases

**Priority Order**:
1. Context Layer (enables smarter AI)
2. Node Actions (most requested)
3. Modifier Actions (common workflow)
4. UI Control (quality of life)
5. Animation/Object Actions (full coverage)

With this system, voice commands like "add a glass material with blue tint and connect it" become natural multi-step operations that the AI can plan and execute intelligently.
