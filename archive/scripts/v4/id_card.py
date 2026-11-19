import bpy, os
bpy.ops.wm.open_mainfile(filepath=r"D:\项目session\blender-supercar\pipeline\v4_stage_anim.blend")
sc = bpy.context.scene
sc.frame_set(20)
sc.render.resolution_x = 800; sc.render.resolution_y = 450
sc.eevee.taa_render_samples = 12
out = r"D:\项目session\blender-supercar\renders_v4\test"
for tag, names in (("hide_endplate", ["GEO_F1_FrontWing_Endplate_L","GEO_F1_FrontWing_Endplate_R"]),
                   ("hide_nose_decal", ["DEC_Nose_Livery_PATCH"])):
    for o in bpy.data.objects:
        if o.name in names: o.hide_render = True
    sc.render.filepath = os.path.join(out, f"id_{tag}.jpg")
    bpy.ops.render.render(write_still=True)
    print("rendered", tag)
