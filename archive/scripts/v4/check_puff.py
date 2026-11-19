import bpy
bpy.ops.wm.open_mainfile(filepath=r"D:\项目session\blender-supercar\pipeline\v4_stage_anim.blend")
sc = bpy.context.scene
sc.frame_set(460)
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
obs = [o for o in bpy.data.objects if o.name.startswith("GEO_Smoke_")]
print("puffs", len(obs))
for o in obs[:4]:
    ev = o.evaluated_get(dg)
    print(o.name, "scale", [round(v,2) for v in ev.scale], "color", [round(v,2) for v in ev.color], "loc", [round(v,1) for v in ev.location], "hide", o.hide_render)
