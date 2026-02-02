"""
BLENDER GEOMETRY NODES - COMPLETE PYTHON REFERENCE
===================================================
Extracted from NodeToPython (BSD-3 License)

This is the CORRECT, VERIFIED way to create geometry nodes via Python.
Use these exact patterns - they are proven to work.
"""

import bpy

# =============================================================================
# PATTERN 1: CREATE GEOMETRY NODE MODIFIER
# =============================================================================

def create_geometry_node_modifier(obj_name="Object", tree_name="GeometryNodes"):
    """Create a geometry nodes modifier on an object."""
    obj = bpy.data.objects[obj_name]

    # Create modifier
    modifier = obj.modifiers.new(name="GeometryNodes", type='NODES')

    # Create new node tree
    node_tree = bpy.data.node_groups.new(name=tree_name, type='GeometryNodeTree')
    modifier.node_group = node_tree

    return node_tree


# =============================================================================
# PATTERN 2: SET UP NODE TREE INTERFACE (INPUT/OUTPUT SOCKETS)
# =============================================================================

def setup_interface(node_tree):
    """Add input/output sockets to the node tree interface."""

    # Add Geometry input socket
    node_tree.interface.new_socket(
        name="Geometry",
        in_out='INPUT',
        socket_type='NodeSocketGeometry'
    )

    # Add Geometry output socket
    node_tree.interface.new_socket(
        name="Geometry",
        in_out='OUTPUT',
        socket_type='NodeSocketGeometry'
    )

    # Add Float input with default value
    float_socket = node_tree.interface.new_socket(
        name="Scale",
        in_out='INPUT',
        socket_type='NodeSocketFloat'
    )
    float_socket.default_value = 1.0
    float_socket.min_value = 0.0
    float_socket.max_value = 10.0

    # Add Integer input
    int_socket = node_tree.interface.new_socket(
        name="Count",
        in_out='INPUT',
        socket_type='NodeSocketInt'
    )
    int_socket.default_value = 5

    # Add Vector input
    vec_socket = node_tree.interface.new_socket(
        name="Offset",
        in_out='INPUT',
        socket_type='NodeSocketVector'
    )
    vec_socket.default_value = (0.0, 0.0, 1.0)


# Socket Types:
# 'NodeSocketGeometry', 'NodeSocketFloat', 'NodeSocketInt', 'NodeSocketBool',
# 'NodeSocketVector', 'NodeSocketColor', 'NodeSocketString', 'NodeSocketMaterial',
# 'NodeSocketObject', 'NodeSocketCollection', 'NodeSocketImage'


# =============================================================================
# PATTERN 3: CREATE NODES
# =============================================================================

def create_nodes(node_tree):
    """Create nodes in the tree."""
    nodes = node_tree.nodes

    # Clear existing nodes
    nodes.clear()

    # Create Group Input (REQUIRED)
    group_input = nodes.new('NodeGroupInput')
    group_input.location = (-400, 0)
    group_input.name = "Group Input"

    # Create Group Output (REQUIRED)
    group_output = nodes.new('NodeGroupOutput')
    group_output.location = (400, 0)
    group_output.name = "Group Output"

    # Create geometry node - use exact bl_idname string
    distribute = nodes.new('GeometryNodeDistributePointsOnFaces')
    distribute.location = (0, 0)
    distribute.name = "Distribute Points"

    # Set node properties
    distribute.distribute_method = 'RANDOM'  # or 'POISSON'

    return group_input, group_output, distribute


# =============================================================================
# PATTERN 4: LINK NODES
# =============================================================================

def link_nodes(node_tree, group_input, group_output, distribute):
    """Create links between nodes."""
    links = node_tree.links

    # Link by socket index
    links.new(
        group_input.outputs[0],   # Geometry output from Group Input
        distribute.inputs[0]      # Mesh input on Distribute
    )

    # Link to output
    links.new(
        distribute.outputs[0],    # Points output
        group_output.inputs[0]    # Geometry input on Group Output
    )

    # Alternative: Link by socket name (less reliable if names change)
    # links.new(group_input.outputs['Geometry'], distribute.inputs['Mesh'])


# =============================================================================
# PATTERN 5: SET INPUT SOCKET DEFAULT VALUES
# =============================================================================

def set_socket_defaults(node):
    """Set default values on node input sockets."""

    # By index (most reliable)
    node.inputs[0].default_value = 5.0

    # By name (works if name is unique)
    node.inputs['Density'].default_value = 10.0

    # Vector values
    node.inputs['Scale'].default_value = (1.0, 1.0, 1.0)

    # Color values (RGBA)
    node.inputs['Color'].default_value = (1.0, 0.0, 0.0, 1.0)

    # Boolean
    node.inputs['Selection'].default_value = True


# =============================================================================
# ALL GEOMETRY NODE TYPES (bl_idname strings)
# =============================================================================

GEOMETRY_NODE_TYPES = {
    # === MESH PRIMITIVES ===
    'GeometryNodeMeshCube': "Creates a cube mesh",
    'GeometryNodeMeshCylinder': "Creates a cylinder mesh",
    'GeometryNodeMeshCone': "Creates a cone mesh",
    'GeometryNodeMeshGrid': "Creates a grid/plane mesh",
    'GeometryNodeMeshCircle': "Creates a circle mesh",
    'GeometryNodeMeshLine': "Creates a line of points",
    'GeometryNodeMeshUVSphere': "Creates a UV sphere",
    'GeometryNodeMeshIcoSphere': "Creates an icosphere",

    # === CURVE PRIMITIVES ===
    'GeometryNodeCurvePrimitiveLine': "Creates a line curve",
    'GeometryNodeCurvePrimitiveCircle': "Creates a circle curve",
    'GeometryNodeCurveArc': "Creates an arc curve",
    'GeometryNodeCurveSpiral': "Creates a spiral curve",
    'GeometryNodeCurveStar': "Creates a star curve",
    'GeometryNodeCurvePrimitiveQuadrilateral': "Creates a quadrilateral curve",
    'GeometryNodeCurvePrimitiveBezierSegment': "Creates a bezier segment",

    # === POINT OPERATIONS ===
    'GeometryNodeDistributePointsOnFaces': "Scatter points on mesh surface",
    'GeometryNodeDistributePointsInVolume': "Scatter points in volume",
    'GeometryNodePoints': "Create points",
    'GeometryNodePointsToVertices': "Convert points to vertices",
    'GeometryNodePointsToCurves': "Convert points to curves",
    'GeometryNodeMeshToPoints': "Convert mesh to points",

    # === INSTANCING ===
    'GeometryNodeInstanceOnPoints': "Place instances at points",
    'GeometryNodeInstancesToPoints': "Convert instances to points",
    'GeometryNodeRealizeInstances': "Make instances real geometry",
    'GeometryNodeRotateInstances': "Rotate instances",
    'GeometryNodeScaleInstances': "Scale instances",
    'GeometryNodeTranslateInstances': "Move instances",
    'GeometryNodeGeometryToInstance': "Convert geometry to instance",

    # === MESH OPERATIONS ===
    'GeometryNodeExtrudeMesh': "Extrude mesh faces/edges/vertices",
    'GeometryNodeScaleElements': "Scale mesh elements",
    'GeometryNodeMeshBoolean': "Boolean operations (union/intersect/difference)",
    'GeometryNodeSubdivideMesh': "Subdivide mesh",
    'GeometryNodeSubdivisionSurface': "Subdivision surface",
    'GeometryNodeTriangulate': "Triangulate faces",
    'GeometryNodeDualMesh': "Create dual mesh",
    'GeometryNodeFlipFaces': "Flip face normals",
    'GeometryNodeSplitEdges': "Split edges",
    'GeometryNodeMergeByDistance': "Merge vertices by distance",
    'GeometryNodeDeleteGeometry': "Delete geometry by selection",
    'GeometryNodeSeparateGeometry': "Separate geometry by selection",
    'GeometryNodeDuplicateElements': "Duplicate elements",
    'GeometryNodeFillCurve': "Fill curve to create mesh",

    # === TRANSFORM ===
    'GeometryNodeTransform': "Transform geometry",
    'GeometryNodeSetPosition': "Set vertex positions",

    # === CURVE OPERATIONS ===
    'GeometryNodeCurveToMesh': "Convert curve to mesh",
    'GeometryNodeCurveToPoints': "Convert curve to points",
    'GeometryNodeMeshToCurve': "Convert mesh edges to curve",
    'GeometryNodeFillCurve': "Fill curve to mesh",
    'GeometryNodeFilletCurve': "Fillet curve corners",
    'GeometryNodeResampleCurve': "Resample curve points",
    'GeometryNodeReverseCurve': "Reverse curve direction",
    'GeometryNodeSubdivideCurve': "Subdivide curve",
    'GeometryNodeTrimCurve': "Trim curve",
    'GeometryNodeSetCurveRadius': "Set curve radius",

    # === JOIN/COMBINE ===
    'GeometryNodeJoinGeometry': "Join multiple geometries",
    'GeometryNodeSeparateComponents': "Separate mesh/curve/points/etc",

    # === INPUT VALUES ===
    'GeometryNodeInputPosition': "Get vertex position",
    'GeometryNodeInputNormal': "Get normal vector",
    'GeometryNodeInputIndex': "Get element index",
    'GeometryNodeInputID': "Get element ID",
    'GeometryNodeInputRadius': "Get point radius",

    # === SAMPLING ===
    'GeometryNodeSampleIndex': "Sample attribute at index",
    'GeometryNodeSampleNearest': "Sample nearest point",
    'GeometryNodeSampleNearestSurface': "Sample nearest surface point",
    'GeometryNodeProximity': "Get distance to geometry",
    'GeometryNodeRaycast': "Raycast to geometry",

    # === ATTRIBUTE ===
    'GeometryNodeCaptureAttribute': "Capture attribute value",
    'GeometryNodeStoreNamedAttribute': "Store named attribute",
    'GeometryNodeInputNamedAttribute': "Get named attribute",
    'GeometryNodeRemoveAttribute': "Remove attribute",

    # === MATERIAL ===
    'GeometryNodeSetMaterial': "Set material on geometry",
    'GeometryNodeReplaceMaterial': "Replace material",
    'GeometryNodeInputMaterial': "Material input",
    'GeometryNodeMaterialSelection': "Select by material",

    # === UTILITY ===
    'GeometryNodeSwitch': "Switch between values",
    'GeometryNodeIndexSwitch': "Switch by index",
    'GeometryNodeBoundBox': "Get bounding box",
    'GeometryNodeConvexHull': "Create convex hull",
}

# === MATH/FUNCTION NODES (used in Geometry Nodes) ===
FUNCTION_NODE_TYPES = {
    'ShaderNodeMath': "Math operations (add, multiply, etc)",
    'ShaderNodeVectorMath': "Vector math operations",
    'ShaderNodeMapRange': "Remap value range",
    'ShaderNodeClamp': "Clamp value",
    'ShaderNodeMix': "Mix/blend values",
    'FunctionNodeCompare': "Compare values",
    'FunctionNodeBooleanMath': "Boolean operations (AND, OR, etc)",
    'FunctionNodeRandomValue': "Generate random values",
    'FunctionNodeInputInt': "Integer constant",
    'FunctionNodeInputVector': "Vector constant",
    'FunctionNodeInputBool': "Boolean constant",
    'FunctionNodeInputString': "String constant",
    'FunctionNodeInputColor': "Color constant",
    'ShaderNodeValue': "Float constant",
}


# =============================================================================
# COMPLETE EXAMPLE: WINDOW GRID ON BUILDING FACADE
# =============================================================================

def create_window_grid():
    """Create a procedural window grid for a building facade."""

    # Create base cube
    bpy.ops.mesh.primitive_cube_add(size=2)
    obj = bpy.context.active_object
    obj.name = "Building_Facade"

    # Create geometry nodes
    mod = obj.modifiers.new(name="WindowGrid", type='NODES')
    tree = bpy.data.node_groups.new(name="WindowGridNodes", type='GeometryNodeTree')
    mod.node_group = tree

    nodes = tree.nodes
    links = tree.links
    nodes.clear()

    # Set up interface
    tree.interface.new_socket(name="Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    tree.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')

    cols_socket = tree.interface.new_socket(name="Columns", in_out='INPUT', socket_type='NodeSocketInt')
    cols_socket.default_value = 5

    rows_socket = tree.interface.new_socket(name="Rows", in_out='INPUT', socket_type='NodeSocketInt')
    rows_socket.default_value = 4

    # Create nodes
    group_input = nodes.new('NodeGroupInput')
    group_input.location = (-600, 0)

    group_output = nodes.new('NodeGroupOutput')
    group_output.location = (600, 0)

    # Grid for window positions
    grid = nodes.new('GeometryNodeMeshGrid')
    grid.location = (-400, 200)
    grid.inputs['Size X'].default_value = 10.0
    grid.inputs['Size Y'].default_value = 8.0

    # Convert grid to points
    to_points = nodes.new('GeometryNodeMeshToPoints')
    to_points.location = (-200, 200)

    # Window geometry (small cube)
    window = nodes.new('GeometryNodeMeshCube')
    window.location = (-200, -100)
    window.inputs['Size'].default_value = (0.8, 0.1, 1.2)

    # Instance windows on points
    instance = nodes.new('GeometryNodeInstanceOnPoints')
    instance.location = (0, 100)

    # Join with original facade
    join = nodes.new('GeometryNodeJoinGeometry')
    join.location = (200, 0)

    # Transform facade
    transform = nodes.new('GeometryNodeTransform')
    transform.location = (-200, -300)
    transform.inputs['Scale'].default_value = (5.0, 0.5, 4.0)

    # Create links
    links.new(group_input.outputs['Columns'], grid.inputs['Vertices X'])
    links.new(group_input.outputs['Rows'], grid.inputs['Vertices Y'])
    links.new(grid.outputs['Mesh'], to_points.inputs['Mesh'])
    links.new(to_points.outputs['Points'], instance.inputs['Points'])
    links.new(window.outputs['Mesh'], instance.inputs['Instance'])
    links.new(group_input.outputs['Geometry'], transform.inputs['Geometry'])
    links.new(transform.outputs['Geometry'], join.inputs['Geometry'])
    links.new(instance.outputs['Instances'], join.inputs['Geometry'])
    links.new(join.outputs['Geometry'], group_output.inputs['Geometry'])

    return obj


# =============================================================================
# COMPLETE EXAMPLE: COLUMN ARRAY
# =============================================================================

def create_column_array():
    """Create a row of columns."""

    bpy.ops.mesh.primitive_plane_add(size=1)
    obj = bpy.context.active_object
    obj.name = "Column_Array"

    mod = obj.modifiers.new(name="Columns", type='NODES')
    tree = bpy.data.node_groups.new(name="ColumnNodes", type='GeometryNodeTree')
    mod.node_group = tree

    nodes = tree.nodes
    links = tree.links
    nodes.clear()

    # Interface
    tree.interface.new_socket(name="Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    tree.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')

    count_socket = tree.interface.new_socket(name="Count", in_out='INPUT', socket_type='NodeSocketInt')
    count_socket.default_value = 6

    # Nodes
    group_input = nodes.new('NodeGroupInput')
    group_input.location = (-400, 0)

    group_output = nodes.new('NodeGroupOutput')
    group_output.location = (400, 0)

    # Line of points
    line = nodes.new('GeometryNodeMeshLine')
    line.location = (-200, 100)
    line.inputs['Start Location'].default_value = (0.0, 0.0, 0.0)
    line.inputs['Offset'].default_value = (2.0, 0.0, 0.0)

    # Column (cylinder)
    cylinder = nodes.new('GeometryNodeMeshCylinder')
    cylinder.location = (-200, -100)
    cylinder.inputs['Radius'].default_value = 0.3
    cylinder.inputs['Depth'].default_value = 4.0

    # Instance columns
    instance = nodes.new('GeometryNodeInstanceOnPoints')
    instance.location = (0, 0)

    # Rotate to stand upright
    rotate = nodes.new('GeometryNodeRotateInstances')
    rotate.location = (200, 0)
    rotate.inputs['Rotation'].default_value = (1.5708, 0.0, 0.0)  # 90 degrees X

    # Links
    links.new(group_input.outputs['Count'], line.inputs['Count'])
    links.new(line.outputs['Mesh'], instance.inputs['Points'])
    links.new(cylinder.outputs['Mesh'], instance.inputs['Instance'])
    links.new(instance.outputs['Instances'], rotate.inputs['Instances'])
    links.new(rotate.outputs['Instances'], group_output.inputs['Geometry'])

    return obj


# =============================================================================
# NODE SETTINGS REFERENCE
# =============================================================================

# Common node settings (set after node creation):

# GeometryNodeDistributePointsOnFaces
# .distribute_method = 'RANDOM' | 'POISSON'

# GeometryNodeExtrudeMesh
# .mode = 'VERTICES' | 'EDGES' | 'FACES'

# GeometryNodeMeshBoolean
# .operation = 'INTERSECT' | 'UNION' | 'DIFFERENCE'

# ShaderNodeMath
# .operation = 'ADD' | 'SUBTRACT' | 'MULTIPLY' | 'DIVIDE' | 'POWER' | 'SQRT' | etc.

# ShaderNodeVectorMath
# .operation = 'ADD' | 'SUBTRACT' | 'MULTIPLY' | 'DIVIDE' | 'CROSS_PRODUCT' | 'DOT_PRODUCT' | etc.

# FunctionNodeCompare
# .operation = 'LESS_THAN' | 'GREATER_THAN' | 'EQUAL' | etc.
# .data_type = 'FLOAT' | 'INT' | 'VECTOR' | 'STRING' | 'RGBA'

# FunctionNodeBooleanMath
# .operation = 'AND' | 'OR' | 'NOT' | 'NAND' | 'NOR' | 'XNOR' | 'XOR'

# GeometryNodeSwitch
# .input_type = 'FLOAT' | 'INT' | 'BOOLEAN' | 'VECTOR' | 'GEOMETRY' | etc.
