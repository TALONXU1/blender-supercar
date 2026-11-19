import bpy
sc = bpy.context.scene
n = bpy.data.node_groups.new("t", 'CompositorNodeTree').nodes.new("CompositorNodeGlare")
print([a for a in dir(n) if not a.startswith('_')])
print("inputs", [i.name for i in n.inputs])
