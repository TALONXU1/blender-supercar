# -*- coding: utf-8 -*-
"""
V6 SPIDER-VERSE RENDERER — 支持分段并行渲染与全片 1281 帧渲染（Neo-Monaco × Nueva York 2099 Sky-Harbor）
输入: v6_spiderverse/v6_stage_anim_sv.blend

用法:
  blender -b -t 8 -P pipeline/render_v6_sv.py -- --range 269-364 --outdir renders_v6/clips_frames/clip1_miles_1610
  blender -b -t 8 -P pipeline/render_v6_sv.py -- --range 585-680 --outdir renders_v6/clips_frames/clip2_gwen_65
  blender -b -t 8 -P pipeline/render_v6_sv.py -- --range 993-1088 --outdir renders_v6/clips_frames/clip3_2099_impact
  blender -b -P pipeline/render_v6_sv.py -- --all
"""
import bpy
import os
import sys
import time

PROJ = r"D:\项目session\blender-supercar"
ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def argval(flag, default=None):
    if flag in ARGV:
        i = ARGV.index(flag)
        if i + 1 < len(ARGV) and not ARGV[i + 1].startswith("--"):
            return ARGV[i + 1]
        return True
    return default


BLEND = argval("--blend", os.path.join(PROJ, "v6_spiderverse", "v6_stage_anim_sv.blend"))
RANGE_STR = argval("--range", None)
DO_ALL = bool(argval("--all", False))
SAMPLES = int(argval("--samples", 18))
OVERWRITE = False if "--no-overwrite" in ARGV else True

if not os.path.isabs(BLEND):
    BLEND = os.path.join(PROJ, BLEND)

if not bpy.data.filepath or os.path.abspath(bpy.data.filepath).lower() != os.path.abspath(BLEND).lower():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
sc = bpy.context.scene

if DO_ALL and not RANGE_STR:
    f_start, f_end = 1, sc.frame_end
    outdir = argval("--outdir", os.path.join(PROJ, "renders_v6", "frames"))
elif RANGE_STR:
    parts = str(RANGE_STR).split("-")
    f_start, f_end = int(parts[0]), int(parts[1])
    outdir = argval("--outdir", os.path.join(PROJ, "renders_v6", "frames"))
else:
    raise SystemExit("Specify --range START-END [--outdir DIR] or --all")

if not os.path.isabs(outdir):
    outdir = os.path.join(PROJ, outdir)
os.makedirs(outdir, exist_ok=True)

# 确保从任意中间帧起渲时，初始活动相机与最近的前置 Timeline Marker 严格一致
markers = sorted(sc.timeline_markers, key=lambda m: m.frame)
init_cam = sc.camera
for mk in markers:
    if mk.frame <= f_start and mk.camera:
        init_cam = mk.camera
    elif mk.frame > f_start:
        break
if init_cam:
    sc.camera = init_cam

sc.render.engine = 'BLENDER_EEVEE'
sc.eevee.use_raytracing = True
if hasattr(sc.eevee, "ray_tracing_method"):
    sc.eevee.ray_tracing_method = 'SCREEN'
if hasattr(sc.eevee, "ray_tracing_options"):
    sc.eevee.ray_tracing_options.resolution_scale = '2'
    sc.eevee.ray_tracing_options.trace_max_roughness = 0.55
if hasattr(sc.eevee, "shadow_pool_size"):
    sc.eevee.shadow_pool_size = '1024'
if hasattr(sc.render, "compositor_device"):
    sc.render.compositor_device = 'CPU'
if hasattr(sc.render, "compositor_precision"):
    sc.render.compositor_precision = 'FULL'
if hasattr(sc.render, "use_compositor_frames_cache"):
    sc.render.use_compositor_frames_cache = False
if sc.view_layers:
    sc.view_layers[0].use_pass_emit = False
    if hasattr(sc.view_layers[0], "pass_cryptomatte_depth"):
        sc.view_layers[0].pass_cryptomatte_depth = 6
sc.eevee.taa_render_samples = SAMPLES
sc.render.resolution_x = 1920
sc.render.resolution_y = 1080
sc.render.resolution_percentage = 100
sc.render.fps = 24
sc.frame_start = f_start
sc.frame_end = f_end
sc.render.use_motion_blur = True
sc.render.motion_blur_shutter = 0.07
sc.render.image_settings.file_format = 'JPEG'
sc.render.image_settings.quality = 95
sc.render.filepath = os.path.join(outdir, "f_")
sc.render.use_overwrite = OVERWRITE
sc.render.use_placeholder = not OVERWRITE

t0 = time.time()
print(f"V6 RENDER START: frames {f_start}..{f_end} ({f_end - f_start + 1}f) -> {outdir} (init_cam={sc.camera.name if sc.camera else None})", flush=True)
bpy.ops.render.render(animation=True)
elapsed = time.time() - t0
n_frames = max(1, f_end - f_start + 1)
print(f"V6 RENDER DONE: {n_frames} frames in {elapsed:.1f}s ({elapsed / n_frames:.2f} s/frame)", flush=True)
