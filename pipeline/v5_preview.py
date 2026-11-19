# -*- coding: utf-8 -*-
"""V5 预览渲染 — 检查赛道几何 / 光照 / 材质（不动画）"""
import bpy, json, os, math
from mathutils import Vector, Matrix, Euler

PROJ = r"D:\项目session\blender-supercar"
BLEND = os.path.join(PROJ, "LATEST", "v5_stage_env.blend")
OUT = os.path.join(PROJ, "renders_v5", "preview")
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=BLEND)
sc = bpy.context.scene
P = json.load(open(os.path.join(PROJ, "track_data", "silverstone_track.json"), encoding="utf-8"))["points"]


def at_s(s):
    n = len(P)
    s = s % P[-1]["s"]
    lo, hi = 0, n - 1
    while hi - lo > 1:
        m = (lo + hi) // 2
        if P[m]["s"] <= s:
            lo = m
        else:
            hi = m
    f = (s - P[lo]["s"]) / max(P[lo + 1]["s"] - P[lo]["s"], 1e-9)
    x = P[lo]["xy"][0] * (1 - f) + P[lo + 1]["xy"][0] * f
    y = P[lo]["xy"][1] * (1 - f) + P[lo + 1]["xy"][1] * f
    a = math.radians(P[lo]["heading_deg"])
    b = math.radians(P[lo + 1]["heading_deg"])
    d = (b - a + math.pi) % (2 * math.pi) - math.pi
    h = a + d * f
    return Vector((x, y, 0.0)), h, Vector((math.sin(h), -math.cos(h), 0.0))


cd = bpy.data.cameras.new("CAM_PREV")
cam = bpy.data.objects.new("CAM_PREV", cd)
sc.collection.objects.link(cam)
sc.camera = cam
cd.clip_start = 0.05
cd.clip_end = 6000
cd.dof.use_dof = False

sc.render.engine = 'BLENDER_EEVEE'
sc.eevee.taa_render_samples = 24
sc.eevee.use_raytracing = True
sc.render.resolution_x = 1600
sc.render.resolution_y = 900
sc.render.image_settings.file_format = 'JPEG'
sc.render.image_settings.quality = 92
sc.view_settings.view_transform = 'AgX'
for look in ('High Contrast', 'AgX - High Contrast', 'Medium High Contrast'):
    try:
        sc.view_settings.look = look
        break
    except Exception:
        continue
sc.view_settings.exposure = -0.25


def shoot(name, loc, tgt, lens):
    loc = Vector(loc)
    d = Vector(tgt) - loc
    cam.location = loc
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    cd.lens = lens
    sc.render.filepath = os.path.join(OUT, name + ".jpg")
    bpy.ops.render.render(write_still=True)
    print("SHOT", name)


# 1) 俯视全场
cx = sum(p["xy"][0] for p in P) / len(P)
cy = sum(p["xy"][1] for p in P) / len(P)
shoot("01_top", (cx, cy + 10, 2100), (cx, cy, 0), 45)
# 2) 起跑直道低机位
p, h, r = at_s(200)
shoot("02_startline", (p + r * 9 - Vector((0, 0, -0.6))), (p + Vector((0, 0, 0.4))), 45)
# 3) 弯道低机位（多弯复合段）
p, h, r = at_s(5300)
shoot("03_corner_low", (p + r * 10 + Vector((0, 0, 0.55))), (p + Vector((0, 0, 0.35))), 50)
# 4) 长焦看台 + 护栏
p, h, r = at_s(2600)
shoot("04_stand", (p + r * 14 - Vector((0, 0, -6.0))), (p + Vector((0, 0, 1.0))), 85)
# 5) 路面细节（俯拍路面 + 路肩）
p, h, r = at_s(5320)
shoot("05_kerb", (p + r * 2 + Vector((0, 0, 26))), (p + Vector((0, 0, 0))), 55)
print("PREVIEW DONE")
