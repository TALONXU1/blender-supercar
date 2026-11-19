import bpy, os
bpy.ops.wm.open_mainfile(filepath=r"D:\项目session\blender-supercar\pipeline\v4_stage_anim.blend")
sc = bpy.context.scene
sc.render.resolution_x = 800; sc.render.resolution_y = 450
sc.eevee.taa_render_samples = 12
for f in (370, 460):
    sc.frame_set(f)
    sc.render.filepath = rf"D:\项目session\blender-supercar\renders_v4\test\smoke_{f}.jpg"
    bpy.ops.render.render(write_still=True)
    print("ok", f)
# 检查烟雾关键帧
obs = [o for o in bpy.data.objects if o.name.startswith("GEO_Smoke_")]
print("puffs", len(obs))
if obs:
    o = obs[0]
    print("first puff anim", o.animation_data.action is not None if o.animation_data else False, "color", tuple(round(v,2) for v in o.color))
