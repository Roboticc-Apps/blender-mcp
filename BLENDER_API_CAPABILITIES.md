# Blender API Capabilities - What We CAN Do

## Summary

The Blender Python API (`bpy`) provides **complete programmatic control** over:
- All objects, materials, nodes, modifiers
- All connections/links between nodes
- Editor switching and viewport control
- Selection and active states

This means `execute_blender_code` can do ANYTHING the user can do in the UI.

---

## Node Tree Manipulation

### Access Nodes
```python
# Get material node tree
mat = bpy.data.materials["MyMaterial"]
tree = mat.node_tree

# Access all nodes
for node in tree.nodes:
    print(node.name, node.type)

# Access node by name
principled = tree.nodes["Principled BSDF"]

# Access node by type (find first)
for node in tree.nodes:
    if node.bl_idname == "ShaderNodeBsdfPrincipled":
        principled = node
        break
```

### Create/Delete Nodes
```python
# Create node
new_node = tree.nodes.new(type="ShaderNodeTexImage")
new_node.name = "My Texture"
new_node.location = (x, y)

# Delete node
tree.nodes.remove(node)
```

### Node Selection
```python
# Select node
node.select = True

# Deselect all
for n in tree.nodes:
    n.select = False

# Set active node
tree.nodes.active = node
```

### Node Inputs/Outputs
```python
# Access by name
base_color_input = node.inputs["Base Color"]
bsdf_output = node.outputs["BSDF"]

# Access by index
first_input = node.inputs[0]

# Get/set value (if not linked)
base_color_input.default_value = (1.0, 0.0, 0.0, 1.0)  # RGBA
roughness = node.inputs["Roughness"].default_value

# Check if linked
if not input.is_linked:
    # Can set default_value
```

### Links (Connections)
```python
# Create link
tree.links.new(
    texture_node.outputs["Color"],
    principled.inputs["Base Color"]
)

# Remove link
for link in tree.links:
    if link.to_node == principled and link.to_socket.name == "Base Color":
        tree.links.remove(link)
        break

# Iterate all links
for link in tree.links:
    print(f"{link.from_node.name}.{link.from_socket.name} -> {link.to_node.name}.{link.to_socket.name}")
```

---

## Material Management

### Access Materials
```python
# All materials
for mat in bpy.data.materials:
    print(mat.name)

# Get by name
mat = bpy.data.materials.get("Material")

# Active object's material
obj = bpy.context.active_object
if obj.active_material:
    mat = obj.active_material

# Object's material slots
for slot in obj.material_slots:
    if slot.material:
        print(slot.material.name)
```

### Create Materials
```python
# Create new material
mat = bpy.data.materials.new(name="My Material")
mat.use_nodes = True  # IMPORTANT: Enable nodes!

# Assign to object
obj.data.materials.append(mat)

# Or replace existing slot
obj.material_slots[0].material = mat
```

### PrincipledBSDFWrapper (High-Level API)
```python
from bpy_extras.node_shader_utils import PrincipledBSDFWrapper

mat = bpy.data.materials.new(name="PBR Material")
mat.use_nodes = True

wrapper = PrincipledBSDFWrapper(mat, is_readonly=False)

# Set colors (RGB tuples)
wrapper.base_color = (0.8, 0.2, 0.1)  # RGB only, not RGBA

# Set scalar values
wrapper.metallic = 1.0
wrapper.roughness = 0.2
wrapper.specular = 0.5
wrapper.alpha = 1.0

# Set textures
wrapper.base_color_texture.image = bpy.data.images.load("/path/to/albedo.png")
wrapper.roughness_texture.image = bpy.data.images.load("/path/to/roughness.png")
wrapper.metallic_texture.image = bpy.data.images.load("/path/to/metallic.png")
wrapper.normalmap_texture.image = bpy.data.images.load("/path/to/normal.png")
```

---

## Editor Switching

```python
# Switch current area to different editor
area = bpy.context.area
area.type = 'NODE_EDITOR'  # or VIEW_3D, PROPERTIES, OUTLINER, etc.

# For node editor, set tree type
for space in area.spaces:
    if space.type == 'NODE_EDITOR':
        space.tree_type = 'ShaderNodeTree'  # or GeometryNodeTree, CompositorNodeTree

# Valid editor types:
# VIEW_3D, NODE_EDITOR, PROPERTIES, OUTLINER, IMAGE_EDITOR,
# SEQUENCE_EDITOR, GRAPH_EDITOR, DOPESHEET_EDITOR, NLA_EDITOR,
# TEXT_EDITOR, CONSOLE, INFO, FILE_BROWSER, SPREADSHEET
```

---

## Object Manipulation

### Access Objects
```python
# All scene objects
for obj in bpy.context.scene.objects:
    print(obj.name, obj.type)

# By name
cube = bpy.data.objects.get("Cube")

# Active object
obj = bpy.context.active_object

# Selected objects
for obj in bpy.context.selected_objects:
    print(obj.name)
```

### Selection
```python
# Deselect all
bpy.ops.object.select_all(action='DESELECT')

# Select object
obj.select_set(True)

# Set as active
bpy.context.view_layer.objects.active = obj
```

### Mode Switching
```python
# Check current mode
current_mode = bpy.context.mode  # 'OBJECT', 'EDIT_MESH', 'SCULPT', etc.

# Switch mode
bpy.ops.object.mode_set(mode='EDIT')  # OBJECT, EDIT, SCULPT, VERTEX_PAINT, etc.

# IMPORTANT: Always return to object mode after mesh operations
bpy.ops.object.mode_set(mode='OBJECT')
```

---

## What We Already Provide in Context

### get_node_tree returns:
```json
{
  "material": "Material Name",
  "nodes": [
    {
      "name": "Principled BSDF",
      "type": "ShaderNodeBsdfPrincipled",
      "label": null,
      "location": [0, 300],
      "inputs": [
        {"name": "Base Color", "type": "RGBA", "is_linked": false, "value": [0.8, 0.8, 0.8, 1.0]},
        {"name": "Roughness", "type": "VALUE", "is_linked": true}
      ],
      "outputs": [
        {"name": "BSDF", "type": "SHADER", "is_linked": true}
      ]
    }
  ],
  "links": [
    {
      "from_node": "Image Texture",
      "from_socket": "Color",
      "to_node": "Principled BSDF",
      "to_socket": "Base Color"
    }
  ]
}
```

### get_full_context returns:
- Editor type and mode
- Viewport state (shading, overlays, camera view)
- Node editor context (if open)
- Selection (active object, all selected)
- Scene info
- Materials list
- Active modifiers

### get_scene_info returns:
- All objects with transforms, materials, modifiers, children
- All materials
- World settings
- Collections

---

## How AI Should Use This

1. **User says**: "Connect the texture to the base color"
2. **AI gets context** via `get_node_tree` → sees all nodes and their names
3. **AI generates code**:
```python
import bpy

mat = bpy.context.active_object.active_material
tree = mat.node_tree

# Find nodes by name (from context)
texture_node = tree.nodes["Image Texture"]
principled = tree.nodes["Principled BSDF"]

# Create connection
tree.links.new(
    texture_node.outputs["Color"],
    principled.inputs["Base Color"]
)
```

4. **AI executes** via `execute_blender_code`

---

## Limitations

1. **Some operators require specific context** - May need to switch editors first
2. **File dialogs are interactive** - Can't programmatically browse, but can load by path
3. **Undo is per-operation** - Each execute_blender_code is one undo step
4. **Some UI state is read-only** - Can't resize panels programmatically

---

## Conclusion

The API is comprehensive enough that with:
1. Good context (node names, connections, selection)
2. Good app_prompt (code patterns, best practices)
3. execute_blender_code

We can accomplish virtually ANY Blender task via voice commands.
