# -*- coding: utf-8 -*-
"""V5 最终渲染：1920x1080 / 24fps / 2161 帧 / EEVEE"""
import bpy, os, time

PROJ = r"D:\项目session\blender-supercar"
BLEND = os.path.join(PROJ, "LATEST", "v5_stage_anim.blend")
FRAMES = os.path.join(PROJ, "renders_v5", "frames")

bpy.ops.wm.open_mainfile(filepath=BLEND)
sc = bpy.context.scene
os.makedirs(FRAMES, exist_ok=True)
sc.render.engine = 'BLENDER_EEVEE'
sc.eevee.taa_render_samples = 32
sc.eevee.use_raytracing = True
sc.render.resolution_x = 1920
sc.render.resolution_y = 1080
sc.render.resolution_percentage = 100
sc.render.fps = 24
sc.frame_start = 1
sc.frame_end = 2161
sc.render.use_motion_blur = True
sc.render.image_settings.file_format = 'JPEG'
sc.render.image_settings.quality = 95
sc.render.filepath = os.path.join(FRAMES, "f_")
sc.render.use_overwrite = False
sc.render.use_placeholder = True
print("RENDER START", time.time(), flush=True)
bpy.ops.render.render(animation=True)
print("RENDER END", time.time(), flush=True)
