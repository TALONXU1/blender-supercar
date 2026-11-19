# -*- coding: utf-8 -*-
"""最终渲染：1080p / 24fps / 288 帧"""
import bpy, os, time
BLEND = r"D:\项目session\blender-supercar\pipeline\v4_stage_anim.blend"
FRAMES = r"D:\项目session\blender-supercar\renders_v4\frames"
bpy.ops.wm.open_mainfile(filepath=BLEND)
sc = bpy.context.scene
os.makedirs(FRAMES, exist_ok=True)
sc.render.engine = 'BLENDER_EEVEE'
sc.eevee.taa_render_samples = 24
sc.eevee.use_raytracing = True
sc.render.resolution_x = 1920
sc.render.resolution_y = 1080
sc.render.resolution_percentage = 100
sc.render.fps = 24
sc.frame_start = 1
sc.frame_end = int(sc.frame_end)
sc.render.use_motion_blur = True
pass
sc.render.image_settings.file_format = 'JPEG'
sc.render.image_settings.quality = 94
sc.render.filepath = os.path.join(FRAMES, "f_")
sc.render.use_overwrite = True
print("RENDER START", time.time())
bpy.ops.render.render(animation=True)
print("RENDER END", time.time())
