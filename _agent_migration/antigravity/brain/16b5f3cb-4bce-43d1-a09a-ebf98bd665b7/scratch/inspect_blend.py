import bpy, os
for rel in ["pipeline/v4_stage_rig.blend", "LATEST/v5_stage_env.blend", "LATEST/v5_stage_anim.blend"]:
    p = os.path.join(r"D:\项目session\blender-supercar", rel)
    if not os.path.exists(p):
        continue
    bpy.ops.wm.open_mainfile(filepath=p)
    print("========================================")
    print("FILE:", rel)
    print("Total objects:", len(bpy.data.objects), "| Meshes:", len(bpy.data.meshes), "| Materials:", len(bpy.data.materials), "| Collections:", len(bpy.data.collections))
    print("Collections tree:")
    def dump_col(c, indent=0):
        print("  " * indent + f"- {c.name} (objs={len(c.objects)}, hide_vp={getattr(c, 'hide_viewport', False)}, hide_render={getattr(c, 'hide_render', False)})")
        for ch in c.children:
            dump_col(ch, indent+1)
    dump_col(bpy.context.scene.collection)
    unlinked = [c.name for c in bpy.data.collections if c.users == 0]
    if unlinked:
        print("Orphan collections:", unlinked)
    orphan_meshes = [m.name for m in bpy.data.meshes if m.users == 0]
    print("Orphan meshes:", len(orphan_meshes), orphan_meshes[:10])
    # Group objects by prefix
    from collections import Counter
    prefixes = Counter()
    types = Counter()
    for o in bpy.data.objects:
        types[o.type] += 1
        parts = o.name.split("_")
        pref = "_".join(parts[:2]) if len(parts) >= 2 else o.name
        prefixes[f"{o.type}:{pref}"] += 1
    print("Object types:", dict(types))
    print("Object prefixes:")
    for k, v in sorted(prefixes.items(), key=lambda x: (-x[1], x[0])):
        print(f"  {k}: {v}")
    # Check non-V5 objects in detail
    non_v5 = [o for o in bpy.data.objects if not o.name.startswith(("V5_", "Cam_", "LGT_V5"))]
    print(f"Non-V5 objects ({len(non_v5)}):")
    for o in sorted(non_v5, key=lambda x: x.name):
        cols = [c.name for c in o.users_collection]
        vcount = len(o.data.vertices) if o.type == 'MESH' and o.data else 0
        mods = [m.type for m in o.modifiers]
        par = o.parent.name if o.parent else None
        print(f"  {o.name:36s} type={o.type:8s} verts={vcount:6d} parent={str(par):20s} mods={mods} cols={cols} hide=({o.hide_viewport},{o.hide_render})")
