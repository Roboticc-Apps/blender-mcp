# Blender AI Control System v2.0

## Overview

This document provides comprehensive knowledge for AI-driven Blender control via `execute_blender_code`. The AI generates Python code dynamically based on voice commands and scene context.

**Core Principle**: One tool (`execute_blender_code`) + comprehensive knowledge = full Blender control.

---

## 1. CONTEXT UNDERSTANDING

Before generating code, understand the context provided:

### Scene Context (from `get_scene_info`)
```json
{
  "name": "Scene",
  "object_count": 5,
  "objects": [
    {"name": "Cube", "type": "MESH", "location": [0, 0, 0]},
    {"name": "Camera", "type": "CAMERA", "location": [7.4, -6.5, 5.3]}
  ],
  "materials_count": 2
}
```

### Node Tree Context (from `get_node_tree`)
```json
{
  "material": "Material",
  "nodes": [
    {"name": "Principled BSDF", "type": "ShaderNodeBsdfPrincipled", "inputs": [...], "outputs": [...]},
    {"name": "Material Output", "type": "ShaderNodeOutputMaterial"}
  ],
  "links": [
    {"from_node": "Principled BSDF", "from_socket": "BSDF", "to_node": "Material Output", "to_socket": "Surface"}
  ]
}
```

### Full Context (from `get_full_context`)
- `selection.active_object`: Currently selected object name
- `selection.selected_objects`: All selected object names
- `editor.type`: Current editor (VIEW_3D, NODE_EDITOR, etc.)
- `mode`: Current mode (OBJECT, EDIT, SCULPT, etc.)

**CRITICAL**: Use exact names from context when referencing objects, materials, or nodes.

---

## 2. OBJECT OPERATIONS

### 2.1 Access Objects

```python
import bpy

# Active (selected) object - USE THIS when user says "this", "selected", "the object"
obj = bpy.context.active_object
if not obj:
    raise ValueError("No object selected")

# Get by name (use name from context)
obj = bpy.data.objects.get("Cube")

# All objects in scene
for obj in bpy.context.scene.objects:
    print(obj.name, obj.type)

# Selected objects (multiple selection)
for obj in bpy.context.selected_objects:
    print(obj.name)
```

### 2.2 Selection

```python
# Deselect all
bpy.ops.object.select_all(action='DESELECT')

# Select object by reference
obj.select_set(True)

# Set as active
bpy.context.view_layer.objects.active = obj

# Select by name
bpy.data.objects["Cube"].select_set(True)
```

### 2.3 Create Primitives

```python
# Cube
bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0))

# Sphere (UV Sphere)
bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(0, 0, 0), segments=32, ring_count=16)

# Ico Sphere
bpy.ops.mesh.primitive_ico_sphere_add(radius=1, subdivisions=2, location=(0, 0, 0))

# Cylinder
bpy.ops.mesh.primitive_cylinder_add(radius=1, depth=2, location=(0, 0, 0), vertices=32)

# Cone
bpy.ops.mesh.primitive_cone_add(radius1=1, depth=2, location=(0, 0, 0), vertices=32)

# Torus
bpy.ops.mesh.primitive_torus_add(major_radius=1, minor_radius=0.25, location=(0, 0, 0))

# Plane
bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 0))

# Circle
bpy.ops.mesh.primitive_circle_add(radius=1, vertices=32, location=(0, 0, 0))

# Grid
bpy.ops.mesh.primitive_grid_add(x_subdivisions=10, y_subdivisions=10, size=2, location=(0, 0, 0))

# Monkey (Suzanne)
bpy.ops.mesh.primitive_monkey_add(size=2, location=(0, 0, 0))

# After creation, the new object is automatically selected and active
new_obj = bpy.context.active_object
```

### 2.4 Transforms

```python
obj = bpy.context.active_object

# Location (absolute)
obj.location = (1, 2, 3)
obj.location.x = 5
obj.location.z += 2  # Move up by 2

# Rotation (Euler radians)
import math
obj.rotation_euler = (0, 0, math.radians(45))  # 45 degrees on Z
obj.rotation_euler.z = math.radians(90)

# Scale
obj.scale = (2, 2, 2)  # Double size uniformly
obj.scale.x = 0.5  # Half width

# Apply transforms (make current transform the new default)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
```

### 2.5 Delete Objects

```python
# Delete selected
bpy.ops.object.delete()

# Delete specific object
obj = bpy.data.objects.get("Cube")
if obj:
    bpy.data.objects.remove(obj, do_unlink=True)
```

### 2.6 Duplicate

```python
# Duplicate selected
bpy.ops.object.duplicate()

# Duplicate linked (instance)
bpy.ops.object.duplicate_move_linked()

# Programmatic duplicate
import bpy
src = bpy.data.objects["Cube"]
new_obj = src.copy()
new_obj.data = src.data.copy()  # Deep copy mesh data
bpy.context.collection.objects.link(new_obj)
```

### 2.7 Parent/Child

```python
# Set parent
child = bpy.data.objects["Cube"]
parent = bpy.data.objects["Empty"]
child.parent = parent

# Clear parent
child.parent = None

# Parent with keep transform
child.parent = parent
child.matrix_parent_inverse = parent.matrix_world.inverted()
```

---

## 3. MODE OPERATIONS

```python
# Get current mode
current_mode = bpy.context.mode  # 'OBJECT', 'EDIT_MESH', 'SCULPT', etc.

# Switch modes
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.object.mode_set(mode='SCULPT')
bpy.ops.object.mode_set(mode='VERTEX_PAINT')
bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
bpy.ops.object.mode_set(mode='TEXTURE_PAINT')

# CRITICAL: Always return to object mode after edit mode operations
bpy.ops.object.mode_set(mode='EDIT')
# ... do edit mode stuff ...
bpy.ops.object.mode_set(mode='OBJECT')  # ALWAYS DO THIS
```

---

## 4. MATERIALS - PrincipledBSDFWrapper (VERIFIED FROM SOURCE)

**Source**: `bpy_extras/node_shader_utils.py` (verified)

This is the PREFERRED method for material creation.

### 4.1 Create Material with Wrapper

```python
from bpy_extras.node_shader_utils import PrincipledBSDFWrapper
import bpy

# Create new material
mat = bpy.data.materials.new(name="MyMaterial")
mat.use_nodes = True  # CRITICAL: Must enable nodes first!

# Create wrapper for easy property access
wrapper = PrincipledBSDFWrapper(mat, is_readonly=False)
```

### 4.2 PrincipledBSDFWrapper Properties (VERIFIED FROM SOURCE CODE)

These are the EXACT properties available - verified from Blender's source:

```python
# Base Color - RGB tuple (0-1), NOT RGBA!
wrapper.base_color = (0.8, 0.2, 0.1)  # Red

# Metallic - float (0-1)
wrapper.metallic = 1.0  # Full metal
wrapper.metallic = 0.0  # Non-metal

# Roughness - float (0-1)
wrapper.roughness = 0.2  # Shiny
wrapper.roughness = 0.8  # Matte

# Specular - float (0-1) - maps to "Specular IOR Level" input
wrapper.specular = 0.5

# Specular Tint - RGB color (not RGBA)
wrapper.specular_tint = (1.0, 1.0, 1.0)

# IOR (Index of Refraction) - float (0-1000)
wrapper.ior = 1.45  # Glass-like

# Transmission - float (0-1) - maps to "Transmission Weight" input
wrapper.transmission = 1.0  # Fully transparent
wrapper.transmission = 0.0  # Opaque

# Alpha - float (0-1)
wrapper.alpha = 1.0  # Fully opaque
wrapper.alpha = 0.5  # Semi-transparent

# Emission Color - RGB (not RGBA)
wrapper.emission_color = (1.0, 0.5, 0.0)  # Orange glow

# Emission Strength - float (0-1000000)
wrapper.emission_strength = 10.0  # Glowing

# Normal Map Strength - float (0-10)
wrapper.normalmap_strength = 1.0
```

### 4.3 Texture Properties (VERIFIED)

```python
# Each property has a texture variant
wrapper.base_color_texture.image = bpy.data.images.load("/path/to/albedo.png")
wrapper.roughness_texture.image = bpy.data.images.load("/path/to/roughness.png")
wrapper.metallic_texture.image = bpy.data.images.load("/path/to/metallic.png")
wrapper.normalmap_texture.image = bpy.data.images.load("/path/to/normal.png")
wrapper.emission_color_texture.image = bpy.data.images.load("/path/to/emission.png")
wrapper.specular_texture.image = bpy.data.images.load("/path/to/specular.png")
wrapper.transmission_texture.image = bpy.data.images.load("/path/to/transmission.png")
wrapper.alpha_texture.image = bpy.data.images.load("/path/to/alpha.png")
wrapper.ior_texture.image = bpy.data.images.load("/path/to/ior.png")
```

### 4.4 Material Presets (VERIFIED)

```python
from bpy_extras.node_shader_utils import PrincipledBSDFWrapper
import bpy

obj = bpy.context.active_object
mat = bpy.data.materials.new(name="Material")
mat.use_nodes = True
wrapper = PrincipledBSDFWrapper(mat, is_readonly=False)

# === CHROME/SILVER METAL ===
wrapper.base_color = (0.9, 0.9, 0.9)
wrapper.metallic = 1.0
wrapper.roughness = 0.1

# === GOLD ===
wrapper.base_color = (1.0, 0.766, 0.336)
wrapper.metallic = 1.0
wrapper.roughness = 0.1

# === COPPER ===
wrapper.base_color = (0.955, 0.637, 0.538)
wrapper.metallic = 1.0
wrapper.roughness = 0.2

# === BRUSHED METAL ===
wrapper.base_color = (0.7, 0.7, 0.7)
wrapper.metallic = 1.0
wrapper.roughness = 0.4

# === RED PLASTIC ===
wrapper.base_color = (0.8, 0.1, 0.1)
wrapper.metallic = 0.0
wrapper.roughness = 0.4
wrapper.specular = 0.5

# === CLEAR GLASS ===
wrapper.base_color = (1.0, 1.0, 1.0)
wrapper.transmission = 1.0
wrapper.roughness = 0.0
wrapper.ior = 1.45

# === FROSTED GLASS ===
wrapper.base_color = (1.0, 1.0, 1.0)
wrapper.transmission = 1.0
wrapper.roughness = 0.3
wrapper.ior = 1.45

# === EMISSIVE/NEON ===
wrapper.base_color = (0.0, 0.0, 0.0)
wrapper.emission_color = (1.0, 0.2, 0.5)
wrapper.emission_strength = 15.0

# === MATTE WHITE ===
wrapper.base_color = (0.8, 0.8, 0.8)
wrapper.metallic = 0.0
wrapper.roughness = 1.0
wrapper.specular = 0.0

# === RUBBER ===
wrapper.base_color = (0.1, 0.1, 0.1)
wrapper.metallic = 0.0
wrapper.roughness = 0.8
wrapper.specular = 0.3

# === SKIN (basic) ===
wrapper.base_color = (0.8, 0.6, 0.5)
wrapper.metallic = 0.0
wrapper.roughness = 0.5
wrapper.specular = 0.3

# === WOOD (basic) ===
wrapper.base_color = (0.4, 0.25, 0.1)
wrapper.metallic = 0.0
wrapper.roughness = 0.6

# === CONCRETE ===
wrapper.base_color = (0.5, 0.5, 0.5)
wrapper.metallic = 0.0
wrapper.roughness = 0.9

# Apply to object
if obj.data.materials:
    obj.data.materials[0] = mat
else:
    obj.data.materials.append(mat)
```

---

## 5. NODE OPERATIONS (Direct API)

For advanced node manipulation beyond PrincipledBSDFWrapper:

### 5.1 Access Node Tree

```python
import bpy

mat = bpy.context.active_object.active_material
if not mat:
    raise ValueError("No active material")

mat.use_nodes = True
tree = mat.node_tree
nodes = tree.nodes
links = tree.links
```

### 5.2 Access Nodes

```python
# By name (use name from context)
principled = nodes.get("Principled BSDF")
output = nodes.get("Material Output")

# By type
for node in nodes:
    if node.bl_idname == "ShaderNodeBsdfPrincipled":
        principled = node
        break
```

### 5.3 Create Nodes

```python
tex_node = nodes.new(type="ShaderNodeTexImage")
tex_node.name = "My Texture"
tex_node.label = "Albedo Map"
tex_node.location = (-300, 300)
```

### 5.4 Connect Nodes

```python
# Create link: output socket -> input socket
links.new(tex_node.outputs["Color"], principled.inputs["Base Color"])

# Access sockets by name
links.new(
    nodes["Image Texture"].outputs["Color"],
    nodes["Principled BSDF"].inputs["Base Color"]
)
```

### 5.5 Set Node Values

```python
# Set input default values (when not connected)
principled.inputs["Base Color"].default_value = (0.8, 0.2, 0.1, 1.0)  # RGBA for nodes!
principled.inputs["Metallic"].default_value = 1.0
principled.inputs["Roughness"].default_value = 0.2

# Check if linked before setting
if not principled.inputs["Base Color"].is_linked:
    principled.inputs["Base Color"].default_value = (1, 0, 0, 1)
```

### 5.6 Common Node Types (VERIFIED)

```python
# Shader Nodes
"ShaderNodeBsdfPrincipled"    # Main PBR shader
"ShaderNodeEmission"          # Emission
"ShaderNodeMixShader"         # Mix shaders
"ShaderNodeBsdfGlass"         # Glass
"ShaderNodeBsdfTransparent"   # Transparent
"ShaderNodeBsdfDiffuse"       # Diffuse

# Texture Nodes
"ShaderNodeTexImage"          # Image texture
"ShaderNodeTexNoise"          # Procedural noise
"ShaderNodeTexVoronoi"        # Voronoi
"ShaderNodeTexGradient"       # Gradient
"ShaderNodeTexChecker"        # Checker
"ShaderNodeTexBrick"          # Brick

# Utility Nodes
"ShaderNodeMath"              # Math operations
"ShaderNodeVectorMath"        # Vector math
"ShaderNodeMix"               # Mix (Blender 4.0+)
"ShaderNodeSeparateXYZ"       # Split vector
"ShaderNodeCombineXYZ"        # Combine vector
"ShaderNodeNormalMap"         # Normal map
"ShaderNodeBump"              # Bump
"ShaderNodeMapping"           # UV transform
"ShaderNodeTexCoord"          # Texture coordinates
```

---

## 6. MODIFIERS

### 6.1 Add Modifiers

```python
obj = bpy.context.active_object

# Subdivision Surface
mod = obj.modifiers.new(name="Subdivision", type='SUBSURF')
mod.levels = 2
mod.render_levels = 3

# Bevel
mod = obj.modifiers.new(name="Bevel", type='BEVEL')
mod.width = 0.02
mod.segments = 3

# Solidify
mod = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
mod.thickness = 0.1

# Array
mod = obj.modifiers.new(name="Array", type='ARRAY')
mod.count = 5
mod.relative_offset_displace = (1.1, 0, 0)

# Mirror
mod = obj.modifiers.new(name="Mirror", type='MIRROR')
mod.use_axis = (True, False, False)

# Boolean
mod = obj.modifiers.new(name="Boolean", type='BOOLEAN')
mod.operation = 'DIFFERENCE'
mod.object = bpy.data.objects["Cutter"]

# Decimate
mod = obj.modifiers.new(name="Decimate", type='DECIMATE')
mod.ratio = 0.5

# Smooth
mod = obj.modifiers.new(name="Smooth", type='SMOOTH')
mod.factor = 0.5
mod.iterations = 5
```

### 6.2 Apply/Remove Modifiers

```python
# Apply modifier
bpy.ops.object.modifier_apply(modifier="Subdivision")

# Remove modifier
obj.modifiers.remove(obj.modifiers["Subdivision"])
```

---

## 7. LIGHTING

### 7.1 Create Lights

```python
import bpy

# Point Light
bpy.ops.object.light_add(type='POINT', location=(0, 0, 3))
light = bpy.context.active_object
light.data.energy = 1000
light.data.color = (1, 0.9, 0.8)

# Area Light
bpy.ops.object.light_add(type='AREA', location=(2, -2, 3))
light = bpy.context.active_object
light.data.energy = 500
light.data.size = 2

# Spot Light
bpy.ops.object.light_add(type='SPOT', location=(0, -3, 3))
light = bpy.context.active_object
light.data.energy = 1000
light.data.spot_size = 0.785

# Sun Light
bpy.ops.object.light_add(type='SUN', location=(0, 0, 10))
light = bpy.context.active_object
light.data.energy = 5
```

### 7.2 Three-Point Lighting

```python
import bpy
import math

# Key Light
bpy.ops.object.light_add(type='AREA', location=(4, -3, 5))
key = bpy.context.active_object
key.name = "Key Light"
key.data.energy = 800
key.data.size = 2
key.rotation_euler = (math.radians(60), 0, math.radians(45))

# Fill Light
bpy.ops.object.light_add(type='AREA', location=(-3, -2, 3))
fill = bpy.context.active_object
fill.name = "Fill Light"
fill.data.energy = 300
fill.data.size = 3
fill.rotation_euler = (math.radians(70), 0, math.radians(-30))

# Rim Light
bpy.ops.object.light_add(type='AREA', location=(0, 4, 4))
rim = bpy.context.active_object
rim.name = "Rim Light"
rim.data.energy = 600
rim.data.size = 1
rim.rotation_euler = (math.radians(120), 0, math.radians(180))
```

---

## 8. CAMERA

```python
import bpy

# Create camera
bpy.ops.object.camera_add(location=(7, -6, 5))
cam = bpy.context.active_object
cam.rotation_euler = (1.1, 0, 0.8)

# Set as active camera
bpy.context.scene.camera = cam

# Camera settings
cam_data = cam.data
cam_data.lens = 50  # Focal length mm
cam_data.clip_start = 0.1
cam_data.clip_end = 1000

# Depth of Field
cam_data.dof.use_dof = True
cam_data.dof.focus_object = bpy.data.objects["Subject"]
cam_data.dof.aperture_fstop = 2.8
```

---

## 9. ANIMATION

```python
import bpy

obj = bpy.context.active_object
scene = bpy.context.scene

# Set frame range
scene.frame_start = 1
scene.frame_end = 250

# Insert keyframes
scene.frame_set(1)
obj.location = (0, 0, 0)
obj.keyframe_insert(data_path="location", frame=1)

scene.frame_set(60)
obj.location = (5, 0, 0)
obj.keyframe_insert(data_path="location", frame=60)

# Keyframe rotation
obj.keyframe_insert(data_path="rotation_euler", frame=1)

# Delete keyframes
obj.keyframe_delete(data_path="location", frame=30)

# Clear all animation
obj.animation_data_clear()
```

---

## 10. MESH EDITING

```python
import bpy

obj = bpy.context.active_object
if obj.type != 'MESH':
    raise ValueError("Not a mesh object")

# Enter edit mode
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')

# Remove doubles
bpy.ops.mesh.remove_doubles(threshold=0.0001)

# Recalculate normals
bpy.ops.mesh.normals_make_consistent(inside=False)

# Remove loose
bpy.ops.mesh.delete_loose()

# Subdivide
bpy.ops.mesh.subdivide(number_cuts=1)

# Extrude
bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={"value": (0, 0, 1)})

# ALWAYS return to object mode
bpy.ops.object.mode_set(mode='OBJECT')
```

---

## 11. EDITOR SWITCHING

```python
import bpy

area = bpy.context.area
area.type = 'NODE_EDITOR'

# Valid types: VIEW_3D, NODE_EDITOR, PROPERTIES, OUTLINER,
# IMAGE_EDITOR, GRAPH_EDITOR, DOPESHEET_EDITOR, TEXT_EDITOR

# For node editor, set tree type
for space in area.spaces:
    if space.type == 'NODE_EDITOR':
        space.tree_type = 'ShaderNodeTree'
        break
```

---

## 12. RENDERING

```python
import bpy

scene = bpy.context.scene

# Render engine
scene.render.engine = 'CYCLES'  # or 'BLENDER_EEVEE'

# Resolution
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080

# Output
scene.render.filepath = "/tmp/render.png"
scene.render.image_settings.file_format = 'PNG'

# Cycles settings
if scene.render.engine == 'CYCLES':
    scene.cycles.samples = 128
    scene.cycles.use_denoising = True

# Render
bpy.ops.render.render(write_still=True)
```

---

## 13. COLLECTIONS

```python
import bpy

# Create collection
new_col = bpy.data.collections.new("MyCollection")
bpy.context.scene.collection.children.link(new_col)

# Move object to collection
obj = bpy.context.active_object
new_col.objects.link(obj)
for col in obj.users_collection:
    if col != new_col:
        col.objects.unlink(obj)

# Hide collection
new_col.hide_viewport = True
```

---

## 14. ERROR HANDLING

Always wrap code in try-except:

```python
import bpy

try:
    obj = bpy.context.active_object
    if not obj:
        raise ValueError("No object selected. Please select an object first.")

    if obj.type != 'MESH':
        raise ValueError(f"Expected mesh, got {obj.type}")

    # ... do work ...

except Exception as e:
    raise RuntimeError(f"Operation failed: {str(e)}")
```

---

## 15. VOICE COMMAND MAPPING

| Voice Phrase | Action |
|--------------|--------|
| "make it shiny/metallic" | `metallic=1.0, roughness=0.2` |
| "make it rough/matte" | `roughness=0.8` |
| "make it red/blue/green" | Set `base_color` |
| "add subdivision" | Add SUBSURF modifier |
| "smooth it out" | SUBSURF + shade_smooth |
| "clean up mesh" | remove_doubles + normals |
| "connect X to Y" | Create node link |
| "add texture" | Add ShaderNodeTexImage |
| "make it glow" | emission_color + strength |
| "make it glass/transparent" | transmission=1.0, ior=1.45 |
| "move up/down/left/right" | Adjust location |
| "rotate it" | Adjust rotation_euler |
| "scale it" | Adjust scale |
| "duplicate it" | bpy.ops.object.duplicate() |
| "delete it" | bpy.ops.object.delete() |
| "render" | bpy.ops.render.render() |

---

## 16. CRITICAL RULES

1. **Always check for None**: Objects, materials, nodes may not exist
2. **Always use `mat.use_nodes = True`**: Before accessing `node_tree`
3. **Always return to object mode**: After edit mode operations
4. **Use context names**: Reference objects/materials/nodes by exact names from context
5. **Handle errors gracefully**: Wrap code in try-except
6. **Use PrincipledBSDFWrapper**: Preferred for material creation
7. **Import math for angles**: Rotation values are in radians
8. **RGB vs RGBA**: Wrapper uses RGB (3 values), node inputs use RGBA (4 values)

---

## 17. COMPLETE EXAMPLE

```python
import bpy
from bpy_extras.node_shader_utils import PrincipledBSDFWrapper

# Create sphere
bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(0, 0, 0), segments=32, ring_count=16)
obj = bpy.context.active_object
obj.name = "MetalSphere"

# Shade smooth
bpy.ops.object.shade_smooth()

# Create metal material
mat = bpy.data.materials.new(name="ChromeMetal")
mat.use_nodes = True
wrapper = PrincipledBSDFWrapper(mat, is_readonly=False)
wrapper.base_color = (0.9, 0.9, 0.9)
wrapper.metallic = 1.0
wrapper.roughness = 0.1

# Apply material
obj.data.materials.append(mat)

# Add subdivision
mod = obj.modifiers.new(name="Subdivision", type='SUBSURF')
mod.levels = 2
```

---

*Verified against Blender source code: bpy_extras/node_shader_utils.py, bl_operators/node.py, bl_operators/object.py*
