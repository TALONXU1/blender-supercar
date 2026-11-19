import bpy, time, os
bpy.ops.wm.open_mainfile(filepath=r"D:\项目session\blender-supercar\pipeline\v4_stage_anim.blend")
sc = bpy.context.scene
sc.render.resolution_x = 1920; sc.render.resolution_y = 1080
sc.eevee.taa_render_samples = 24
sc.frame_set(160)
sc.render.filepath = r"D:\项目session\blender-supercar\renders_v4\test\time_160.jpg"
t=time.time(); bpy.ops.render.render(write_still=True); print("RENDER_SECONDS", round(time.time()-t,1))
