import bpy, sys, json, math
from mathutils import Vector

blend = sys.argv[-1] if sys.argv[-1].endswith('.blend') else r"D:\项目session\blender-supercar\scifi_f1_2035.blend"
bpy.ops.wm.open_mainfile(filepath=blend)
scene = bpy.context.scene

print("=== BLENDER", bpy.app.version_string, "===")
print("ENGINES:", [i.identifier for i in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items])
print("SCENE:", scene.name, "frames", scene.frame_start, scene.frame_end, "fps", scene.render.fps, "res",
      scene.render.resolution_x, scene.render.resolution_y, "engine", scene.render.engine)
print("CAMERA:", scene.camera.name if scene.camera else None)

types = {}
for o in bpy.data.objects:
    types.setdefault(o.type, []).append(o.name)
print("\nOBJECT COUNT:", len(bpy.data.objects))
for t, names in sorted(types.items()):
    print(f"\n-- {t} ({len(names)}) --")
    for n in sorted(names):
        o = bpy.data.objects[n]
        print(f"   {n} | parent={o.parent.name if o.parent else '-'} ptype={o.parent_type} pbone={o.parent_bone or '-'} verts={len(o.data.vertices) if o.type=='MESH' else '-'} mods={[m.type for m in o.modifiers]}")

print("\n-- MATERIALS (%d) --" % len(bpy.data.materials))
for m in sorted(bpy.data.materials, key=lambda x: x.name):
    users = m.users
    imgs = []
    if m.node_tree:
        for n in m.node_tree.nodes:
            if n.type == 'TEX_IMAGE' and n.image:
                imgs.append(n.image.name)
    print(f"   {m.name} users={users} imgs={imgs}")

print("\n-- IMAGES --")
for i in bpy.data.images:
    print("   ", i.name, i.size[:], i.filepath)

print("\n-- COLLECTIONS --")
for c in bpy.data.collections:
    print("   ", c.name, len(c.objects))

print("\n-- ACTIONS --")
for a in bpy.data.actions:
    print("   ", a.name, "fcurves", len(a.fcurves) if hasattr(a, 'fcurves') else 'n/a')

print("\n-- LIGHTS --")
for o in bpy.data.objects:
    if o.type == 'LIGHT':
        l = o.data
        print(f"   {o.name} type={l.type} energy={l.energy} loc={tuple(round(v,2) for v in o.location)}")

print("\n-- WORLD --")
print("   ", scene.world.name if scene.world else None)
if scene.world and scene.world.node_tree:
    for n in scene.world.node_tree.nodes:
        print("      node", n.name, n.type)

# bounding of car meshes
car = [o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith(('GEO_Track_', 'LGT_', 'Cam_'))]
mn = Vector((1e9,)*3); mx = Vector((-1e9,)*3)
for o in car:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        mn = Vector((min(mn[i], w[i]) for i in range(3)))
        mx = Vector((max(mx[i], w[i]) for i in range(3)))
print("\nCAR BBOX min", tuple(round(v,3) for v in mn), "max", tuple(round(v,3) for v in mx),
      "size", tuple(round(mx[i]-mn[i],3) for i in range(3)))

# materials per car object summary
print("\n-- SAMPLE MESH DETAIL --")
for o in sorted(car, key=lambda x: -len(x.data.vertices))[:25]:
    print(f"   {o.name} verts={len(o.data.vertices)} polys={len(o.data.polygons)} mats={[m.name if m else None for m in o.data.materials]} smooth={o.data.polygons[0].use_smooth if o.data.polygons else None} loc={tuple(round(v,3) for v in o.location)} scale={tuple(round(v,3) for v in o.scale)}")

# armature
for o in bpy.data.objects:
    if o.type == 'ARMATURE':
        print("\n-- ARMATURE", o.name, "bones", len(o.data.bones))
        for b in o.data.bones:
            print("   ", b.name, "head", tuple(round(v,3) for v in b.head_local), "tail", tuple(round(v,3) for v in b.tail_local), "parent", b.parent.name if b.parent else '-')

print("\n-- CONSTRAINTS --")
for o in bpy.data.objects:
    for c in o.constraints:
        print("   ", o.name, c.type, c.name)

print("\n-- DRIVERS --")
for o in bpy.data.objects:
    ad = o.animation_data
    if ad and ad.drivers:
        for d in ad.drivers:
            print("   ", o.name, d.data_path, d.driver.expression)
print("DONE")
