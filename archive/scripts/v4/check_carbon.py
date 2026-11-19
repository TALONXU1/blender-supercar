import bpy
bpy.ops.wm.open_mainfile(filepath=r"D:\项目session\blender-supercar\pipeline\v4_stage_model.blend")
for n in ("Mat_Forged_Carbon","Mat_Carbon_Satin","Mat_Carbon_Fiber","Mat_RedBull_MatteNavy","Mat_Rim_Forged_Dark"):
    m = bpy.data.materials.get(n)
    if not m: continue
    b = next((x for x in m.node_tree.nodes if x.type=='BSDF_PRINCIPLED'), None)
    if b:
        print(n, "base", [round(v,3) for v in b.inputs['Base Color'].default_value],
              "metal", round(b.inputs['Metallic'].default_value,2),
              "rough", round(b.inputs['Roughness'].default_value,2),
              "coat", round(b.inputs['Coat Weight'].default_value,2) if 'Coat Weight' in b.inputs else None,
              "links_to_basecolor", b.inputs['Base Color'].is_linked)
