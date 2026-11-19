import bpy
bpy.ops.wm.open_mainfile(filepath=r"D:\项目session\blender-supercar\pipeline\v4_stage_model.blend")
for n in ("Mat_DEC_Sidepod_Oracle","Mat_DEC_Engine_RedBull","Mat_DEC_Nose_Livery","Mat_DEC_Halo_Oracle"):
    m = bpy.data.materials.get(n)
    if not m:
        print(n, "MISSING"); continue
    imgs = [x.image.name + " :: " + (x.image.filepath or "no-path") for x in m.node_tree.nodes if x.type=='TEX_IMAGE' and x.image]
    print(n, "->", imgs)
print("--- patches ---")
for o in bpy.data.objects:
    if o.name.endswith("_PATCH"):
        print(o.name, [mm.name for mm in o.data.materials], "verts", len(o.data.vertices))
