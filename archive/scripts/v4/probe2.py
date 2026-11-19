import bpy, inspect
sc = bpy.context.scene
print("view transforms", [i.identifier for i in bpy.types.ColorManagedViewSettings.bl_rna.properties['view_transform'].enum_items])
print("render method", [i.identifier for i in bpy.types.Material.bl_rna.properties['surface_render_method'].enum_items])
print("shade_smooth_by_angle doc", bpy.ops.object.shade_smooth_by_angle.__doc__)
print("node types has glare", 'CompositorNodeGlare' in dir(bpy.types))
print("EEVEE raytracing", sc.eevee.use_raytracing, sc.eevee.ray_tracing_method)
print("film", [a for a in dir(sc.render) if 'film' in a])
